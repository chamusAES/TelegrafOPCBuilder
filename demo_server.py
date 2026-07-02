"""Throwaway OPC-UA demo server mimicking a BAS-style address space."""
import asyncio
from asyncua import Server, ua


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://127.0.0.1:62541")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    idx = 1  # use ns=1 like the JACE-style export

    objects = server.nodes.objects
    bldg = await objects.add_object(ua.NodeId("Site", idx), "Site")
    names = [
        "AnalogInput25.Present_Value", "AnalogInput26.Present_Value",
        "AnalogInput27.Present_Value", "BinaryInput15.Present_Value",
        "MultiStateInput2.Present_Value",
    ]
    for n in names:
        nid = ua.NodeId(f"[Site]{n}", idx)
        await bldg.add_variable(nid, n, 42.0)

    async with server:
        print("demo server up")
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
