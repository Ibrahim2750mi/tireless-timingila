#!/usr/bin/env python

import asyncio
import json
import secrets
from functools import partial
from time import sleep
from typing import Dict, List

import websockets
import websockets.legacy.server

from config import ROOM_SIZE, WAITING_SECOND

online_client: Dict[str, "Client"] = {}
private_rooms: Dict[str, "Room"] = {}
public_rooms: Dict[str, "Room"] = {}

encode_json = partial(json.dumps, ensure_ascii=False)


class Client:
    """Client class that store in 'online_client' dict & 'Room' object."""

    def __init__(self, websocket: websockets.legacy.server.WebSocketServerProtocol, client_id: str,
                 room_key: str) -> None:
        self.socket = websocket
        self.client_id = client_id
        self.room_key = room_key


class Room:
    """A room contains a maximum of 4 players. If 4 players are present in the room the game starts."""

    def __init__(self, room_key) -> None:
        self.room_key: str = room_key
        self.clients: Dict[str, Client] = {}
        self.socket_list: List = []
        self.game_status: Dict = {}

    def __len__(self) -> int:
        return len(self.clients)

    def add_player(self, client_id: str) -> None:
        """Adds the player in the room."""
        self.clients[client_id] = online_client[client_id]
        self.socket_list.append(online_client[client_id].socket)

    def remove_player(self, client_id: str) -> None:
        """Removes player from the room."""
        self.socket_list.remove(self.clients[client_id].socket)
        del self.clients[client_id]


async def error(websocket: websockets.legacy.server.WebSocketServerProtocol, message):
    """Send an error message."""
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send(encode_json(event))


async def play(websocket: websockets.legacy.server.WebSocketServerProtocol, current_room: Room):
    """Receive and process moves from a player."""
    if len(current_room) == ROOM_SIZE:

        async for message in websocket:
            """
            Unfinish part :
                Still waiting for game logic & game stucture etc...
            """

            await websocket.send(encode_json(message))

            '''
            # Parse a "play" event from the UI.
            event = json.loads(message)
            assert event["type"] == "play"
            column = event["column"]

            try:
                # Play the move.
                row = game.play(role, column)
            except RuntimeError as exc:
                # Send an "error" event if the move was illegal.
                await error(websocket, str(exc))
                continue

            # Send a "play" event to update the UI.
            event = {
                "type": "play",
                "player": role,
                "column": column,
                "row": row,
            }
            websockets.broadcast( current_room.socket_list , json.dumps(event))

            # If move is winning, send a "win" event.
            if game.winner is not None:
                event = {
                    "type": "win",
                    "player": game.winner,
                }
                websockets.broadcast( current_room.socket_list , json.dumps(event))
            '''

    elif len(current_room) < ROOM_SIZE:
        event = {
            "type": "waiting",
        }
        await websocket.send(json.dumps(event))
        sleep(WAITING_SECOND)

    else:
        await error(websocket, "The room is full!")


async def create_private_room(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """Handle a connection from the room owner (the player that creates private room)."""
    client_id = secrets.token_urlsafe(6)
    room_key = secrets.token_urlsafe(6)

    online_client[client_id] = Client(websocket, client_id, room_key)
    private_rooms[room_key] = Room(room_key)
    private_rooms[room_key].add_player(client_id)

    try:
        event = {
            "type": "init",
            "room_key": room_key,
        }

        await websocket.send(json.dumps(event))
        # Receive and process moves from the first player.
        await play(websocket, private_rooms[room_key])

    finally:
        del online_client[client_id]
        del private_rooms[room_key]


async def join_private_game(websocket: websockets.legacy.server.WebSocketServerProtocol, room_key):
    """Handle a connection from the other player (except the one who create room)."""
    try:
        current_room = private_rooms[room_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    # add current player to global online_client dict
    client_id = secrets.token_urlsafe(6)
    online_client[client_id] = Client(websocket, client_id, room_key)

    current_room.add_player(client_id)

    try:
        await play(websocket, current_room)
    finally:
        del current_room.clients[client_id]


async def create_public_room(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """
    Creates a public room which can be joined without a room key.

    The function will be called when :
        1. when 'ROOMS' is empty
        2. when the last room from 'ROOMS' is full
    """
    print("create public game\n")

    client_id = secrets.token_urlsafe(6)
    room_key = secrets.token_urlsafe(6)

    online_client[client_id] = Client(websocket, client_id, room_key)
    public_rooms[room_key] = Room(room_key)
    private_rooms[-1].add_player(client_id)

    try:
        # Send the secret access tokens to the browser of the first player,
        # where they'll be used for building "room_key" and "watch" links.
        event = {
            "type": "init",
            "room_key": room_key,
        }

        await websocket.send(json.dumps(event))
        # Receive and process moves from the first player.
        await play(websocket, private_rooms[room_key])

    finally:
        del online_client[client_id]
        del private_rooms[room_key]


async def join_public_game(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """Handle a connection that player joined public game."""
    print("join public game\n")

    if (len(public_rooms) == 0) or (len(public_rooms[-1]) == ROOM_SIZE):
        # the situation that player become room creator.
        await create_public_room(websocket)

    else:

        current_room = private_rooms[-1]

        client_id = secrets.token_urlsafe(6)
        online_client[client_id] = Client(websocket, client_id, current_room.room_key)

        current_room.add_player(client_id)

        try:
            await play(websocket, current_room)
        finally:
            del current_room.clients[client_id]


async def handler(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """Handle a connection and dispatch it according to who is connecting."""
    message = await websocket.recv()
    # event = decode_json(message)
    # websocket.recv() sends a string on a text frame. Remove this comment and the above line.

    if "join" in message:
        if "room_key" in message:
            await join_private_game(websocket, message[-6:])
        else:
            await join_public_game(websocket)
    elif message == "create":
        await create_private_room(websocket)


async def start_server():
    """To get the server started at the uri "ws://localhost:8001"."""
    async with websockets.serve(handler, "localhost", 8001):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
