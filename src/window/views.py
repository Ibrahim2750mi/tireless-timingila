import arcade
import arcade.gui


class Menu(arcade.View):
    def __init__(self, main_window: arcade.Window):
        super().__init__(main_window)
        self.main_window = main_window

        self.v_box = None
        self.manager = None

    def on_show_view(self):
        self.setup()

    def setup(self):
        """Set up the game variables. Call to re-start the game."""
        self.v_box = arcade.gui.UIBoxLayout()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        play_button = arcade.gui.UIFlatButton(text="PLAY", width=300)

        self.v_box.add(play_button)

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="left",
                anchor_y="bottom",
                align_x=250,
                align_y=100,
                child=self.v_box
            )
        )

    def on_draw(self):
        """Render the screen."""

        self.clear()

        self.manager.draw()
