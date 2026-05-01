import os
import time
from opcua_connection.client import DEFAULT_ENDPOINT, OPCUAClient
from opcua import Client, ua

ENDPOINT = os.getenv("PLC_ENDPOINT", DEFAULT_ENDPOINT)

APP_DONE_NODE_ID      = 'ns=3;s="abstractMachine"."appDone"'
APP_RUN_NODE_ID       = 'ns=3;s="abstractMachine"."appRun"'
TASK_CODE_NODE_ID     = 'ns=3;s="abstractMachine"."taskCode"'
QUANTITY_NODE_ID      = 'ns=3;s="abstractMachine"."quantity"'
STEP_INDEX_NODE_ID    = 'ns=3;s="abstractMachine"."stepIndex"'
RELEASE_NODE_ID       = 'ns=3;s="abstractMachine"."release"'

READ_RFID_DATA_NODE_ID  = 'ns=3;s="identData"."readData"'
WRITE_RFID_DATA_NODE_ID = 'ns=3;s="identData"."writeData"'
RFID_DO_WRITE_NODE_ID   = 'ns=3;s="rfidControl"."doWrite"'
RFID_WRITE_DONE_NODE_ID = 'ns=3;s="rfidControl"."writeDone"'

# HMI panel tags
HMI_INSTRUCTION_NODE_ID  = 'ns=3;s="HMI_Data"."HMI_Instruction"'
HMI_STEP_COUNTER_NODE_ID = 'ns=3;s="HMI_Data"."HMI_StepCounter"'
HMI_CONFIRM_NODE_ID      = 'ns=3;s="HMI_Data"."confirm"'
HMI_REFUSE_NODE_ID       = 'ns=3;s="HMI_Data"."refuse"'


def write_node_value(opc_client, node_id, value):
    node = opc_client.get_node(node_id)
    if isinstance(value, (bytes, bytearray)):
        variant_type = ua.VariantType.ByteString
    elif isinstance(value, bool):
        variant_type = ua.VariantType.Boolean
    else:
        variant_type = node.get_data_type_as_variant_type()
    if not isinstance(variant_type, ua.VariantType):
        raise TypeError(
            f"Expected ua.VariantType for node '{node_id}', "
            f"got {type(variant_type).__name__}: {variant_type!r}"
        )
    node.set_value(ua.DataValue(ua.Variant(value, variant_type)))


def write_rfid_data(opc_client, rfid_data):
    """Write data to RFID and complete doWrite handshake."""
    if isinstance(rfid_data, (bytes, bytearray)):
        payload = rfid_data
    elif isinstance(rfid_data, list):
        payload = bytes(rfid_data)
    else:
        raise ValueError("RFID data must be bytes/bytearray/list")
    write_node_value(opc_client, WRITE_RFID_DATA_NODE_ID, payload)
    write_node_value(opc_client, RFID_DO_WRITE_NODE_ID, True)
    while not bool(opc_client.get_node(RFID_WRITE_DONE_NODE_ID).get_value()):
        time.sleep(0.05)
    write_node_value(opc_client, RFID_DO_WRITE_NODE_ID, False)


def update_rfid_step_index(opc_client, step_index):
    """Read RFID payload, update byte 5 (step index) and write back."""
    raw_data = opc_client.get_node(READ_RFID_DATA_NODE_ID).get_value()
    if raw_data is None:
        raw_data = bytearray(32)
    elif isinstance(raw_data, list):
        raw_data = bytearray(raw_data)
    elif isinstance(raw_data, (bytes, bytearray)):
        raw_data = bytearray(raw_data)
    else:
        raise ValueError(f"Unsupported RFID payload type: {type(raw_data).__name__}")
    if len(raw_data) < 32:
        raw_data.extend(b"\x00" * (32 - len(raw_data)))
    raw_data[5] = int(step_index) & 0xFF
    write_rfid_data(opc_client, raw_data)


def write_hmi_step(opc_client, instruction, step_index, total_steps):
    """Write current instruction and step counter to the HMI panel."""
    write_node_value(opc_client, HMI_INSTRUCTION_NODE_ID, str(instruction))
    write_node_value(opc_client, HMI_STEP_COUNTER_NODE_ID, f"Step {step_index} of {total_steps}")


def wait_for_panel_response(opc_client, timeout=60.0):
    """Poll HMI_Confirm and HMI_Refuse tags until one is pressed. Returns 'confirmed' or 'refused'."""
    # Reset both bits first in case they were left True
    write_node_value(opc_client, HMI_CONFIRM_NODE_ID, False)
    write_node_value(opc_client, HMI_REFUSE_NODE_ID, False)

    start = time.time()
    while True:
        if bool(opc_client.get_node(HMI_CONFIRM_NODE_ID).get_value()):
            write_node_value(opc_client, HMI_CONFIRM_NODE_ID, False)
            return "confirmed"
        if bool(opc_client.get_node(HMI_REFUSE_NODE_ID).get_value()):
            write_node_value(opc_client, HMI_REFUSE_NODE_ID, False)
            return "refused"
        if time.time() - start > timeout:
            print("Warning: panel response timed out, defaulting to confirmed.")
            return "confirmed"
        time.sleep(0.1)


def _ensure_client(opc_client=None):
    created_here = opc_client is None
    client = opc_client or OPCUAClient(ENDPOINT)
    client.connect()
    return client, created_here

def set_app_run(opc_client=None):
    client, created_here = _ensure_client(opc_client)
    try:
        app_run_node = client.get_node(APP_RUN_NODE_ID)
        app_run_node.set_value(ua.DataValue(ua.Variant(True, app_run_node.get_data_type_as_variant_type())))
    finally:
        if created_here:
            client.disconnect()

def send_task_to_plc(task_code, quantity, step_index, total_steps, instruction, 
                     display_step=None,   # <-- add this
                     opc_client=None, release_after=True):
    client, created_here = _ensure_client(opc_client)
    try:

        panel_step = display_step if display_step is not None else step_index
        write_hmi_step(client, instruction, panel_step, total_steps)

        write_node_value(client, TASK_CODE_NODE_ID, int(task_code - 400))
        update_rfid_step_index(client, step_index)
        write_node_value(client, APP_RUN_NODE_ID, True)
        while not client.get_node(APP_DONE_NODE_ID).get_value():
            time.sleep(0.05)
        if release_after:
            write_node_value(client, RELEASE_NODE_ID, True)
            time.sleep(0.1)
            write_node_value(client, RELEASE_NODE_ID, False)
        write_node_value(client, APP_RUN_NODE_ID, False)
        print(f"Sent task_code={task_code}, quantity={quantity}, step_index={step_index} to PLC.")
    finally:
        if created_here:
            client.disconnect()


if __name__ == "__main__":
    temp_client = OPCUAClient(ENDPOINT)
    try:
        temp_client.connect()
        send_task_to_plc(
            task_code=411,
            quantity=1,
            step_index=3,
            total_steps=4,
            instruction="Grab 1 Red Cover",
            opc_client=temp_client
        )
    finally:
        temp_client.disconnect()