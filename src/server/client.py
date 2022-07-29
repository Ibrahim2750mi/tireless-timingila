#!/usr/bin/env python

"""Dummy client."""

import asyncio

import websockets
import websockets.exceptions

from server import decode_json, encode_json


async def client(oper: int = None):
    """Connect to server side"""
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as websocket:

        try:
            if oper is None:
                oper = int(input("input oper : "))
            if oper == 1:
                # create private room
                event = {
                    "type": "create",
                }

                await websocket.send(encode_json(event))
            elif oper == 2:
                # join private room
                key = str(input("input room key: "))
                event = {
                    "type": "join",
                    "room_key": key,
                }
                await websocket.send(encode_json(event))
            else:
                event = {
                    "type": "join",
                }
                await websocket.send(encode_json(event))

            async for message in websocket:

                print("mes: ", message)
                event = decode_json(message)

                if event["type"] == "waiting":
                    # await websocket.send( encode_json(event) )
                    print("still waiting")
                elif event["type"] == "start":
                    # The game start
                    await websocket.send(encode_json(event))

                elif event["type"] == "play":
                    oper = int(input("input your move: "))

                    await websocket.send(encode_json(oper))
                elif event["type"] == "player_disconnect":
                    print(event)
                    # await websocket.send( encode_json(event) )

        except websockets.exceptions.ConnectionClosedError:
            print("server close connect")
        finally:
            print("connect close")


asyncio.run(client())
