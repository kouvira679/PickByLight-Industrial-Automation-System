import os


DEFAULT_ENDPOINT = os.getenv("PLC_ENDPOINT", "opc.tcp://172.21.4.1:4840")


class OPCUAClient:
    def __init__(self, endpoint=None):
        self.endpoint = endpoint or DEFAULT_ENDPOINT
        self.client = None
        self.connected = False
        self._node_cache = {}

    def connect(self):
        if self.connected and self.client is not None:
            return self

        try:
            from opcua import Client 
        except Exception as e:
            raise RuntimeError(
                "The python-opcua package is required. Install it with: pip install opcua"
            ) from e

        self.client = Client(self.endpoint)
        self.client.connect()
        self.connected = True
        self._node_cache.clear()
        print(f"Connected to PLC: {self.endpoint}")
        return self

    def disconnect(self):
        if self.connected and self.client is not None:
            self.client.disconnect()
            print("Disconnected from PLC")

        self.client = None
        self.connected = False
        self._node_cache.clear()

    def get_node(self, node_id):
        if not self.connected or self.client is None:
            raise RuntimeError("OPC UA client is not connected")

        if node_id not in self._node_cache:
            self._node_cache[node_id] = self.client.get_node(node_id)

        return self._node_cache[node_id]
