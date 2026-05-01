from database.schema import initialize_database
from database.queries import log_order_step
from dbh import DB, STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETE
from opcua_connection.client import OPCUAClient
from opcua_connection.reader import ENDPOINT, wait_and_read_rfid, wait_until_trigger_clears
from logic.order_logic import process_order_step
from models.models_catalog import get_model
from opcua_connection.writer import (
    send_task_to_plc, wait_for_panel_response, write_hmi_step
)
from test_orders import seed_test_orders
import socket
import json
from database.queries import log_order_step, deduct_inventory
import os

ORDERS_DB = "production_orders.db"


# ── Database helpers ───────────────────────────────────────────────────────────

def get_next_pending_order(db: DB):
    pending = [dict(row) for row in db.pull(order_status=STATUS_PENDING)]
    return pending[0] if pending else None


def mark_order_status(db: DB, order_id: int, is_final: bool) -> None:
    db.update_status(order_id, STATUS_COMPLETE if is_final else STATUS_IN_PROGRESS)


# ── HMI / GUI helpers ──────────────────────────────────────────────────────────

def send_to_hmi(payload: dict):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("localhost", 65432))
        client.sendall(json.dumps(payload).encode())
        response = client.recv(1024).decode()
        client.close()
        print(f"GUI response: {response}")
        return response
    except ConnectionRefusedError:
        print("GUI not running — falling back to panel HMI.")
        return None


def get_operator_response(payload: dict, plc_client) -> str:
    response = send_to_hmi(payload)
    if response is not None:
        return response
    return wait_for_panel_response(plc_client)


# ── Order resolution ───────────────────────────────────────────────────────────

def resolve_new_order(rfid_result, orders_db: DB):
    """Called once when a pallet arrives. Returns (order_id, model_id, source)."""
    rfid_order_id = rfid_result["order_id"]
    rfid_model_id = rfid_result["model_id"]

    if rfid_model_id in (1, 2, 3) and rfid_order_id != 0:
        return rfid_order_id, rfid_model_id, "rfid"

    pending = get_next_pending_order(orders_db)
    if pending is None:
        raise RuntimeError("No pending orders and RFID is blank — nothing to do.")

    print(
        f"RFID blank/invalid — using pending DB order: "
        f"order_id={pending['order_id']}, model_id={pending['model_id']}"
    )
    return pending["order_id"], pending["model_id"], "database_fallback"


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    for db_file in ["production_orders.db", "pick_by_light.db"]:
        if os.path.exists(db_file):
            os.remove(db_file)

    initialize_database() 
    seed_test_orders()
    orders_db = DB(ORDERS_DB)

    plc_client = OPCUAClient(ENDPOINT)
    plc_client.connect()

    print("Python application started. Waiting for PLC triggers...")

    try:
        while True:
            try:
                # ══ PHASE 1: Wait for pallet ══════════════════════════════════
                # One PLC trigger per order — pallet arrives at station
                rfid_result = wait_and_read_rfid(opc_client=plc_client)
                order_id, model_id, source = resolve_new_order(rfid_result, orders_db)

                model       = get_model(model_id)
                total_steps = len(model["workplan"])

                print(f"\n[Order] Started — order {order_id}, model {model_id}, {total_steps} steps")
                mark_order_status(orders_db, order_id, is_final=False)

                # ══ PHASE 2: Step through ALL parts with HMI confirm ══════════
                # Operator presses Confirm on panel for each step.
                # Conveyor does NOT move between steps — only after final step.
                refused = False

                for step_index in range(total_steps):
                    step_result   = process_order_step(model_id, step_index)
                    is_final_step = step_result["is_final_step"]

                    print(f"\nPick instruction")
                    print(f"  Order ID  : {order_id}")
                    print(f"  Source    : {source}")
                    print(f"  Model     : {step_result['model_name']}")
                    print(f"  Step      : {step_index + 1} of {total_steps}")
                    print(f"  Task code : {step_result['task_code']}")
                    print(f"  Part      : {step_result['part_name']}")
                    print(f"  Quantity  : {step_result['quantity']}")

                    log_order_step(
                        order_id=order_id,
                        model_id=model_id,
                        step_index=step_index,
                        task_code=step_result["task_code"],
                        part_name=step_result["part_name"],
                        quantity=step_result["quantity"],
                    )

                    # Update HMI panel display
                    write_hmi_step(
                        opc_client=plc_client,
                        instruction=step_result['part_name'],
                        step_index=step_index + 1,
                        total_steps=total_steps,
                    )

                    # Build payload for GUI (if running)
                    hmi_payload = {
                        "order_id":   order_id,
                        "model_name": step_result["model_name"],
                        "step_index": step_index,
                        "step_label": f"Step {step_index + 1} of {total_steps}",
                        "task_code":  step_result["task_code"],
                        "part_name":  step_result["part_name"],
                        "quantity":   step_result["quantity"],
                        "is_final":   is_final_step,
                    }

                    # Wait for operator to press Confirm or Refuse
                    response = get_operator_response(hmi_payload, plc_client)
                    

                    if response == "refused":
                        print(f"  Order refused at step {step_index + 1}.")
                        refused = True
                        break
                    
                    deduct_inventory(step_result['part_name'], step_result['quantity'])

                    if not is_final_step:
                        # Mid-order step — just acknowledge, keep pallet still
                        print(f"  Step {step_index + 1} confirmed — next step.")
                        continue

                    # ── Final step confirmed → release pallet / move conveyor ──
                    print(f"  All steps done — sending task to PLC and releasing pallet.")
                    send_task_to_plc(
                        task_code=step_result["task_code"],
                        quantity=step_result["quantity"],
                        step_index=0,          
                        display_step=step_index + 1,
                        total_steps=total_steps,
                        instruction=step_result["part_name"],
                        opc_client=plc_client,
                        release_after=True,     
                    )

                # ══ PHASE 3: Close order, wait for pallet to clear ════════════
                mark_order_status(orders_db, order_id, is_final=True)

                if refused:
                    print(f"Order {order_id} closed (refused by operator).\n")
                else:
                    print(f"Order {order_id} complete — all {total_steps} steps done.\n")

                print("Waiting for pallet to clear conveyor...")
                cleared = wait_until_trigger_clears(opc_client=plc_client, timeout=10.0)
                if not cleared:
                    print("Warning: awaitApp stayed TRUE — check conveyor.")

                print("Ready for next order.\n")

            except (ValueError, IndexError, RuntimeError) as e:
                print(f"Error: {e}")
                wait_until_trigger_clears(opc_client=plc_client, timeout=5.0)
            except Exception as e:
                print(f"Unexpected error: {e}")
                wait_until_trigger_clears(opc_client=plc_client, timeout=5.0)
    finally:
        plc_client.disconnect()


if __name__ == "__main__":
    main()