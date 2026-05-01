import os
import time

from opcua_connection.client import DEFAULT_ENDPOINT, OPCUAClient

ENDPOINT = os.getenv("PLC_ENDPOINT", DEFAULT_ENDPOINT)

RFID_NODE_ID = 'ns=3;s="identData"."readData"'
AWAIT_APP_NODE_ID = 'ns=3;s="abstractMachine"."awaitApp"'
APP_RUN_NODE_ID = 'ns=3;s="abstractMachine"."appRun"'


def parse_rfid_data(raw_data):
    """
    Expected RFID schema:
    byte[0:4] = order_id
    byte[4]   = model_id
    byte[5]   = step_index
    """
    if raw_data is None:
        raise ValueError("RFID data is empty")

    if isinstance(raw_data, list):
        raw_data = bytes(raw_data)

    if len(raw_data) < 6:
        raise ValueError(f"RFID data too short: {raw_data}")

    order_id = int.from_bytes(raw_data[0:4], byteorder="little")
    model_id = raw_data[4]
    step_index = raw_data[5]

    return order_id, model_id, step_index


def is_blank_rfid(raw_data):
    if raw_data is None:
        return True
    if isinstance(raw_data, list):
        return not any(raw_data[:6])
    if isinstance(raw_data, (bytes, bytearray)):
        return not any(raw_data[:6])
    return False


def _ensure_client(opc_client=None):
    created_here = opc_client is None
    client = opc_client or OPCUAClient(ENDPOINT)
    client.connect()
    return client, created_here


def get_await_app_value(opc_client=None):
    client, created_here = _ensure_client(opc_client)
    try:
        await_app_node = client.get_node(AWAIT_APP_NODE_ID)
        return bool(await_app_node.get_value())
    finally:
        if created_here:
            client.disconnect()


def wait_for_trigger_rising_edge(opc_client=None, poll_interval=0.2):
    client, created_here = _ensure_client(opc_client)

    try:
        await_app_node = client.get_node(AWAIT_APP_NODE_ID)
        print("Waiting for PLC trigger (awaitApp rising edge)...")

        saw_low = False
        while True:
            current = bool(await_app_node.get_value())
            if not current:
                saw_low = True
            elif saw_low:
                print("PLC trigger received.")
                return True
            time.sleep(poll_interval)
    finally:
        if created_here:
            client.disconnect()


def wait_until_trigger_clears(opc_client=None, poll_interval=0.2, timeout=10.0):
    client, created_here = _ensure_client(opc_client)
    started = time.time()
    try:
        await_app_node = client.get_node(AWAIT_APP_NODE_ID)
        while bool(await_app_node.get_value()):
            if timeout is not None and (time.time() - started) > timeout:
                return False
            time.sleep(poll_interval)
        return True
    finally:
        if created_here:
            client.disconnect()


def read_rfid(opc_client=None):
    client, created_here = _ensure_client(opc_client)

    try:
        rfid_node = client.get_node(RFID_NODE_ID)
        raw_data = rfid_node.get_value()

        print(f"Raw RFID data: {raw_data}")

        order_id, model_id, step_index = parse_rfid_data(raw_data)

        print(f"Order ID: {order_id}")
        print(f"Model ID: {model_id}")
        print(f"Step Index: {step_index}")

        return {
            "order_id": order_id,
            "model_id": model_id,
            "step_index": step_index,
            "raw_data": raw_data,
            "is_blank": is_blank_rfid(raw_data),
        }
    finally:
        if created_here:
            client.disconnect()


def wait_and_read_rfid(opc_client=None, poll_interval=0.2):
    wait_for_trigger_rising_edge(opc_client=opc_client, poll_interval=poll_interval)
    return read_rfid(opc_client=opc_client)


if __name__ == "__main__":
    temp_client = OPCUAClient(ENDPOINT)
    try:
        temp_client.connect()
        result = wait_and_read_rfid(opc_client=temp_client)
        print(result)
    finally:
        temp_client.disconnect()
