import board
from digitalio import DigitalInOut, Direction, Pull
import time

button = DigitalInOut(board.D4)
button.direction = Direction.INPUT
button.pull = Pull.DOWN

print("Watching button...")

while True:
    print(button.value)
    time.sleep(0.5)
