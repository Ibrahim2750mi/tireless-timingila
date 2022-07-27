import webbrowser
from random import randint

import arcade
import arcade.gui


class Menu(arcade.View):
    """
    Menu view.

    :param main_window: Main window in which it showed.
    """

    def __init__(self, main_window: arcade.Window):
        super().__init__(main_window)
        self.main_window = main_window

        self.v_box = None
        self.manager = None

    def on_show_view(self) -> None:
        """Called when the current is switched to this view."""
        self.setup()

    def setup(self) -> None:
        """Set up the game variables. Call to re-start the game."""
        self.v_box = arcade.gui.UIBoxLayout()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        play_button = arcade.gui.UIFlatButton(text="PLAY", width=200)
        play_button.on_click = self._on_click_play_button
        dummy_play_button = arcade.gui.UIFlatButton(text="VIP PLAY", width=200)
        dummy_play_button.on_click = self._on_click_dummy_play_button

        self.v_box.add(play_button)
        self.v_box.add(dummy_play_button)

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="left",
                anchor_y="bottom",
                align_x=250,
                align_y=100,
                child=self.v_box
            )
        )

    def on_draw(self) -> None:
        """Render the screen."""

        self.clear()

        self.manager.draw()

    def _on_click_dummy_play_button(_self, _: arcade.gui.UIOnClickEvent) -> None:
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
    def __init__(self, main_window):
        super().__init__(main_window)

        self.main_window = main_window

        self.v_box = None
        self.manager = None

        self.name_input_box = None

    def on_show_view(self) -> None:
        self.setup()

    def setup(self) -> None:

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

        self.clear()

        self.manager.draw()

    def _on_click_find_players_button(self, _: arcade.gui.UIOnClickEvent):
        # Implement websockets here.
        print(self.name_input_box.text)
        main_game = Game(self.main_window)
        self.main_window.show_view(main_game)


class Game(arcade.View):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def on_show_view(self):
        self.setup()

    def setup(self):
        pass

    def on_draw(self):

        self.clear()
