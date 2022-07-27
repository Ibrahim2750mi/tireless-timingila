#!/usr/bin/env python

import asyncio
import json
import secrets
from time import sleep

import websockets


class Client:
    """
    Client class that store in 'ONLINE_CLIENT' dict & 'Room' object
    """
    def __init__(self ,_websocket ,_client_id ,_room_key ) -> None:
        self.socket = _websocket # websocket object 
        self.client_id:str = _client_id
        self.room_key:str = _room_key

class Room:
    """
    Room class
    """
    def __init__(self , _room_key) -> None:
        self.room_key:str = _room_key
        self.clients: dict[ str , Client ] = None 
        self.socket_list:list = None # list of websocket object ( for brocasting )
        self.game_status:dict = None

    def get_room_size(self) -> int :
        return len( self.clients )

    def add_player( self , client_id:str ) -> None :
        self.clients[client_id] = ONLINE_CLIENT[ client_id]
        self.socket_list.append( ONLINE_CLIENT[ client_id].socket )

    def remove_player( self , client_id:str ) -> None :
        self.socket_list.remove( self.clients[client_id].socket )
        del self.clients[client_id]

# Global varibales 
ROOM_SIZE = 4 
WAITING_SECOND = 3
ONLINE_CLIENT = {} # { client_id , Client }  : dict[str,Client]
PRIVATE_ROOMS = {} # { room_key , Room }  : dict[str,Room]
PUBLIC_ROOMS  = {} # { room_key , Room }  : list[Room] 

# helper function ( dict -> str of json )
def encode_json(message) -> str :
    return json.dumps( message, ensure_ascii=False)

# helper function ( str of json -> dict )
def decode_json(message) -> dict :
    return json.loads( message )

async def error(websocket, message):
    """
    Send an error message.
    """
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send( encode_json(event) )


async def play(websocket, current_room:Room ):
    """
    Receive and process moves from a player.
    """
    if current_room.get_room_size() == ROOM_SIZE :

        async for message in websocket:
            
            """
            Unfinish part : 
                Still waiting for game logic & game stucture etc...
            """

            websocket.send( encode_json(message) )

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

    
    elif current_room.get_room_size() < ROOM_SIZE :
        # waiting for player 
        event = {
                "type": "waiting",
        }
        websocket.send( json.dumps(event) )
        sleep( WAITING_SECOND )

    else :
        # the room is full
        error( websocket , "The room is full !" )

async def create_private_room(websocket):
    """
    Handle a connection from the room owner ( the player that create private room )
    """
    # Initialize a Connect Four game, the set of WebSocket connections
    # receiving moves from this game, and secret access tokens.
    

    client_id = secrets.token_urlsafe(6)
    room_key = secrets.token_urlsafe(6)

    ONLINE_CLIENT[ client_id ] = Client( websocket , client_id , room_key )
    PRIVATE_ROOMS[ room_key ] = Room( room_key )
    PRIVATE_ROOMS[ room_key ].add_player( client_id )

    try:
        # Send the secret access tokens to the browser of the first player,
        # where they'll be used for building "room_key" and "watch" links.
        event = {
            "type": "init",
            "room_key": room_key ,
        }

        await websocket.send( json.dumps(event) )
        # Receive and process moves from the first player.
        await play( websocket , PRIVATE_ROOMS[ room_key ] )

    finally:
        del ONLINE_CLIENT[client_id]
        del PRIVATE_ROOMS[room_key]


async def join_private_game(websocket, room_key):
    """
    Handle a connection from the other player ( except the one who create room )
    Join room by 'room_key'
    """
    # Find the Connect Four game.
    try:
        current_room = PRIVATE_ROOMS[room_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    # add current player to global ONLINE_CLIENT dict
    client_id = secrets.token_urlsafe(6)
    ONLINE_CLIENT[client_id] = Client( websocket , client_id ,room_key )

    current_room.add_player( client_id )

    try:
        # Receive and process moves from the other 
        await play( websocket , current_room )
    finally:
        del current_room.clients[ client_id ]

async def create_public_room( websocket ):
    """
    The function will be called when :
        1. when 'ROOMS' is empty
        2. when the last room from 'ROOMS' is full
    """

    print( "create public game\n" )

    client_id = secrets.token_urlsafe(6)
    room_key = secrets.token_urlsafe(6)

    ONLINE_CLIENT[ client_id ] = Client( websocket , client_id , room_key )
    PUBLIC_ROOMS.append( Room( room_key ) )
    PRIVATE_ROOMS[-1].add_player( client_id )

    try:
        # Send the secret access tokens to the browser of the first player,
        # where they'll be used for building "room_key" and "watch" links.
        event = {
            "type": "init",
            "room_key": room_key ,
        }

        await websocket.send( json.dumps(event) )
        # Receive and process moves from the first player.
        await play( websocket , PRIVATE_ROOMS[ room_key ] )

    finally:
        del ONLINE_CLIENT[client_id]
        del PRIVATE_ROOMS[room_key]

async def join_public_game( websocket ):
    """
    Handle a connection that player joined public game.
    """
    print( "join public game\n" )

    if( (len(PUBLIC_ROOMS) == 0 ) or ( len(PUBLIC_ROOMS[-1]) == ROOM_SIZE ) ):
        # the situation that player become room creater
        create_public_room( websocket )
    
    else: # the last room is <= ROOM_SIZE 
        
        current_room = PRIVATE_ROOMS[-1]

        # add current player to global online client dict
        client_id = secrets.token_urlsafe(6)
        ONLINE_CLIENT[client_id] = Client( websocket , client_id , current_room.room_key )

        current_room.add_player( client_id )

        try:
            # Receive and process moves from the second player.
            await play( websocket , current_room )
        finally:
            del current_room.clients[ client_id ]

async def handler(websocket):
    """
    Handle a connection and dispatch it according to who is connecting.
    """
    # Receive and parse the "init" event from the UI.
    message = await websocket.recv()
    event = decode_json( message )

    if "join" in event:
        if "room_key" in event:
            # player join private room
            await join_private_game(websocket, event["room_key"])
        else:
            # player join public room
            await join_public_game( websocket )
    elif "create" in event:
        # The player create private room
        await create_private_room(websocket)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
