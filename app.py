"""
Telegraf OPC-UA Config Builder
------------------------------
Local web tool: connects to an OPC-UA server, lets you browse the address
space, select nodes, organize them into Telegraf groups, and generates a
telegraf.conf [[inputs.opcua]] / [[inputs.opcua_listener]] block to copy.

Run:
    pip install asyncua fastapi uvicorn
    python app.py
Then open http://localhost:8600

Notes:
- Run this on a machine that can reach the OPC-UA endpoint (WSL2 works).
- Single-user tool: it holds one OPC-UA client session at a time.
"""

import asyncio
import contextlib
from pathlib import Path
from typing import Optional

import uvicorn
from asyncua import Client, ua
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

APP_DIR = Path(__file__).parent
app = FastAPI(title="Telegraf OPC-UA Config Builder")

STATE = {"client": None, "endpoint": None}
LOCK = asyncio.Lock()


class ConnectRequest(BaseModel):
    endpoint: str
    security_policy: str = "None"       # None | Basic128Rsa15 | Basic256 | Basic256Sha256
    security_mode: str = "None"         # None | Sign | SignAndEncrypt
    auth_method: str = "Anonymous"      # Anonymous | UserName | Certificate
    username: Optional[str] = None
    password: Optional[str] = None
    certificate: Optional[str] = None   # path on this machine, only for secure policies
    private_key: Optional[str] = None


class BrowseRequest(BaseModel):
    node_id: str


async def _drop_client():
    client = STATE.get("client")
    STATE["client"] = None
    STATE["endpoint"] = None
    if client is not None:
        with contextlib.suppress(Exception):
            await client.disconnect()


def _node_class_name(node_class) -> str:
    try:
        return ua.NodeClass(node_class).name
    except Exception:
        return str(node_class)


async def _list_children(node_id: str):
    client = STATE["client"]
    node = client.get_node(node_id)
    refs = await node.get_children_descriptions()
    children = []
    for ref in refs:
        nid = ref.NodeId.to_string()
        # ExpandedNodeId on the same server can carry a srv=0; prefix; strip it
        if nid.startswith("srv="):
            nid = nid.split(";", 1)[1]
        children.append({
            "nodeId": nid,
            "browseName": ref.BrowseName.Name,
            "displayName": (ref.DisplayName.Text or ref.BrowseName.Name),
            "nodeClass": _node_class_name(ref.NodeClass),
        })
    children.sort(key=lambda c: (c["nodeClass"] != "Object", c["displayName"].lower()))
    return children


@app.post("/api/connect")
async def connect(req: ConnectRequest):
    async with LOCK:
        await _drop_client()
        client = Client(url=req.endpoint, timeout=10)
        try:
            if req.security_policy not in ("", "None"):
                if not (req.certificate and req.private_key):
                    return JSONResponse(
                        {"ok": False, "error": "Secure policies need certificate and private key paths."},
                        status_code=400,
                    )
                await client.set_security_string(
                    f"{req.security_policy},{req.security_mode},{req.certificate},{req.private_key}"
                )
            if req.auth_method == "UserName":
                client.set_user(req.username or "")
                client.set_password(req.password or "")
            await client.connect()
        except Exception as exc:
            with contextlib.suppress(Exception):
                await client.disconnect()
            return JSONResponse({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status_code=400)

        STATE["client"] = client
        STATE["endpoint"] = req.endpoint
        try:
            namespaces = await client.get_namespace_array()
            children = await _list_children("i=85")  # Objects folder
        except Exception as exc:
            await _drop_client()
            return JSONResponse({"ok": False, "error": f"Connected but browse failed: {exc}"}, status_code=400)

        return {"ok": True, "endpoint": req.endpoint, "namespaces": namespaces, "children": children}


@app.post("/api/browse")
async def browse(req: BrowseRequest):
    async with LOCK:
        if STATE["client"] is None:
            return JSONResponse({"ok": False, "error": "Not connected."}, status_code=400)
        try:
            children = await _list_children(req.node_id)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status_code=400)
        return {"ok": True, "children": children}


@app.post("/api/disconnect")
async def disconnect():
    async with LOCK:
        await _drop_client()
    return {"ok": True}


@app.get("/api/status")
async def status():
    return {"connected": STATE["client"] is not None, "endpoint": STATE["endpoint"]}


@app.get("/", response_class=HTMLResponse)
async def index():
    return (APP_DIR / "index.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8600, log_level="warning")
