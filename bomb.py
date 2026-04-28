#################################
# CSC 102 Defuse the Bomb Project
# Main program
# Team:
#################################

from bomb_configs import *
from bomb_phases import *

import subprocess
import sys

###########
# functions
###########

def bootup():
    gui._lscroll["text"] = boot_text.replace("\x00", "")
    gui.setup()

    if RPi:
        setup_phases()
        check_phases()
    else:
        gui._lscroll["text"] += "\n\nTEST MODE: RPi is False, so hardware will not run."


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


def run_riddler_games():
    global strikes_left

    games = [
        ("anagram_game.py", "First test: Anagrams. Win 5 rounds to earn code piece 5."),
        ("tic_tac_toe_game.py", "Second test: Tic-Tac-Toe. Beat the Riddler to earn code piece 4."),
        ("wordle_game.py", "Third test: Wordle. Solve the word to earn code piece 2.")
    ]

    for filename, message in games:
        gui._lscroll["text"] = message
        gui.update()

        won = run_minigame(filename)

        if not won:
            strike()
            gui._lscroll["text"] = f"You failed {filename}.\nStrike added.\nStrikes left: {strikes_left}"
            gui.update()

            if strikes_left == 0:
                turn_off()
                gui.after(100, gui.conclusion, False)
                return False

    gui._lscroll["text"] = (
        "You survived the Riddler's games.\n"
        "Code pieces found: 5, 4, 2.\n"
        "Now follow the riddle to find the final wire clue.\n"
        "Pull the correct two wires to reveal the last digit."
    )
    gui.update()
    return True


def check_phases():
    global active_phases

    if timer._running:
        gui._ltimer["text"] = f"Time left: {timer}"
    else:
        turn_off()
        gui.after(100, gui.conclusion, False)
        return

    if button._running:
        gui._lbutton["text"] = f"Silver Button: {button}"

        if button._defused:
            button._running = False
            active_phases -= 1
            gui._lscroll["text"] = "THE TEST HAS BEGUN.\nFlip the switches into the correct Riddler sequence."

        elif button._failed:
            strike()
            button._failed = False

    if toggles._running:
        gui._ltoggles["text"] = f"Toggles: {toggles}"

        if toggles._defused:
            toggles._running = False
            active_phases -= 1

            games_won = run_riddler_games()

            if not games_won:
                return

        elif toggles._failed:
            strike()
            toggles._failed = False

    if wires._running:
        gui._lwires["text"] = f"Wires pulled: {wires}"

        if wires._defused:
            wires._running = False
            active_phases -= 1
            gui._lscroll["text"] = (
                "Correct wires pulled.\n"
                "Final code piece: 6\n"
                "Full code: 5426\n"
                "Enter the full code on the keypad."
            )

        elif wires._failed:
            strike()
            wires._failed = False

    if keypad._running:
        gui._lkeypad["text"] = f"Keypad Code: {keypad}"

        if keypad._defused:
            keypad._running = False
            active_phases -= 1

        elif keypad._failed:
            strike()
            keypad._failed = False
            keypad._value = ""

    gui._lstrikes["text"] = f"Strikes left: {strikes_left}"

    if strikes_left == 0:
        turn_off()
        gui.after(1000, gui.conclusion, False)
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
    keypad._running = False
    wires._running = False
    button._running = False
    toggles._running = False

    if RPi:
        component_7seg.blink_rate = 0
        component_7seg.fill(0)

        for pin in button._rgb:
            pin.value = True


######
# MAIN
######

window = Tk()
gui = Lcd(window)

strikes_left = NUM_STRIKES
active_phases = NUM_PHASES

gui.after(100, bootup)

window.mainloop()
