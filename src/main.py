import arcade

from config import SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH
from window import Menu, Window

if __name__ == '__main__':
    # arcade.schedule(lambda _: print(proc.stdout.read()), interval=3)
    game = Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu = Menu(game)
    game.show_view(menu)
    arcade.run()
