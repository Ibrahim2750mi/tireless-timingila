import pathlib

PATH = pathlib.Path(__file__).resolve().parent.parent
ASSET_PATH = pathlib.Path(__file__).resolve().parent.parent / "assets"
SRC_PATH = pathlib.Path(__file__).resolve().parent.parent / "src"
# interface

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "CHEMYSTERY"

# websockets

WAITING_SECOND = 3
ROOM_SIZE = 2

if __name__ == '__main__':
    print(ASSET_PATH)
