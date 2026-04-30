from bombconfigs import *
from bombphases import *

import subprocess
import sys

def bootup():
    gui._lscroll["text"] = boot_text.replace("\x00", "")
    gui.setup()

    if RPi:
        setup_phases()
        check_phases()
    else:
        gui._lscroll["text"] += "\nTEST MODE"

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
    keypad.start()
    wires.start()
    button.start()
    toggles.start()

def run_minigame(filename):
    result = subprocess.run([sys.executable, filename])
    return result.returncode == 0

def run_games():
    global strikes_left

    games = [
        ("anagrams.py", "ANAGRAM TEST"),
        ("tictactoegame.py", "TIC TAC TOE"),
        ("wordl.py", "WORDLE TEST")
    ]

    for file, text in games:
        gui._lscroll["text"] = text
        gui.update()

        if not run_minigame(file):
            strikes_left -= 1

            if strikes_left == 0:
                turn_off()
                gui.after(100, gui.conclusion, False)
                return False

    gui._lscroll["text"] = "ALL GAMES COMPLETE\nPULL CORRECT WIRES"
    return True

def check_phases():
    global active_phases

    if timer._running:
        gui._ltimer["text"] = f"Time: {timer}"
    else:
        turn_off()
        gui.after(100, gui.conclusion, False)
        return

    if button._running:
        gui._lbutton["text"] = f"Button: {button}"
        if button._defused:
            button._running = False
            active_phases -= 1

    if toggles._running:
        gui._ltoggles["text"] = f"Toggles: {toggles}"
        if toggles._defused:
            toggles._running = False
            active_phases -= 1

            if not run_games():
                return

    if wires._running:
        gui._lwires["text"] = f"Wires: {wires}"
        if wires._defused:
            wires._running = False
            active_phases -= 1

    if keypad._running:
        gui._lkeypad["text"] = f"Code: {keypad}"
        if keypad._defused:
            keypad._running = False
            active_phases -= 1

    gui._lstrikes["text"] = f"Strikes: {strikes_left}"

    if strikes_left == 0:
        turn_off()
        gui.after(100, gui.conclusion, False)
        return

    if active_phases == 0:
        turn_off()
        gui.after(100, gui.conclusion, True)
        return

    gui.after(100, check_phases)

def turn_off():
    timer._running = False
    keypad._running = False
    wires._running = False
    button._running = False
    toggles._running = False

window = Tk()
gui = Lcd(window)

strikes_left = NUM_STRIKES
active_phases = NUM_PHASES

gui.after(100, bootup)
window.mainloop()
