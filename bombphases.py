from bombconfigs import *

from tkinter import *
from threading import Thread
from time import sleep

class Lcd(Frame):
    def __init__(self, window):
        super().__init__(window, bg="black")
        window.attributes("-fullscreen", True)

        self._timer = None
        self._button = None

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=1)

        self._lscroll = Label(
            self,
            bg="black",
            fg="white",
            font=("Courier New", 18),
            text="",
            justify=LEFT,
            wraplength=900
        )
        self._lscroll.grid(row=0, column=0, columnspan=3, sticky=W, padx=20, pady=20)

        self.pack(fill=BOTH, expand=True)

    def setup(self):
        self._lcode = Label(
            self,
            bg="black",
            fg="#00ff00",
            font=("Courier New", 24),
            text="Code: ____"
        )
        self._lcode.grid(row=1, column=0, columnspan=3, sticky=W, padx=20, pady=10)

        self._ltoggles = Label(
            self,
            bg="black",
            fg="#00ff00",
            font=("Courier New", 18),
            text="Switches: waiting"
        )
        self._ltoggles.grid(row=2, column=0, columnspan=2, sticky=W, padx=20)

        self._lkeypad = Label(
            self,
            bg="black",
            fg="#00ff00",
            font=("Courier New", 18),
            text="Keypad: "
        )
        self._lkeypad.grid(row=3, column=0, columnspan=2, sticky=W, padx=20)

        self._lwires = Label(
            self,
            bg="black",
            fg="#00ff00",
            font=("Courier New", 18),
            text="Wires: waiting"
        )
        self._lwires.grid(row=4, column=0, columnspan=2, sticky=W, padx=20)

        self._lbutton = Label(
            self,
            bg="black",
            fg="#00ff00",
            font=("Courier New", 18),
            text="Silver Button: waiting"
        )
        self._lbutton.grid(row=5, column=0, columnspan=2, sticky=W, padx=20)

        self._lstrikes = Label(
            self,
            bg="black",
            fg="#00ff00",
            font=("Courier New", 18),
            text="Strikes left: 3"
        )
        self._lstrikes.grid(row=6, column=0, sticky=W, padx=20)

        self._ltimer = Label(
            self,
            bg="black",
            fg="red",
            font=("Courier New", 26, "bold"),
            text="05:00"
        )
        self._ltimer.grid(row=6, column=2, sticky=SE, padx=30, pady=30)

    def setTimer(self, timer):
        self._timer = timer

    def setButton(self, button):
        self._button = button

    def conclusion(self, success=False):
        for widget in self.winfo_children():
            widget.destroy()

        if success:
            text = "YOU DEFUSED THE BOMB\nYOU OUTSMARTED THE RIDDLER"
            color = "#00ff00"
        else:
            text = "BOOM\nTHE RIDDLER WINS"
            color = "red"

        label = Label(
            self,
            text=text,
            fg=color,
            bg="black",
            font=("Courier New", 32, "bold"),
            justify=CENTER
        )
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
        self._started = False
        self._min = "05"
        self._sec = "00"

    def start_countdown(self):
        self._started = True

    def run(self):
        self._running = True

        while self._running:
            self._update()

            if RPi:
                self._component.print(str(self))

            if self._started:
                sleep(1)
                self._value -= 1

                if self._value <= 0:
                    self._value = 0
                    self._running = False
            else:
                sleep(0.1)

    def _update(self):
        self._min = f"{self._value // 60}".zfill(2)
        self._sec = f"{self._value % 60}".zfill(2)

    def __str__(self):
        return f"{self._min}:{self._sec}"


class Keypad(PhaseThread):
    def __init__(self, component, target):
        super().__init__("Keypad", component, target)
        self._value = ""

    def run(self):
        self._running = True

        while self._running:
            if self._component.pressed_keys:
                key = self._component.pressed_keys[0]

                while self._component.pressed_keys:
                    sleep(0.05)

                if key == "*":
                    self._value = ""
                elif key == "#":
                    if self._value == self._target:
                        self._defused = True
                    else:
                        self._failed = True
                        self._value = ""
                else:
                    self._value += str(key)

                if self._value == self._target:
                    self._defused = True
                elif len(self._value) >= len(self._target) and self._value != self._target:
                    self._failed = True
                    self._value = ""

            sleep(0.1)

    def __str__(self):
        if self._defused:
            return "DEFUSED"
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
            elif len(self._value) >= len(self._target) and sorted(self._value) != sorted(self._target):
                self._failed = True

            sleep(0.1)

    def __str__(self):
        if self._defused:
            return "DEFUSED"
        return str(self._value)


class Toggles(PhaseThread):
    def __init__(self, component, target):
        super().__init__("Toggles", component, target)
        self._value = []

    def run(self):
        self._running = True

        while self._running:
            self._value = []

            for switch in self._component:
                # If switch values are backwards on your box,
                # change this line to: self._value.append(0 if switch.value else 1)
                self._value.append(1 if switch.value else 0)

            if self._value == self._target:
                self._defused = True

            sleep(0.2)

    def __str__(self):
        if self._defused:
            return "DEFUSED"
        return str(self._value)


class Button(PhaseThread):
    def __init__(self, component_state, component_rgb, target, color, timer):
        super().__init__("Button", component_state, target)
        self._value = False
        self._pressed = False
        self._timer = timer
        self._rgb = component_rgb

    def run(self):
        self._running = True

        if RPi:
            self._rgb[0].value = False
            self._rgb[1].value = True
            self._rgb[2].value = True

        while self._running:
            self._value = self._component.value

            if self._value:
                self._pressed = True
            else:
                if self._pressed:
                    self._defused = True
                    self._timer.start_countdown()
                    self._pressed = False

            sleep(0.1)

    def __str__(self):
        if self._defused:
            return "ACTIVATED"
        return "Pressed" if self._value else "Waiting"
