#!/usr/bin/env python

import asyncio
import json
import secrets
from typing import Dict, List

import websockets
import websockets.legacy.server

from config import ROOM_SIZE

# Global varibales
online_clients: Dict[str, "Client"] = {}
private_rooms: Dict[str, "Room"] = {}
public_rooms: Dict[str, "Room"] = {}
public_rooms_keys: List[str] = []


def encode_json(message) -> str:
    """Helper function ( dict -> str of json )"""
    return json.dumps(message, ensure_ascii=False)


def decode_json(message) -> dict:
    """Helper function ( str of json -> dict )"""
    return json.loads(message)


class Client:
    """Client class that store in 'online_clients' dict & 'Room' object"""

    def __init__(self, websocket: websockets.legacy.server.WebSocketServerProtocol,
                 client_id, room_key="") -> None:
        self.socket = websocket
        self.client_id: str = client_id
        self.room_key: str = room_key
        self.private: bool = False

    def add_public_room_key(self, room_key: str) -> None:
        """Update room key for public room."""
        self.room_key: str = room_key

    def add_private_room_key(self, room_key: str) -> None:
        """Update room key for private room."""
        self.room_key: str = room_key
        self.private = True


class Room:
    """A room contains a maximum of 4 players. If 4 players are present in the room the game starts."""

    def __init__(self, room_key) -> None:
        self.room_key: str = room_key
        self.clients: Dict[str, Client] = {}
        self.socket_list: List = []  # list of websocket object ( for brocasting )
        self.game_status: Dict = {"winner": None}
        self.private: bool = False

    def get_room_size(self) -> int:
        """Return current room size"""
        return len(self.clients)

    def add_player(self, client_id: str) -> None:
        """Adds the player in the room."""
        self.clients[client_id] = online_clients[client_id]
        self.socket_list.append(online_clients[client_id].socket)

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


