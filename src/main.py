import arcade

from config import (SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH)
from window import Window, Menu


if __name__ == '__main__':
    game = Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu = Menu(game)
    game.show_view(menu)
    arcade.run()