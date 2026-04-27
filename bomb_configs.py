#################################
# CSC 102 Defuse the Bomb Project
# Configuration file
# Team:
#################################

# constants
DEBUG = False
RPi = True            # True when running on Raspberry Pi
SHOW_BUTTONS = False
COUNTDOWN = 300      # 5 minutes
NUM_STRIKES = 3      # 3 failed attempts total
NUM_PHASES = 4       # keypad, wires, button, toggles

# imports
from random import choice

if RPi:
    import board
    from adafruit_ht16k33.segments import Seg7x4
    from digitalio import DigitalInOut, Direction, Pull
    from adafruit_matrixkeypad import Matrix_Keypad

#################################
# setup the electronic components
#################################

# 7-segment display
if RPi:
    i2c = board.I2C()
    component_7seg = Seg7x4(i2c)
    component_7seg.brightness = 0.5

# keypad
if RPi:
    keypad_cols = [DigitalInOut(i) for i in (board.D10, board.D9, board.D11)]
    keypad_rows = [DigitalInOut(i) for i in (board.D5, board.D6, board.D13, board.D19)]

    keypad_keys = (
        (1, 2, 3),
        (4, 5, 6),
        (7, 8, 9),
        ("*", 0, "#")
    )

    component_keypad = Matrix_Keypad(keypad_rows, keypad_cols, keypad_keys)

# jumper wires
if RPi:
    component_wires = [
        DigitalInOut(i) for i in
        (board.D14, board.D15, board.D18, board.D23, board.D24)
    ]

    for pin in component_wires:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

# pushbutton
if RPi:
    component_button_state = DigitalInOut(board.D4)
    component_button_state.direction = Direction.INPUT
    component_button_state.pull = Pull.DOWN

    component_button_RGB = [
        DigitalInOut(i) for i in
        (board.D17, board.D27, board.D22)
    ]

    for pin in component_button_RGB:
        pin.direction = Direction.OUTPUT
        pin.value = True

# toggle switches
if RPi:
    component_toggles = [
        DigitalInOut(i) for i in
        (board.D12, board.D16, board.D20, board.D21)
    ]

    for pin in component_toggles:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

#################################
# target generation
#################################

def genSerial():
    return "RIDDLER5426"

def genTogglesTarget():
    # Correct toggle pattern.
    # 1 = switch ON/up
    # 0 = switch OFF/down
    return [1, 0, 1, 1]

def genWiresTarget():
    # Correct wires to pull.
    # Wire numbers start at 1 from left to right.
    return [2, 4]

def genKeypadTarget():
    # Final defusal code
    return "5426"

button_color = choice(["R", "G", "B"])

def genButtonTarget():
    global button_color

    b_target = None

    if button_color == "G":
        b_target = [n for n in serial if n.isdigit()][0]
    elif button_color == "B":
        b_target = [n for n in serial if n.isdigit()][-1]

    return b_target

###############################

serial = genSerial()
toggles_target = genTogglesTarget()
wires_target = genWiresTarget()
keypad_target = genKeypadTarget()
button_target = genButtonTarget()

boot_text = f"THE RIDDLER HAS TAKEN YOUR TEAMMATE.\n"\
            f"Solve his riddles. Beat his games.\n"\
            f"Press the silver button to begin the test.\n"\
            f"Flip the switches into the correct sequence.\n"\
            f"Find each piece of the code.\n"\
            f"Final code: 5426\n"\
            f"Serial number: {serial}\n"
