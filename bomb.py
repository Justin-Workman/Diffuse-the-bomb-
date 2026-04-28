#################################
# CSC 102 Defuse the Bomb Project
# Main program
# Team:
#################################

from bomb_configs import *
from bomb_phases import *

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
            gui._lscroll["text"] = "Correct switches.\nNow solve the Riddler's games.\nCode piece 1: 5\nCode piece 2: 4\nCode piece 3: 2\nFind the final clue and pull the right wires."

        elif toggles._failed:
            strike()
            toggles._failed = False

    if wires._running:
        gui._lwires["text"] = f"Wires pulled: {wires}"

        if wires._defused:
            wires._running = False
            active_phases -= 1
            gui._lscroll["text"] = "Correct wires pulled.\nFinal code piece: 6\nEnter the full code on the keypad."

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