async def waiting(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """Handle player waiting untill room size == 4"""
    print("enter waiting loop")
    async for message in websocket:
        event = decode_json(message)

        print("wait: ", event)
        if event["type"] == "start":
            print(" break waiting loop ! ")
            break


async def play_private(websocket: websockets.legacy.server.WebSocketServerProtocol,
                       client_id: str, current_room: Room):
    """Receive and process moves from a player.( Private Game )"""
    print("Private Game start !")
    try:
        async for message in websocket:
            event = decode_json(message)
            print(event)

            # Game logic
            print(" current room size:", current_room.get_room_size())
            await websocket.send(encode_json({"type": "debug", "room_size": current_room.get_room_size(), }))

            if event["type"] == "player_disconnect" and current_room.get_room_size() == 1:

                await error(websocket, encode_json("All the other player left the game !"))
                break
            if current_room.game_status["winner"]:

                print("The winner is ", current_room.game_status["winner"])
                break
    finally:
        # remove player from room
        del current_room.clients[client_id]
        pass


async def play_public(websocket: websockets.legacy.server.WebSocketServerProtocol, client_id: str, current_room: Room):
    """Receive and process moves from a player.( Public Game )"""
    print("Public Game start !")

    try:
        async for message in websocket:
            event = decode_json(message)
            print(event)

            # Game logic

            if event["type"] == "player_disconnect":
                print("The public game end becase player disconnect")

                await error(websocket, "The public game end becase player disconnect")
                return
            if current_room.game_status["winner"]:

                print("The winner is ", current_room.game_status["winner"])
                return
    finally:
        # remove player from room
        del current_room.clients[client_id]
        pass


async def create_private_room(websocket: websockets.legacy.server.WebSocketServerProtocol, client_id: str):
    """Handle a connection from the room owner ( the player that create private room )"""
    room_key = secrets.token_urlsafe(6)
    private_rooms[room_key] = Room(room_key)
    private_rooms[room_key].add_player(client_id)

    online_clients[client_id].add_private_room_key(room_key)

    try:
        # Send the secret access tokens to the browser of the first player,
        # where they'll be used for building "room_key" and "watch" links.
        event = {
            "type": "init",
            "room_key": room_key,
        }
        await websocket.send(encode_json(event))

        await waiting(websocket)
        await play_private(websocket, client_id, private_rooms[room_key])

    finally:
        pass


async def join_private_game(websocket: websockets.legacy.server.WebSocketServerProtocol,
                            client_id: str, room_key: str):
    """Handle a connection from the other player ( except the one who create room )"""
    try:
        current_room = private_rooms[room_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    current_room.add_player(client_id)
    online_clients[client_id].add_private_room_key(room_key)

    event = {
        "type": "player_join",
        "player": client_id,
    }
    websockets.broadcast(current_room.socket_list, encode_json(event))

    try:
        if current_room.get_room_size() == ROOM_SIZE:
            # current player is the fourth player that join the game.
            event = {
                "type": "start",
            }
            websockets.broadcast(current_room.socket_list, encode_json(event))
            # brocadcast start event to all players in the room
            # ( break waiting loop for other players )

            await play_private(websocket, client_id, current_room)
        else:
            await waiting(websocket)
            await play_private(websocket, client_id, current_room)
    finally:
        # print("join private play finally : " , client_id )
        # del current_room.clients[ client_id ]
        pass


async def create_public_room(websocket: websockets.legacy.server.WebSocketServerProtocol, client_id):
    """Create public room

    The function will be called when :

        1. when 'ROOMS' is empty
        2. when the last room from 'ROOMS' is full
    """
    print("create public game\n")

    # create new room
    room_key = secrets.token_urlsafe(6)
    public_rooms_keys.append(room_key)
    public_rooms[public_rooms_keys[-1]] = Room(room_key)
    public_rooms[room_key].add_player(client_id)

    online_clients[client_id].add_public_room_key(room_key)

    try:
        event = {
            "type": "init",
        }
        await websocket.send(encode_json(event))

        await waiting(websocket)
        await play_public(websocket, client_id, public_rooms[room_key])
    finally:
        pass


async def join_public_game(websocket: websockets.legacy.server.WebSocketServerProtocol, client_id):
    """Handle a connection that player joined public game."""
    print("join public game\n")

    if (len(public_rooms_keys) == 0) or (public_rooms[public_rooms_keys[-1]].get_room_size() == ROOM_SIZE):
        # the situation that player become room creater
        await create_public_room(websocket, client_id)

    else:
        # the last room is <= ROOM_SIZE
        last_room_key = public_rooms_keys[-1]
        current_room = public_rooms[last_room_key]
        # add current player to current room
        current_room.add_player(client_id)
        online_clients[client_id].add_public_room_key(last_room_key)

        # broadcast new player join message
        event = {
            "type": "player_join",
            "player": client_id,
        }
        websockets.broadcast(current_room.socket_list, encode_json(event))

        try:
            if current_room.get_room_size() == ROOM_SIZE:
                # current player is the fourth player that join the game.
                event = {
                    "type": "start",
                }
                websockets.broadcast(current_room.socket_list, encode_json(event))
                # brocadcast start event to all players in the room
                # ( break waiting loop for other players )

                await play_public(websocket, client_id, current_room)
            else:
                await waiting(websocket)
                await play_public(websocket, client_id, current_room)
        finally:
            # del current_room.clients[ client_id ]
            pass


async def handler(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """Handle a connection and dispatch it according to who is connecting."""
    print("called")
    try:
        print("player online !")
        # add current player to global online client dictionary
        client_id = secrets.token_urlsafe(6)
        online_clients[client_id] = Client(websocket, client_id)

        async for message in websocket:
            event = decode_json(message)
            print("message : ", event)

            if event["type"] == "join":

                print(" player join ")

                if "room_key" in event:
                    # player join private room
                    await join_private_game(websocket, client_id, event["room_key"])
                else:
                    # player join public room
                    await join_public_game(websocket, client_id)

            elif event["type"] == "create":
                # The player create private room
                print(" player create private room ")
                await create_private_room(websocket, client_id)
    finally:
        print("player life cycle end", client_id)

        if len(online_clients[client_id].room_key) > 0:
            # if player have joined the game
            event = {
                "type": "player_disconnect",
                "player": client_id,
            }

            if online_clients[client_id].private:
                # player join private room
                websockets.broadcast(private_rooms[online_clients[client_id].room_key].socket_list, encode_json(event))
            else:
                # join public room
                websockets.broadcast(public_rooms[online_clients[client_id].room_key].socket_list, encode_json(event))

        del online_clients[client_id]


async def main():
    """To get the server started at the uri "ws://localhost:8001"."""
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == "__main__":
    print("connected!")
    asyncio.run(main())
