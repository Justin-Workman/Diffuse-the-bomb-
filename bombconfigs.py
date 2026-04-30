DEBUG = False
RPi = True
SHOW_BUTTONS = False

COUNTDOWN = 300
NUM_STRIKES = 3
NUM_PHASES = 3

from random import choice

if RPi:
    import board
    from adafruit_ht16k33.segments import Seg7x4
    from digitalio import DigitalInOut, Direction, Pull
    from adafruit_matrixkeypad import Matrix_Keypad

if RPi:
    i2c = board.I2C()
    component_7seg = Seg7x4(i2c)
    component_7seg.brightness = 0.7

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

if RPi:
    component_wires = [
        DigitalInOut(i) for i in
        (board.D14, board.D15, board.D18, board.D23, board.D24)
    ]

    for pin in component_wires:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

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

if RPi:
    component_toggles = [
        DigitalInOut(i) for i in
        (board.D12, board.D16, board.D20, board.D21)
    ]

    for pin in component_toggles:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

def genSerial():
    return "RIDDLER5426"

def genTogglesTarget():
    # 13 in binary = 1101
    # Switch 1 UP, Switch 2 UP, Switch 3 DOWN, Switch 4 UP
    return [1, 1, 0, 1]

def genWiresTarget():
    return [2, 4]

def genKeypadTarget():
    return "5426"

button_color = choice(["R", "G", "B"])

def genButtonTarget():
    return None

serial = genSerial()
toggles_target = genTogglesTarget()
wires_target = genWiresTarget()
keypad_target = genKeypadTarget()
button_target = genButtonTarget()

boot_text = '"If you would like to see your friend again,\nI suggest you press the silver button."\n\n- Riddler'
