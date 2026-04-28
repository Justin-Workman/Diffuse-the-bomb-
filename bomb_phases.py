#################################
# CSC 102 Defuse the Bomb Project
#################################

from bomb_configs import *

from tkinter import *
import tkinter
from threading import Thread
from time import sleep
import os
import sys

#########
# classes
#########

class Lcd(Frame):
    def __init__(self, window):
        super().__init__(window, bg="black")
        window.attributes("-fullscreen", True)

        self._timer = None
        self._button = None

        self.setupBoot()

    def setupBoot(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=1)

        self._lscroll = Label(self, bg="black", fg="white",
                              font=("Courier New", 14), text="", justify=LEFT)
        self._lscroll.grid(row=0, column=0, columnspan=3, sticky=W)
        self.pack(fill=BOTH, expand=True)

    def setup(self):
        self._ltimer = Label(self, bg="black", fg="#00ff00",
                             font=("Courier New", 18))
        self._ltimer.grid(row=1, column=0, columnspan=3, sticky=W)

        self._lkeypad = Label(self, bg="black", fg="#00ff00",
                              font=("Courier New", 18))
        self._lkeypad.grid(row=2, column=0, columnspan=3, sticky=W)

        self._lwires = Label(self, bg="black", fg="#00ff00",
                             font=("Courier New", 18))
        self._lwires.grid(row=3, column=0, columnspan=3, sticky=W)

        self._lbutton = Label(self, bg="black", fg="#00ff00",
                              font=("Courier New", 18))
        self._lbutton.grid(row=4, column=0, columnspan=3, sticky=W)

        self._ltoggles = Label(self, bg="black", fg="#00ff00",
                               font=("Courier New", 18))
        self._ltoggles.grid(row=5, column=0, columnspan=2, sticky=W)

        self._lstrikes = Label(self, bg="black", fg="#00ff00",
                               font=("Courier New", 18))
        self._lstrikes.grid(row=5, column=2, sticky=W)

    def setTimer(self, timer):
        self._timer = timer

    def setButton(self, button):
        self._button = button

    def conclusion(self, success=False):
        if success:
            text = "YOU DEFUSED THE BOMB\nRIDDLER DEFEATED"
            color = "#00ff00"
        else:
            text = "BOOM\nTHE RIDDLER WINS"
            color = "red"

        for widget in self.winfo_children():
            widget.destroy()

        label = Label(self, text=text, fg=color, bg="black",
                      font=("Courier New", 28))
        label.pack(expand=True)


class PhaseThread(Thread):
    def __init__(self, name, component=None, target=None):
        super().__init__(daemon=True)
        self._component = component
        self._target = target
        self._defused = False
        self._failed = False
        self._value = None
        self._running = False


class Timer(PhaseThread):
    def __init__(self, component, initial_value):
        super().__init__("Timer", component)
        self._value = initial_value
        self._paused = False

    def run(self):
        self._running = True

        while self._running:
            sleep(1)
            self._value -= 1
            if self._value <= 0:
                self._running = False

    def __str__(self):
        return str(self._value)


class Keypad(PhaseThread):
    def __init__(self, component, target):
        super().__init__("Keypad", component, target)
        self._value = ""

    def run(self):
        self._running = True

        while self._running:
            if self._component.pressed_keys:
                key = self._component.pressed_keys[0]
                self._value += str(key)

                if self._value == self._target:
                    self._defused = True

                elif self._value != self._target[:len(self._value)]:
                    self._failed = True

                sleep(0.3)

    def __str__(self):
        return self._value


class Wires(PhaseThread):
    def __init__(self, component, target):
        super().__init__("Wires", component, target)
        self._value = []

    def run(self):
        self._running = True

        while self._running:
            self._value = []

            for i, wire in enumerate(self._component):
                if not wire.value:
                    self._value.append(i + 1)

            if sorted(self._value) == sorted(self._target):
                self._defused = True

            sleep(0.1)

    def __str__(self):
        return str(self._value)


# 🔥 FIXED TOGGLES CLASS
class Toggles(PhaseThread):
    def __init__(self, component, target):
        super().__init__("Toggles", component, target)
        self._value = []

    def run(self):
        self._running = True

        while self._running:
            self._value = []

            for switch in self._component:
                # 🔥 THIS LINE FIXES MOST WIRING ISSUES
                self._value.append(0 if switch.value else 1)

            # Debug print (you can remove later)
            print("Toggle State:", self._value)

            if self._value == self._target:
                self._defused = True

            sleep(0.2)

    def __str__(self):
        return str(self._value)


class Button(PhaseThread):
    def __init__(self, component_state, component_rgb, target, color, timer):
        super().__init__("Button", component_state, target)
        self._rgb = component_rgb
        self._timer = timer
        self._value = False
        self._pressed = False

    def run(self):
        self._running = True

        while self._running:
            self._value = self._component.value

            if self._value:
                self._pressed = True
            else:
                if self._pressed:
                    self._defused = True
                    self._pressed = False

            sleep(0.1)

    def __str__(self):
        return "Pressed" if self._value else "Released"
