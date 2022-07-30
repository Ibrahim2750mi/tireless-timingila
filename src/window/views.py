import asyncio
import json
import webbrowser
from random import randint

import arcade
import arcade.gui
import websockets
import websockets.exceptions

from config import PATH, SCREEN_HEIGHT, SCREEN_WIDTH

STYLE_WHITE = {"font_name": "Dilo World", "font_color": (255, 255, 255), "bg_color": (202, 201, 202),
               "border_color": (119, 117, 119)}

STYLE_RED = {"font_name": "Dilo World", "font_color": (255, 0, 0), "bg_color": (202, 201, 202),
             "border_color": (119, 117, 119)}

MENU_BACKGROUND = arcade.load_texture(f"{PATH}assets/backgrounds/menu_bg.jpg", width=SCREEN_WIDTH,
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

        arcade.load_font(f"{PATH}assets/fonts/DiloWorld-mLJLv.ttf")

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
        async with websockets.connect("ws://localhost:8002") as ws:
            try:
                await ws.send(encode_json(event))
                msg = await ws.recv()
                print(msg)
                event = decode_json(msg)
                self.client_id = event.get("player", self.client_id)
                self.room_key = event.get("room", self.room_key)

                num_players = int(event.get("length", 0))
                client_data = event.get("client_data", 0)

                if num_players == 4:
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

    def on_show_view(self):
        """Called when the current is switched to this view."""
        self.setup()

    def setup(self):
        """Set up the game variables. Call to re-start the game."""
        pass

    def on_draw(self):
        """Called when this view should draw."""
        self.clear()
