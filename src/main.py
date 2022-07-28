import subprocess as sp

import arcade

from config import PATH, SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH
from window import Menu, Window


if __name__ == '__main__':
    proc = sp.Popen(["python", f"{PATH}src/server/server.py"], stdout=sp.PIPE,
                    stderr=sp.PIPE, universal_newlines=True, bufsize=1)
    # arcade.schedule(lambda _: print(proc.stdout.read()), interval=3)
    game = Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu = Menu(game)
    game.show_view(menu)
    arcade.run()
