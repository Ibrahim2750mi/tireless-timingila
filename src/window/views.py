import asyncio
import json
import time
import webbrowser
from functools import partial
from random import randint

import arcade
import arcade.gui
import nest_asyncio
import websockets
import websockets.exceptions

from config import (
    ASSET_PATH, ROOM_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH, WAITING_SECOND
)

nest_asyncio.apply()

FONT_COLOR_WHITE = (255, 255, 255)
FONT_COLOR_RED = (255, 0, 0)
STYLE_WHITE = {"font_name": "Dilo World", "font_color": FONT_COLOR_WHITE, "bg_color": (202, 201, 202),
               "border_color": (119, 117, 119)}

STYLE_RED = {"font_name": "Dilo World", "font_color": FONT_COLOR_RED, "bg_color": (202, 201, 202),
             "border_color": (119, 117, 119)}

MENU_BACKGROUND = arcade.load_texture(str(ASSET_PATH / "backgrounds" / "menu_bg.jpg"), width=SCREEN_WIDTH,
                                      height=SCREEN_HEIGHT)


def encode_json(message) -> str:
    """Helper function ( dict -> str of json )"""
    return json.dumps(message, ensure_ascii=False)


def decode_json(message) -> dict:
    """Helper function ( str of json -> dict )"""
    return json.loads(message)


class Menu(arcade.View):
    """
    Menu view.

    :param main_window: Main window in which the view is shown.
    """

    def __init__(self, main_window: arcade.Window):
        super().__init__(main_window)
        self.main_window = main_window

        self.v_box = None
        self.v_box_heading = None

        self.manager = None

        arcade.load_font(str(ASSET_PATH / "fonts" / "DiloWorld-mLJLv.ttf"))

    def on_show_view(self) -> None:
        """Called when the current is switched to this view."""
        self.setup()

    def setup(self) -> None:
        """Set up the game variables. Call to re-start the game."""
        self.v_box = arcade.gui.UIBoxLayout(space_between=30)
        self.v_box_heading = arcade.gui.UIBoxLayout()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        play_button = arcade.gui.UIFlatButton(text="PLAY", width=200, style=STYLE_WHITE)
        play_button.on_click = self._on_click_play_button
        create_lobby_button = arcade.gui.UIFlatButton(text="Create Lobby", width=200, style=STYLE_WHITE)
        dummy_play_button = arcade.gui.UIFlatButton(text="Play", width=200, style=STYLE_RED)
        dummy_play_button.on_click = self._on_click_dummy_play_button

        self.v_box.add(play_button)
        self.v_box.add(create_lobby_button)
        self.v_box.add(dummy_play_button)

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                child=self.v_box
            )
        )

    def on_draw(self) -> None:
        """Called when this view should draw."""
        self.clear()

        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            MENU_BACKGROUND)
        self.manager.draw()

    def _on_click_dummy_play_button(self, _: arcade.gui.UIOnClickEvent) -> None:
        """
        Do one of three things when the dummy play button is pressed.

        [0] Open a URL using the `webbrowser` module. (The same module used by `import antigravity`)
        [1] Close the window and exit python.
        [2] Do both.
        """
        if (picked := randint(0, 2)) != 1:
            webbrowser.open_new("https://youtu.be/fujCdB93fpw")
        if picked:
            self.main_window.close()
            arcade.exit()
            raise SystemExit

    def _on_click_play_button(self, _: arcade.gui.UIOnClickEvent) -> None:
        waiting_screen = WaitingScreen(self.main_window)
        self.main_window.show_view(waiting_screen)


