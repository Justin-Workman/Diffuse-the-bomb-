from bombconfigs import *
from bombphases import *

import subprocess
import sys

def bootup():
    gui._lscroll["text"] = boot_text.replace("\x00", "")
    gui.setup()
    setup_phases()
    check_phases()

def setup_phases():
    global timer, keypad, wires, button, toggles

    timer = Timer(component_7seg, COUNTDOWN)
    gui.setTimer(timer)

    keypad = Keypad(component_keypad, keypad_target)
    wires = Wires(component_wires, wires_target)
    button = Button(component_button_state, component_button_RGB, button_target, button_color, timer)
    gui.setButton(button)
    toggles = Toggles(component_toggles, toggles_target)

    timer.start()
    button.start()

def start_puzzle_phases():
    global keypad, wires, toggles

    keypad.start()
    wires.start()
    toggles.start()

def run_minigame(filename):
    result = subprocess.run([sys.executable, filename])
    return result.returncode == 0

def run_games():
    global strikes_left

    games = [
        ("tictactoegame.py", '"You better get three in a row,\nor like Mufasa you will go."\n\n- Riddler'),
        ("anagrams.py", "Unscramble the Riddler's message.\nWin to earn the next piece."),
        ("wordl.py", "Solve the Wordle test.\nThe Riddler is watching.")
    ]

    for file, text in games:
        gui._lscroll["text"] = text
        gui.update()

        if not run_minigame(file):
            strike()

            if strikes_left == 0:
                turn_off()
                gui.after(100, gui.conclusion, False)
                return False

    gui._lscroll["text"] = (
        "The games are complete.\n"
        "Code pieces found: 5, 4, 2.\n"
        "Now find the final clue.\n"
        "Pull the correct wires."
    )
    gui.update()
    return True

def check_phases():
    global active_phases

    gui._ltimer["text"] = str(timer)

    if not timer._running:
        turn_off()
        gui.after(100, gui.conclusion, False)
        return

    if button._running:
        gui._lbutton["text"] = f"Silver Button: {button}"

        if button._defused:
            button._running = False

            gui._lscroll["text"] = (
                '"Switches go up, switches go down,\n'
                "if you can't make the number 13 in binary,\n"
                'your friend will be in the ground."\n\n'
                "- Riddler"
            )

            start_puzzle_phases()

    if toggles._running:
        gui._ltoggles["text"] = f"Switches: {toggles}"

        if toggles._defused:
            toggles._running = False
            active_phases -= 1

            gui._lcode["text"] = "Code: 5___"
            gui._lscroll["text"] = (
                "Correct. Binary 13 has been solved.\n"
                "First code piece: 5\n\n"
                '"You better get three in a row,\n'
                'or like Mufasa you will go."\n\n'
                "- Riddler"
            )
            gui.update()

            if not run_games():
                return

        elif toggles._failed:
            strike()
            toggles._failed = False

    if wires._running:
        gui._lwires["text"] = f"Wires: {wires}"

        if wires._defused:
            wires._running = False
            active_phases -= 1

            gui._lcode["text"] = "Code: 5426"
            gui._lscroll["text"] = (
                "Correct wires pulled.\n"
                "Final code piece: 6\n"
                "Full code: 5426\n"
                "Enter 5426 on the keypad."
            )

        elif wires._failed:
            strike()
            wires._failed = False

    if keypad._running:
        gui._lkeypad["text"] = f"Keypad: {keypad}"

        if keypad._defused:
            keypad._running = False
            active_phases -= 1

        elif keypad._failed:
            strike()
            keypad._failed = False

    gui._lstrikes["text"] = f"Strikes left: {strikes_left}"

    if strikes_left == 0:
        turn_off()
        gui.after(100, gui.conclusion, False)
        return

    if active_phases == 0:
        turn_off()
        gui.after(100, gui.conclusion, True)
        return

    gui.after(100, check_phases)

def strike():
    global strikes_left
    strikes_left -= 1

def turn_off():
    timer._running = False
    button._running = False
    toggles._running = False
    wires._running = False
    keypad._running = False

    if RPi:
        component_7seg.blink_rate = 0
        component_7seg.fill(0)

        for pin in button._rgb:
            pin.value = True

window = Tk()
gui = Lcd(window)

strikes_left = NUM_STRIKES
active_phases = NUM_PHASES

gui.after(100, bootup)
window.mainloop()
