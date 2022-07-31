#!/usr/bin/env python

import asyncio
import json
import secrets

import websockets
import websockets.legacy.server

from chemistry import Reaction, get_reaction
from config import ROOM_SIZE

# Global varibales
online_clients: dict[str, "Client"] = {}
private_rooms: dict[str, "Room"] = {}
public_rooms: dict[str, "Room"] = {}
public_rooms_keys: list[str] = []
planned_disconnection: list[str] = []


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
        self.name: str = None

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
        self.clients: dict[str, Client] = {}
        self.socket_list: list = []  # list of websocket object ( for brocasting )
        self.game_status: dict = {"winner": None, "started": False, "confirmed participants": [], "turn": 0}
        self.private: bool = False

        self.reaction: Reaction = None

    def __len__(self):
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
    message = await websocket.recv()
    event = decode_json(message)

    print("wait: ", event)
    if event["type"] == "start":
        print(" break waiting loop ! ")


async def play_private(websocket: websockets.legacy.server.WebSocketServerProtocol,
                       client_id: str, current_room: Room):
    """Receive and process moves from a player.( Private Game )"""
    print("Private Game start !")
    try:
        async for message in websocket:
            event = decode_json(message)
            print(event)

            # Game logic
            print(" current room size:", len(current_room))
            await websocket.send(encode_json({"type": "debug", "room_size": len(current_room), }))

            if event["type"] == "player_disconnect" and len(current_room) == 1:
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
            "player": client_id,
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

    # add current player to current room
    current_room.add_player(client_id)
    online_clients[client_id].add_private_room_key(room_key)

    # broadcast new player join message
    event = {
        "type": "player_join",
        "player": client_id,
        "room": room_key,
    }
    websockets.broadcast(current_room.socket_list, encode_json(event))

    try:
        if len(current_room) == ROOM_SIZE:
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
            "player": client_id,
            "room": room_key,
        }
        await websocket.send(encode_json(event))

        await waiting(websocket)
        await play_public(websocket, client_id, public_rooms[room_key])
    finally:
        pass


async def join_public_game(websocket: websockets.legacy.server.WebSocketServerProtocol, client_id):
    """Handle a connection that player joined public game."""
    print("join public game\n")

    if (len(public_rooms_keys) == 0) or (len(public_rooms[public_rooms_keys[-1]]) == ROOM_SIZE):
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
            "room": last_room_key
        }
        websockets.broadcast(current_room.socket_list, encode_json(event))

        try:
            if len(current_room) == ROOM_SIZE:
                # current player is the fourth player that join the game.

                client_ids = tuple(current_room.clients.keys())
                client_names = []
                for client in client_ids:
                    client_names.append(online_clients[client].name)
                client_data = dict(zip(client_ids, client_names))
                current_room.game_status['started'] = True
                event = {
                    "type": "reply_room_status",
                    "length": len(current_room),
                    "client_data": client_data,
                    "started": True
                }
                await websocket.send(encode_json(event))

                # websockets.broadcast(current_room.socket_list, encode_json(event))

                # brocadcast start event to all players in the room
                # ( break waiting loop for other players )

                # await play_public(websocket, client_id, current_room)
            else:
                await waiting(websocket)
                await play_public(websocket, client_id, current_room)
        finally:
            # del current_room.clients[ client_id ]
            pass


async def handler(websocket: websockets.legacy.server.WebSocketServerProtocol):
    """Handle a connection and dispatch it according to who is connecting."""
    client_id = ""

    try:
        print("player online !")
        # add current player to global online client dictionary

        async for message in websocket:
            event = decode_json(message)
            print("message : ", event)

            if event["player"] is None:
                client_id = secrets.token_urlsafe(6)
                online_clients[client_id] = Client(websocket, client_id)
                online_clients[client_id].name = event["player_name"]
            else:
                client_id = event["player"]

            if event["auto_disconnect"]:
                planned_disconnection.append(client_id)

            match event["type"]:

                case "ping":
                    pass

                case "join":

                    print("player join")

                    if "room_key" in event:
                        # player join private room
                        await join_private_game(websocket, client_id, event["room_key"])
                    else:
                        # player join public room
                        await join_public_game(websocket, client_id)

                case "create":
                    # The player create private room
                    print("player create private room")
                    await create_private_room(websocket, client_id)

                case "room_status":
                    room = None
                    if public_rooms.get(event["room"], None) is not None:
                        room = public_rooms[event['room']]
                    elif private_rooms.get(event["room"], None) is not None:
                        room = private_rooms[event['room']]
                    else:
                        event = {
                            "type": "bad request"
                        }

                    if room:
                        client_ids = tuple(room.clients.keys())
                        client_names = []
                        for client in client_ids:
                            client_names.append(online_clients[client].name)
                        client_data = dict(zip(client_ids, client_names))

                        event = {
                            "type": "reply_room_status",
                            "length": len(room),
                            "client_data": client_data,
                        }
                    await websocket.send(encode_json(event))
                case "get_reaction_pub":
                    room = public_rooms[event['room']]
                    reaction = room.reaction
                    if not room.reaction:
                        reaction = get_reaction()
                        room.reaction = reaction

                    omit_number = tuple(public_rooms[event['room']].clients.keys()).index(client_id)
                    await websocket.send(encode_json(reaction.json(omit_number)))
                case "turn_status_pub":
                    room = public_rooms[event['room']]
                    omit_number = tuple(public_rooms[event['room']].clients.keys()).index(client_id)
                    reactants = room.reaction.reactants.copy()
                    plus_index = reactants.index(" ")
                    reactants.remove(" ")
                    reactants[omit_number] = "XX"
                    reactants.insert(plus_index, " + ")
                    event = {
                        "type": "turn_reply",
                        "turn": room.game_status['turn'],
                        "reaction": ''.join(reactants),
                    }
                    await websocket.send(encode_json(event))
                case "select_option_pub":
                    room = public_rooms[event['room']]
                    reactants = room.reaction.reactants
                    plus_index = reactants.index(" ")
                    reactants.remove(" ")
                    reactants[event['index']] = event['option']
                    reactants.insert(plus_index, " ")

                    room.game_status['turn'] = event['turn']
                    if room.game_status['turn'] == ROOM_SIZE:
                        room.reaction = None
                        room.game_status['turn'] = 0
                    event = {
                        "type": "option_reply",
                        'turn': room.game_status['turn'],
                    }
                    await websocket.send(encode_json(event))
    finally:
        if client_id in planned_disconnection:
            planned_disconnection.remove(client_id)
            return
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
    asyncio.run(main())