class WaitingScreen(arcade.View):
    """
    Waiting screen view. Here the player is chooses their name and joins a game.

    :param main_window: Main window in which it showed.
    """

    def __init__(self, main_window: arcade.Window):
        super().__init__(main_window)

        self.main_window = main_window

        self.v_box = None
        self.manager = None

        self.name_input_box = None

        self.client_id = None
        self.client_data = None
        self.room_key = None

        self.all_player_ids = None

        self.lambda_client = None

    def on_show_view(self) -> None:
        """Called once when the view is shown."""
        self.setup()

    def setup(self) -> None:
        """Set up the game variables. Call to re-start the game."""
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.name_input_box = arcade.gui.UIInputText(text="Enter your name here", width=250, height=20,
                                                     text_color=(255, 0, 0), font_name="Dilo World")
        name_input_box_border = self.name_input_box.with_border(width=2, color=(119, 117, 119))
        find_players_button = arcade.gui.UIFlatButton(text="Find players", width=250, style=STYLE_WHITE)
        find_players_button.on_click = self._on_click_find_players_button

        self.v_box.add(name_input_box_border)
        self.v_box.add(find_players_button)

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center",
                anchor_y="center",
                child=self.v_box
            )
        )

    def on_draw(self) -> None:
        """Called when this view should draw."""
        self.clear()

        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            MENU_BACKGROUND)
        arcade.draw_rectangle_filled(self.name_input_box.x + 125, self.name_input_box.y + 10,
                                     250, 20, (202, 201, 202))
        self.manager.draw()

    def _on_click_find_players_button(self, _: arcade.gui.UIOnClickEvent):
        join_event = {
            "type": "join",
            "player": self.client_id,
            "auto_disconnect": True,
            "player_name": self.name_input_box.text,
        }

        asyncio.run(self.client(join_event))
        room_status_event = {
            "type": "room_status",
            "player": self.client_id,
            "auto_disconnect": True,
            "room": self.room_key
        }

        self.lambda_client = lambda _: asyncio.run(self.client(room_status_event))

        arcade.schedule(self.lambda_client, 3)

    async def client(self, event):
        """Client side for the waiting screen."""
        async with websockets.connect("ws://localhost:8001") as ws:
            try:
                await ws.send(encode_json(event))
                msg = await ws.recv()
                event = decode_json(msg)
                self.client_id = event.get("player", self.client_id)
                self.room_key = event.get("room", self.room_key)

                num_players = int(event.get("length", 0))
                client_data = event.get("client_data", 0)

                if num_players == ROOM_SIZE:
                    self.client_data = client_data
                    arcade.unschedule(self.lambda_client)
                    game = Game(self.main_window, self.client_data, self.name_input_box.text, self.client_id,
                                self.room_key)
                    self.main_window.show_view(game)
                    return

            except websockets.exceptions.ConnectionClosedOK as e:
                print(e)


