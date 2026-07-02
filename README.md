# Telegraf OPC-UA Config Builder

Local web tool. Connects to a live OPC-UA server, lets you browse the address
space, organize tags into groups with UNS-style default_tags, and generates a
telegraf.conf input block to copy or download.

## Run

    pip install asyncua fastapi uvicorn
    python app.py

Open http://localhost:8600. Run it anywhere that can reach the OPC-UA
endpoint (WSL2 works fine for the Ignition and JACE setups).

## Workflow

1. Enter endpoint, security policy/mode, and auth. Connect.
2. Expand the address space tree. "+ add" puts a variable in the active
   group. "+ vars" on an object adds all its direct child variables at once.
3. Groups carry namespace, identifier_type, and default_tags (site,
   subsystem, system_type, etc.). Namespace and id type auto-fill from the
   first node added. Node names are editable inline.
4. The config pane updates live. Copy or download.

## Output modes

- inputs.opcua, grouped (the standard format with per-group default_tags)
- inputs.opcua, flat node list
- inputs.opcua_listener (subscription) in either layout, with
  subscription_interval

Toggles for the timeout/retry block, use_unregistered_reads, timestamp
source, tagexclude/fieldexclude, and password masking ("***") in output.

Nodes can also be added by pasting a NodeId string (ns=1;s=...) without
connecting, so the tool works offline as a pure formatter too.

## Test server

demo_server.py stands up a fake JACE-style server on opc.tcp://127.0.0.1:62541
with [Site] string identifiers for testing the tool end to end.

State (groups, settings) persists in browser localStorage between sessions.
