import asyncio

import websockets
import websockets.client


async def start_client():
    """Runs the test client."""
    async with websockets.connect("ws://localhost:8001") as ws:
        await ws.send("create")
        msg = await ws.recv()
        print(msg)

if __name__ == '__main__':
    asyncio.run(start_client())