class Game(arcade.View):
    """
    Main game logic goes here.

    :param main_window: Main window in which it showed.
    """

    def __init__(self, main_window: arcade.Window, all_player_data: dict[str, str], player_name: str, player_id: str,
                 room_id: str):
        super().__init__(main_window)
        self.main_window = main_window

        self.all_player_data = all_player_data
        self.player_name = player_name
        self.player_id = player_id
        self.room_id = room_id

        self.reaction = {}

        self.v_box = None
        self.v_box_top = None
        self.h_box_top = None
        self.manager = None

        self.name_labels = []
        self.round_label: arcade.gui.UILabel = None
        self.current_turn: arcade.gui.UILabel = None
        self.current_label: arcade.gui.UILabel = None
        self.reaction_label: arcade.gui.UILabel = None

        self.player_names = None
        self.option = None

        self.round = 1
        self.turn_index = 0

        self.lambda_client = None

    def on_show_view(self):
        """Called when the current is switched to this view."""
        event = {
            "type": "get_reaction_pub",
            "player": self.player_id,
            "auto_disconnect": True,
            "room": self.room_id
        }
        asyncio.run(self.client(event))

        time.sleep(0.5)

    def get_turn(self):
        """Will schedule to send a type "turn_status_pub" event to the server."""
        if self.turn_index != self.reaction['index']:
            event = {
                "type": "turn_status_pub",
                "player": self.player_id,
                "room": self.room_id,
                "auto_disconnect": True,
            }

            self.lambda_client = lambda _: asyncio.run(self.client(event))
            arcade.schedule(self.lambda_client, WAITING_SECOND)

    def setup(self):
        """Set up the game variables. Call to re-start the game."""
        self.player_names = tuple(self.all_player_data.values())

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.h_box_top = arcade.gui.UIBoxLayout(vertical=False, space_between=200)
        # switch font color to red just to test if it's working
        self.round_label = arcade.gui.UILabel(text=f"Round {self.round} of 3", text_color=FONT_COLOR_RED,
                                              font_name="Dilo World")
        self.h_box_top.add(self.round_label)
        # self.h_box_top.add(reaction_label)

        self.v_box_top = arcade.gui.UIBoxLayout(space_between=20)
        self.reaction_label = arcade.gui.UILabel(
            text=f"Recipe is: {self.reaction['reaction']}",
            width=450,
            text_color=FONT_COLOR_RED,
            font_size=20,
            height=50,
        )
        self.reaction_label.fit_content()
        v_box_h_box = arcade.gui.UIBoxLayout(vertical=False)
        for option in self.reaction['options']:
            mod_style = STYLE_WHITE
            mod_style["font_name"] = "Arial"
            option_method = partial(self._on_click_option, option=option)
            options_button = arcade.gui.UIFlatButton(text=option, width=250 / 4, style=mod_style)
            options_button.on_click = option_method
            v_box_h_box.add(options_button)

        self.current_turn = arcade.gui.UILabel(text=f"{self.player_names[self.turn_index]}'s Turn",
                                               font_name="Dilo World", text_color=FONT_COLOR_RED, width=250, height=30)
        self.current_turn.fit_content()

        self.current_label = arcade.gui.UILabel(
            text=f"Current reaction is: {self.reaction['current_reaction']}",
            width=300,
            text_color=FONT_COLOR_RED,
            font_size=12,
            height=50,
        )
        self.current_label.fit_content()
        self.v_box_top.add(self.reaction_label)
        self.v_box_top.add(v_box_h_box)
        self.v_box_top.add(self.current_turn)
        self.v_box_top.add(self.current_label)

        self.v_box = arcade.gui.UIBoxLayout(space_between=20)

        for name in self.player_names:
            style = FONT_COLOR_WHITE
            if name == self.player_name:
                style = FONT_COLOR_RED
            label = arcade.gui.UILabel(text=name, font_name="Dilo World", text_color=style, width=250, height=30)
            label_border = label.with_border(width=4, color=(119, 117, 119))
            self.name_labels.append(label)
            self.v_box.add(label_border)

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="left",
                anchor_y="top",
                align_x=20,
                child=self.h_box_top
            )
        )

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="left",
                anchor_y="center",
                align_x=20,
                child=self.v_box
            )
        )

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center",
                anchor_y="top",
                child=self.v_box_top
            )
        )

    def on_draw(self):
        """Called when this view should draw."""
        self.clear()

        for label in self.name_labels:
            arcade.draw_rectangle_filled(label.x + label.width / 2, label.y + label.height / 2,
                                         label.width, label.height, (202, 201, 202))

        self.manager.draw()

    def _on_click_option(self, _: arcade.gui.UIOnClickEvent, option):
        if self.reaction["index"] != self.turn_index:
            return
        self.option = option
        mod_reactants = self.reaction['reactants'].copy()
        plus_index = mod_reactants.index(" ")
        mod_reactants.remove(" ")
        mod_reactants[self.reaction['index']] = self.option
        mod_reactants.insert(plus_index, " + ")

        self.reaction['current_reaction'] = ''.join(mod_reactants)

        self.turn_index += 1

        event = {
            "type": "select_option_pub",
            "option": self.option,
            "player": self.player_id,
            "room": self.room_id,
            "turn": self.turn_index,
            "auto_disconnect": True,
            "index": self.reaction['index'],
        }

        asyncio.run(self.client(event))

    async def client(self, event):
        """Client side for the waiting screen."""
        async with websockets.connect("ws://localhost:8001") as ws:
            try:
                await ws.send(encode_json(event))
                msg = await ws.recv()
                event_recv = decode_json(msg)
                print(event_recv)
                match event["type"]:
                    case "get_reaction_pub":
                        self.reaction['reaction_original'] = event_recv['reaction_original']
                        self.reaction['reaction'] = event_recv['reaction']
                        self.reaction['reactants'] = event_recv['reactants']
                        self.reaction['products'] = event_recv["products"]
                        self.reaction['options'] = event_recv['options']
                        self.reaction['index'] = event_recv['index']
                        self.reaction["current_reaction"] = event_recv["reaction"]
                        if self.manager:
                            self.manager.clear()
                        self.setup()
                        self.get_turn()
                    case "select_option_pub":
                        print(event_recv)
                        event = {
                            "type": "turn_status_pub",
                            "player": self.player_id,
                            "room": self.room_id,
                            "auto_disconnect": True,
                        }
                        if event_recv['turn'] == 0:
                            self.round += 1
                            event = {
                                "type": "get_reaction_pub",
                                "player": self.player_id,
                                "auto_disconnect": True,
                                "room": self.room_id
                            }
                            self.turn_index = event_recv['turn']
                            asyncio.run(self.client(event))
                            return

                        self.turn_index = event_recv['turn']
                        self.current_turn.text = f"{self.player_names[event_recv['turn']]}'s Turn"
                        self.current_turn.fit_content()

                        self.current_label.text = f"Current reaction is: {self.reaction['current_reaction']}"
                        self.current_label.fit_content()

                        print(event)
                        self.lambda_client = lambda _: asyncio.run(self.client(event))
                        arcade.schedule(self.lambda_client, WAITING_SECOND)
                    case "turn_status_pub":
                        # round end
                        if event_recv['turn'] < self.turn_index:
                            print("round changed")
                            self.round += 1

                            event = {
                                "type": "get_reaction_pub",
                                "player": self.player_id,
                                "auto_disconnect": True,
                                "room": self.room_id
                            }
                            self.turn_index = event_recv['turn']
                            asyncio.run(self.client(event))

                        elif event_recv['turn'] == self.reaction['index']:
                            arcade.unschedule(self.lambda_client)
                            self.reaction["current_reaction"] = event_recv["reaction"].replace("XX", self.option)
                            self.turn_index = event_recv['turn']

                            self.manager.clear()
                            self.setup()

                        elif event_recv['turn'] != self.reaction['index']:
                            self.turn_index = event_recv['turn']
                            self.reaction['current_reaction'] = event_recv['reaction']

                            self.current_turn.text = f"{self.player_names[self.turn_index]}'s Turn"
                            self.current_turn.fit_content()

                            self.current_label.text = f"Current reaction is: {self.reaction['current_reaction']}"
                            self.current_label.fit_content()

                    case _:
                        pass

            except Exception as e:
                raise e
