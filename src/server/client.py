#!/usr/bin/env python

import asyncio
import json

import websockets


# helper function ( dict -> str of json )
def encode_json(message) -> str :
    return json.dumps( message, ensure_ascii=False)

# helper function ( str of json -> dict )
def decode_json(message) -> dict :
    return json.loads( message )

async def client():
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as websocket:
        # Close the connection when receiving SIGTERM.

        try :
            oper = int(input("input oper : "))
            event = {}
            if oper ==1 :
                event = {
                    "type" : "create",
                }

                await websocket.send( encode_json(event) )
            elif oper==2 :

                key = str(input("input room key: ") )
                event = {
                    "type" : "join",
                    "room_key" : key ,
                }
                await websocket.send( encode_json(event) )
            else:
                # join public room
                event = {
                    "type" : "join",
                }
                await websocket.send( encode_json(event) )


            async for message in websocket:
                print("mes: " , message )

                event = decode_json( message )

                if event["type"] == "waiting" :
                    # await websocket.send( encode_json(event) )
                    print("still waiting")
                elif event["type"] == "start":
                    # The game start
                    await websocket.send( encode_json(event) )

                elif event["type"] == "play":
                    oper = int(input("input your move: "))

                    await websocket.send( encode_json(oper) )
                elif event["type"] == "player_disconnect":
                    # player disconnect 
                    print( event )
                    # await websocket.send( encode_json(event) )

        except websockets.exceptions.ConnectionClosedError:
            print("server close connect")
        finally:
            print("connect close")

asyncio.run(client())