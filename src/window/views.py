import asyncio
import json
import webbrowser
from random import randint

import arcade
import arcade.gui
import websockets
import websockets.exceptions

from config import PATH, SCREEN_HEIGHT, SCREEN_WIDTH


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
        self.background = arcade.load_texture(f"{PATH}assets/backgrounds/menu_bg.jpg",
                                              width=SCREEN_WIDTH, height=SCREEN_HEIGHT)

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

        style_white = {"font_name": "Dilo World", "font_color": (255, 255, 255), "bg_color": (202, 201, 202),
                       "border_color": (119, 117, 119)}

        style_red = {"font_name": "Dilo World", "font_color": (255, 0, 0), "bg_color": (202, 201, 202),
                     "border_color": (119, 117, 119)}

        play_button = arcade.gui.UIFlatButton(text="PLAY", width=200, style=style_white)
        play_button.on_click = self._on_click_play_button
        create_lobby_button = arcade.gui.UIFlatButton(text="Create Lobby", width=200, style=style_white)
        dummy_play_button = arcade.gui.UIFlatButton(text="Play", width=200, style=style_red)
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
        """Render the screen."""
        self.clear()

        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background)
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
    Waiting screen view.

    :param main_window: Main window in which the view is shown.
    """

    def __init__(self, main_window: arcade.Window):
        super().__init__(main_window)

        self.main_window = main_window

        self.v_box = None
        self.manager = None

        self.name_input_box = None

        self.client_id = None
        self.room_key = None

        self.all_player_ids = None

        self.lambda_client = None

    def on_show_view(self) -> None:
        """Called when the current is switched to this view."""
        self.setup()

    def setup(self) -> None:
        """Set up the view."""
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.name_input_box = arcade.gui.UIInputText(text="Enter your name here", width=250, height=20)
        name_input_box_border = self.name_input_box.with_border(width=2, color=(0, 0, 0))
        find_players_button = arcade.gui.UIFlatButton(text="Find players", width=250)
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
        """Render the view."""
        self.clear()

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
                self.client_id = event["player"] if event.get("player", None) else self.client_id
                self.room_key = event["room"] if event.get("room", None) else self.room_key

                num_players = int(event['length']) if event.get("length", None) else 0
                client_data = event['client_data'] if event.get("client_data", None) else 0

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
    Game view.

    :param main_window: Main window in which the view is shown.
    """

    def __init__(self, main_window: arcade.Window, player_ids, player_name, player_id, room_id):
        super().__init__(main_window)
        self.main_window = main_window

    def on_show_view(self):
        """Called when the current is switched to this view."""
        self.setup()

    def setup(self):
        """Set up the view."""
        pass

    def on_draw(self):
        """Render the view."""
        self.clear()
