import tkinter as tk
from tkinter import messagebox
import random
import time
from dataclasses import dataclass

# =========================================================
# OPTIONAL RASPBERRY PI HARDWARE SUPPORT
# =========================================================

try:
    import board
    import digitalio
    from adafruit_matrixkeypad import Matrix_Keypad

    RPI_ENABLED = True

except ImportError:
    RPI_ENABLED = False


# =========================================================
# CONFIG
# =========================================================

WINDOW_BG = "#050505"
TEXT_GREEN = "#00FF66"
TEXT_RED = "#FF3333"
TEXT_YELLOW = "#FFD633"
TEXT_CYAN = "#00FFFF"
FONT_MAIN = ("Courier New", 20)
FONT_LARGE = ("Courier New", 32, "bold")

COUNTDOWN_SECONDS = 600
TOTAL_STRIKES = 5

TOGGLE_TARGET = [True, False, True, True]
FINAL_CODE = "5426"

WORD_BANK = [
    "ARRAY",
    "STACK",
    "QUEUE",
    "INPUT",
    "DEBUG",
]

ANAGRAM_WORDS = [
    "python",
    "planet",
    "school",
    "computer",
    "science",
]


# =========================================================
# GAME STATE
# =========================================================

@dataclass
class GameState:
    strikes: int = TOTAL_STRIKES
    timer: int = COUNTDOWN_SECONDS
    active: bool = False
    stage: str = "BOOT"

    anagram_wins: int = 0

    wordle_attempts: int = 0
    wordle_secret: str = ""

    keypad_input: str = ""

    last_keypress: float = 0


# =========================================================
# MAIN GAME
# =========================================================

