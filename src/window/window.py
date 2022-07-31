import arcade

from config import ASSET_PATH


class Window(arcade.Window):
    """Main application class."""

    def __init__(self, width, height, title):
        super().__init__(width, height, title)

        arcade.set_background_color(arcade.color.ANTI_FLASH_WHITE)

        # self.music = arcade.Sound(str(ASSET_PATH / "music" / "game_bg.wav"))
        # self.music_player = self.music.play(loop=True, volume=0.1)
        # self.music_player.seek(90)
