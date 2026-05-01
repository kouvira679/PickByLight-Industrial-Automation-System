# PickByLight_database
using sql to handle our pickbylight database

## OPC UA connection fix
The OPC UA reader and writer now support a persistent client connection.

- `main.py` connects to the PLC once at startup
- the same client is reused for trigger reads, RFID reads, and PLC writes
- the client only disconnects when the program exits
- endpoint can be changed with the `PLC_ENDPOINT` environment variable

Default endpoint:
`opc.tcp://172.21.4.1:4840`