class BombGame:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, root):

        self.root = root
        self.state = GameState()

        self.root.title("Riddler's Revenge")
        self.root.configure(bg=WINDOW_BG)
        self.root.attributes("-fullscreen", True)

        self.setup_ui()
        self.setup_hardware()

        self.show_intro()

        self.root.after(100, self.hardware_loop)

    # =====================================================
    # UI SETUP
    # =====================================================

    def setup_ui(self):

        self.top_frame = tk.Frame(self.root, bg=WINDOW_BG)
        self.top_frame.pack(fill="x")

        self.timer_label = tk.Label(
            self.top_frame,
            text="10:00",
            font=("Courier New", 26, "bold"),
            fg=TEXT_RED,
            bg=WINDOW_BG
        )

        self.timer_label.pack(side="left", padx=20, pady=10)

        self.strike_label = tk.Label(
            self.top_frame,
            text=f"STRIKES: {self.state.strikes}",
            font=("Courier New", 26, "bold"),
            fg=TEXT_YELLOW,
            bg=WINDOW_BG
        )

        self.strike_label.pack(side="right", padx=20)

        self.content = tk.Frame(self.root, bg=WINDOW_BG)
        self.content.pack(expand=True)

    # =====================================================
    # HARDWARE SETUP
    # =====================================================

    def setup_hardware(self):

        if not RPI_ENABLED:
            return

        # Toggles
        self.toggles = [
            digitalio.DigitalInOut(pin)
            for pin in (
                board.D12,
                board.D16,
                board.D20,
                board.D21
            )
        ]

        for t in self.toggles:
            t.direction = digitalio.Direction.INPUT
            t.pull = digitalio.Pull.DOWN

        # Wires
        self.wires = [
            digitalio.DigitalInOut(pin)
            for pin in (
                board.D14,
                board.D15,
                board.D18,
                board.D23,
                board.D24
            )
        ]

        for w in self.wires:
            w.direction = digitalio.Direction.INPUT
            w.pull = digitalio.Pull.UP

        # Start Button
        self.start_btn = digitalio.DigitalInOut(board.D4)
        self.start_btn.direction = digitalio.Direction.INPUT
        self.start_btn.pull = digitalio.Pull.DOWN

        # Keypad
        rows = [
            digitalio.DigitalInOut(pin)
            for pin in (
                board.D5,
                board.D6,
                board.D13,
                board.D19
            )
        ]

        cols = [
            digitalio.DigitalInOut(pin)
            for pin in (
                board.D10,
                board.D9,
                board.D11
            )
        ]

        self.keypad = Matrix_Keypad(
            rows,
            cols,
            (
                (1, 2, 3),
                (4, 5, 6),
                (7, 8, 9),
                ("*", 0, "#")
            )
        )

        self.previous_keys = []

    # =====================================================
    # CORE LOOP
    # =====================================================

    def hardware_loop(self):

        if RPI_ENABLED:

            # START BUTTON
            if (
                self.state.stage == "BOOT"
                and self.start_btn.value
            ):
                self.activate_bomb()

            # TOGGLE STAGE
            if self.state.stage == "TOGGLES":

                toggle_values = [t.value for t in self.toggles]

                if toggle_values == TOGGLE_TARGET:
                    self.show_anagram_game()

            # FINAL STAGE
            if self.state.stage == "FINAL":

                red_cut = not self.wires[0].value
                blue_cut = not self.wires[2].value

                if red_cut and blue_cut:

                    keys = self.keypad.pressed_keys

                    if keys != self.previous_keys:

                        current_time = time.time()

                        if (
                            keys
                            and current_time - self.state.last_keypress > 0.2
                        ):

                            self.state.keypad_input += str(keys[0])

                            self.state.last_keypress = current_time

                            self.code_display.config(
                                text=self.state.keypad_input
                            )

                            if len(self.state.keypad_input) >= 4:
                                self.verify_final_code()

                    self.previous_keys = keys

        self.root.after(100, self.hardware_loop)

    # =====================================================
    # TIMER
    # =====================================================

    def start_timer(self):

        if not self.state.active:
            return

        if self.state.timer <= 0:
            self.explode("TIME EXPIRED")
            return

        self.state.timer -= 1

        minutes = self.state.timer // 60
        seconds = self.state.timer % 60

        self.timer_label.config(
            text=f"{minutes:02}:{seconds:02}"
        )

        self.root.after(1000, self.start_timer)

    # =====================================================
    # GENERAL UTILITIES
    # =====================================================

    def clear_content(self):

        for widget in self.content.winfo_children():
            widget.destroy()

    def update_strikes(self):

        self.strike_label.config(
            text=f"STRIKES: {self.state.strikes}"
        )

    def take_strike(self, reason):

        self.state.strikes -= 1

        self.update_strikes()

        if self.state.strikes <= 0:
            self.explode(reason)
            return

        messagebox.showwarning(
            "STRIKE",
            f"{reason}\n\nRemaining Strikes: {self.state.strikes}"
        )

    def explode(self, reason):

        self.state.active = False

        messagebox.showerror(
            "BOOM",
            f"EXPLOSION\n\n{reason}"
        )

        self.root.destroy()

    def win_game(self):

        self.state.active = False

        messagebox.showinfo(
            "SUCCESS",
            "BOMB DEFUSED\n\nGotham is safe."
        )

        self.root.destroy()

    # =====================================================
    # INTRO
    # =====================================================

    def show_intro(self):

        self.clear_content()

        text = (
            "RIDDLER'S REVENGE\n\n"
            "The Riddler has planted a bomb.\n"
            "Batman is occupied.\n"
            "You are Gotham's only hope.\n\n"
            "Press the PHYSICAL SILVER BUTTON\n"
            "to activate the bomb."
        )

        label = tk.Label(
            self.content,
            text=text,
            fg=TEXT_GREEN,
            bg=WINDOW_BG,
            font=FONT_MAIN,
            justify="center"
        )

        label.pack(expand=True)

    # =====================================================
    # ACTIVATE BOMB
    # =====================================================

    def activate_bomb(self):

        self.state.active = True
        self.state.stage = "TOGGLES"

        self.start_timer()

        self.clear_content()

        label = tk.Label(
            self.content,
            text=(
                "BOMB ACTIVATED\n\n"
                "Flip the switches\n"
                "into the correct configuration."
            ),
            fg=TEXT_RED,
            bg=WINDOW_BG,
            font=FONT_LARGE,
            justify="center"
        )

        label.pack(expand=True)

    # =====================================================
    # ANAGRAM GAME
    # =====================================================

    def show_anagram_game(self):

        self.state.stage = "ANAGRAM"

        self.clear_content()

        self.anagram_target = random.choice(ANAGRAM_WORDS)

        scrambled = "".join(
            random.sample(
                self.anagram_target,
                len(self.anagram_target)
            )
        )

        title = tk.Label(
            self.content,
            text=f"UNSCRAMBLE ({self.state.anagram_wins}/2)",
            fg=TEXT_YELLOW,
            bg=WINDOW_BG,
            font=FONT_LARGE
        )

        title.pack(pady=20)

        word = tk.Label(
            self.content,
            text=scrambled,
            fg="white",
            bg=WINDOW_BG,
            font=("Courier New", 42, "bold")
        )

        word.pack(pady=20)

        self.anagram_entry = tk.Entry(
            self.content,
            font=FONT_MAIN,
            justify="center"
        )

        self.anagram_entry.pack(pady=20)

        submit = tk.Button(
            self.content,
            text="SUBMIT",
            command=self.check_anagram,
            font=FONT_MAIN
        )

        submit.pack()

    def check_anagram(self):

        guess = self.anagram_entry.get().lower()

        if guess == self.anagram_target:

            self.state.anagram_wins += 1

            if self.state.anagram_wins >= 2:

                messagebox.showinfo(
                    "RIDDLER",
                    "Correct.\n\nFirst digit: 5"
                )

                self.show_ttt()

            else:
                self.show_anagram_game()

        else:
            self.take_strike("Incorrect Anagram")

    # =====================================================
    # TIC TAC TOE
    # =====================================================

    def show_ttt(self):

        self.state.stage = "TTT"

        self.clear_content()

        self.ttt_board = [""] * 9

        title = tk.Label(
            self.content,
            text="DEFEAT THE RIDDLER",
            fg=TEXT_CYAN,
            bg=WINDOW_BG,
            font=FONT_LARGE
        )

        title.pack(pady=20)

        board_frame = tk.Frame(
            self.content,
            bg=WINDOW_BG
        )

        board_frame.pack()

        self.ttt_buttons = []

        for i in range(9):

            btn = tk.Button(
                board_frame,
                text="",
                width=5,
                height=2,
                font=("Arial", 24),
                command=lambda i=i: self.ttt_move(i)
            )

            btn.grid(
                row=i // 3,
                column=i % 3,
                padx=5,
                pady=5
            )

            self.ttt_buttons.append(btn)

    def ttt_move(self, index):

        if self.ttt_board[index] != "":
            return

        self.ttt_board[index] = "X"

        self.ttt_buttons[index].config(
            text="X",
            state="disabled"
        )

        if self.check_ttt_win("X"):

            messagebox.showinfo(
                "RIDDLER",
                "Impressive.\n\nSecond digit: 4"
            )

            self.show_wordle()
            return

        if "" not in self.ttt_board:
            self.take_strike("Tie Game")
            self.show_ttt()
            return

        self.ttt_ai_move()

    def ttt_ai_move(self):

        empty = [
            i for i, value in enumerate(self.ttt_board)
            if value == ""
        ]

        move = random.choice(empty)

        self.ttt_board[move] = "O"

        self.ttt_buttons[move].config(
            text="O",
            state="disabled"
        )

        if self.check_ttt_win("O"):

            self.take_strike("Lost Tic-Tac-Toe")

            self.show_ttt()
            return

        if "" not in self.ttt_board:

            self.take_strike("Tie Game")

            self.show_ttt()

    def check_ttt_win(self, player):

        wins = [
            (0, 1, 2),
            (3, 4, 5),
            (6, 7, 8),
            (0, 3, 6),
            (1, 4, 7),
            (2, 5, 8),
            (0, 4, 8),
            (2, 4, 6),
        ]

        return any(
            self.ttt_board[a] ==
            self.ttt_board[b] ==
            self.ttt_board[c] ==
            player
            for a, b, c in wins
        )

    # =====================================================
    # WORDLE GAME
    # =====================================================

    def show_wordle(self):

        self.state.stage = "WORDLE"

        self.clear_content()

        self.state.wordle_attempts = 0
        self.state.wordle_secret = random.choice(WORD_BANK)

        title = tk.Label(
            self.content,
            text="WORDLE",
            fg=TEXT_GREEN,
            bg=WINDOW_BG,
            font=FONT_LARGE
        )

        title.pack(pady=20)

        self.wordle_info = tk.Label(
            self.content,
            text="Guess the 5-letter word",
            fg="white",
            bg=WINDOW_BG,
            font=FONT_MAIN
        )

        self.wordle_info.pack(pady=10)

        self.wordle_entry = tk.Entry(
            self.content,
            font=("Courier New", 24),
            justify="center"
        )

        self.wordle_entry.pack(pady=20)

        submit = tk.Button(
            self.content,
            text="GUESS",
            command=self.check_wordle,
            font=FONT_MAIN
        )

        submit.pack()

    def check_wordle(self):

        guess = self.wordle_entry.get().upper()

        if len(guess) != 5:
            messagebox.showwarning(
                "INVALID",
                "Enter a 5-letter word."
            )
            return

        self.state.wordle_attempts += 1

        if guess == self.state.wordle_secret:

            messagebox.showinfo(
                "RIDDLER",
                "Correct.\n\nThird digit: 2"
            )

            self.show_final_stage()

            return

        remaining = 5 - self.state.wordle_attempts

        self.wordle_info.config(
            text=f"Incorrect.\nAttempts Remaining: {remaining}"
        )

        if self.state.wordle_attempts >= 5:

            self.take_strike("Wordle Failed")

            self.show_wordle()

    # =====================================================
    # FINAL STAGE
    # =====================================================

    def show_final_stage(self):

        self.state.stage = "FINAL"

        self.clear_content()

        text = (
            "FINAL CHALLENGE\n\n"
            "Go to the hardware module.\n\n"
            "1. Pull RED and BLUE wires\n"
            "2. Enter the 4-digit code\n"
            "3. Defuse the bomb"
        )

        label = tk.Label(
            self.content,
            text=text,
            fg=TEXT_RED,
            bg=WINDOW_BG,
            font=FONT_MAIN,
            justify="center"
        )

        label.pack(pady=50)

        self.code_display = tk.Label(
            self.content,
            text="",
            fg=TEXT_GREEN,
            bg=WINDOW_BG,
            font=("Courier New", 40, "bold")
        )

        self.code_display.pack(pady=20)

    def verify_final_code(self):

        if self.state.keypad_input == FINAL_CODE:
            self.win_game()

        else:

            self.take_strike("Incorrect Final Code")

            self.state.keypad_input = ""

            self.code_display.config(text="")

    # =====================================================
    # ESCAPE KEY
    # =====================================================

    def quit_game(self, event=None):

        self.root.destroy()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    game = BombGame(root)

    root.bind("<Escape>", game.quit_game)

    root.mainloop()
