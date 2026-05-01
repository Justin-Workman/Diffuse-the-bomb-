"""
riddlers_revenge.py  ─  Riddler's Revenge Bomb Game
Single-file build. Run with:  python3 riddlers_revenge.py
Press ESC to quit at any time.
"""

import tkinter as tk
from tkinter import messagebox
import random
import time
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════
# OPTIONAL RPi SUPPORT
# ═══════════════════════════════════════════════════════════

try:
    import board
    import digitalio
    from adafruit_ht16k33.segments import Seg7x4
    from adafruit_matrixkeypad import Matrix_Keypad
    RPi = True
except ImportError:
    RPi = False


# ═══════════════════════════════════════════════════════════
# CONFIG  ─  edit here
# ═══════════════════════════════════════════════════════════

COUNTDOWN      = 300            # seconds
NUM_STRIKES    = 3
FINAL_CODE     = "5426"
TOGGLES_TARGET = [1, 1, 0, 1]  # binary 13: UP UP DOWN UP
WIRES_TARGET   = [2, 4]         # wire numbers to pull

WORD_BANK      = ["array", "stack", "queue", "input", "debug"]
ANAGRAM_POOL   = [
    "python", "planet", "school", "binary", "signal",
    "cipher", "decode", "enigma", "riddle", "shadow",
]

# ── Colours ───────────────────────────────────────────────
BG          = "#050505"
GREEN       = "#00FF66"
RED         = "#FF3333"
YELLOW      = "#FFD633"
CYAN        = "#00FFFF"
DIM         = "#3A3A3C"

# Wordle tile colours
T_CORRECT   = "#538D4E"
T_PRESENT   = "#B59F3B"
T_ABSENT    = "#3A3A3C"
T_EMPTY_BG  = "#121213"
T_EMPTY_FG  = "#818384"
T_TEXT      = "#FFFFFF"

# Fonts
F_LARGE   = ("Courier New", 28, "bold")
F_MAIN    = ("Courier New", 18)
F_BODY    = ("Courier New", 14)
F_TILE    = ("Courier New", 22, "bold")
F_KEY     = ("Courier New", 12, "bold")
F_SMALL   = ("Courier New", 11)

WORDLE_ROWS    = 6
WORDLE_COLS    = 5

ANAGRAM_ROUNDS   = 2
ANAGRAM_ATTEMPTS = 3

KB_ROWS = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    ["ENTER"] + list("zxcvbnm") + ["⌫"],
]


# ═══════════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════════

@dataclass
class State:
    stage:          str   = "BOOT"
    timer:          int   = COUNTDOWN
    active:         bool  = False
    strikes_left:   int   = NUM_STRIKES
    code:           str   = "____"

    # Anagram
    anagram_word:   str   = ""
    anagram_pool:   list  = None
    anagram_rounds: int   = 0
    anagram_tries:  int   = 0

    # TTT
    ttt_board:      list  = None

    # Wordle
    w_secret:       str   = ""
    w_attempt:      int   = 0
    w_current:      str   = ""

    # Wires (non-RPi)
    wire_pulled:    list  = None

    # Keypad
    kp_input:       str   = ""

    def __post_init__(self):
        if self.anagram_pool is None:
            self.anagram_pool = random.sample(ANAGRAM_POOL, len(ANAGRAM_POOL))
        if self.ttt_board is None:
            self.ttt_board = [""] * 9
        if self.wire_pulled is None:
            self.wire_pulled = []


# ═══════════════════════════════════════════════════════════
# TTT MINIMAX (module-level helper functions)
# ═══════════════════════════════════════════════════════════

_TTT_WINS = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6),
]

def _ttt_winner(board, p):
    return any(board[a]==board[b]==board[c]==p for a,b,c in _TTT_WINS)

def _ttt_win_line(board, p):
    for ln in _TTT_WINS:
        if all(board[i]==p for i in ln):
            return ln
    return None

def _minimax(board, is_max, depth=0):
    if _ttt_winner(board, "O"):  return 10 - depth
    if _ttt_winner(board, "X"):  return depth - 10
    if all(b for b in board):    return 0
    scores = []
    for i in range(9):
        if board[i] == "":
            board[i] = "O" if is_max else "X"
            scores.append(_minimax(board, not is_max, depth+1))
            board[i] = ""
    return max(scores) if is_max else min(scores)

def _best_move(board):
    best, move = -999, None
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            s = _minimax(board, False)
            board[i] = ""
            if s > best:
                best, move = s, i
    return move


# ═══════════════════════════════════════════════════════════
# BOMB GAME
# ═══════════════════════════════════════════════════════════

class BombGame:

    def __init__(self, root):
        self.root  = root
        self.state = State()

        self.root.title("Riddler's Revenge")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._build_ui()
        self._setup_hardware()
        self._show_boot()
        self.root.after(100, self._hw_loop)

    # ─────────────────────────────────────────────────────
    # UI SKELETON
    # ─────────────────────────────────────────────────────

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=10, pady=6)

        self._timer_lbl = tk.Label(
            top, text="05:00", font=F_LARGE, fg=RED, bg=BG)
        self._timer_lbl.pack(side="left")

        self._code_lbl = tk.Label(
            top, text="CODE: ____", font=("Courier New", 20, "bold"),
            fg=GREEN, bg=BG)
        self._code_lbl.pack(side="left", padx=30)

        self._stage_lbl = tk.Label(
            top, text="BOOT", font=("Courier New", 14), fg=CYAN, bg=BG)
        self._stage_lbl.pack(side="left")

        self._strike_lbl = tk.Label(
            top, text=f"STRIKES: {NUM_STRIKES}", font=F_LARGE, fg=YELLOW, bg=BG)
        self._strike_lbl.pack(side="right")

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(expand=True, fill="both")

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()
        # Remove any bindings set by previous stage
        for seq in ("<Key>", "<Return>", "<BackSpace>"):
            try: self.root.unbind(seq)
            except: pass

    def _set_code(self, code):
        self.state.code = code
        self._code_lbl.config(text=f"CODE: {code}")

    def _update_top(self):
        self._stage_lbl.config(text=self.state.stage)
        self._strike_lbl.config(text=f"STRIKES: {self.state.strikes_left}")

    # ─────────────────────────────────────────────────────
    # HARDWARE SETUP
    # ─────────────────────────────────────────────────────

    def _setup_hardware(self):
        if not RPi:
            return

        i2c = board.I2C()
        self._seg = Seg7x4(i2c)
        self._seg.brightness = 0.7

        # Toggles (Pull.DOWN → value=True when switch UP)
        self._toggles = []
        for pin in (board.D12, board.D16, board.D20, board.D21):
            d = digitalio.DigitalInOut(pin)
            d.direction = digitalio.Direction.INPUT
            d.pull      = digitalio.Pull.DOWN
            self._toggles.append(d)

        # Wires (Pull.DOWN → value=False when wire pulled)
        self._wires = []
        for pin in (board.D14, board.D15, board.D18, board.D23, board.D24):
            d = digitalio.DigitalInOut(pin)
            d.direction = digitalio.Direction.INPUT
            d.pull      = digitalio.Pull.DOWN
            self._wires.append(d)

        # Start button (Pull.DOWN → value=True when pressed)
        self._btn = digitalio.DigitalInOut(board.D4)
        self._btn.direction = digitalio.Direction.INPUT
        self._btn.pull      = digitalio.Pull.DOWN

        # Keypad
        cols = [digitalio.DigitalInOut(p) for p in (board.D10, board.D9, board.D11)]
        rows = [digitalio.DigitalInOut(p) for p in (board.D5, board.D6, board.D13, board.D19)]
        keys = ((1,2,3),(4,5,6),(7,8,9),("*",0,"#"))
        self._keypad = Matrix_Keypad(rows, cols, keys)
        self._prev_keys = []

    # ─────────────────────────────────────────────────────
    # HARDWARE POLL LOOP
    # ─────────────────────────────────────────────────────

    def _hw_loop(self):
        self._update_top()

        if RPi:
            s = self.state.stage

            if s == "BOOT" and self._btn.value:
                self._activate()

            elif s == "TOGGLES":
                vals = [1 if t.value else 0 for t in self._toggles]
                if vals == TOGGLES_TARGET:
                    self._show_anagram()

            elif s == "WIRES":
                pulled = sorted([i+1 for i, w in enumerate(self._wires) if not w.value])
                if pulled == sorted(WIRES_TARGET):
                    self._wires_solved()
                elif len(pulled) >= len(WIRES_TARGET) and pulled != sorted(WIRES_TARGET):
                    self._strike("Wrong wires pulled!")
                    self._show_wires()   # reset and try again

            elif s == "FINAL":
                self._poll_keypad()

        self.root.after(100, self._hw_loop)

    def _poll_keypad(self):
        current = list(self._keypad.pressed_keys)
        new     = [k for k in current if k not in self._prev_keys]
        self._prev_keys = current
        for key in new:
            self._keypad_key(key)

    # ─────────────────────────────────────────────────────
    # TIMER
    # ─────────────────────────────────────────────────────

    def _start_timer(self):
        self.state.active = True
        self._tick()

    def _tick(self):
        if not self.state.active:
            return
        if self.state.timer <= 0:
            self._explode("TIME OUT")
            return
        self.state.timer -= 1
        m, s = divmod(self.state.timer, 60)
        self._timer_lbl.config(text=f"{m:02}:{s:02}")
        if self.state.timer <= 60:
            self._timer_lbl.config(fg=RED)
        elif self.state.timer <= 120:
            self._timer_lbl.config(fg=YELLOW)
        if RPi:
            self._seg.print(f"{m:02}{s:02}")
        self.root.after(1000, self._tick)

    # ─────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────

    def _strike(self, reason="Strike!"):
        self.state.strikes_left -= 1
        self._update_top()
        if self.state.strikes_left <= 0:
            self._explode(reason)
            return False
        messagebox.showwarning("STRIKE", f"{reason}\n\n{self.state.strikes_left} strike(s) remaining.")
        return True

    def _explode(self, reason=""):
        self.state.active = False
        self._clear()
        tk.Label(
            self.content, text="B O O M",
            fg=RED, bg=BG, font=("Courier New", 60, "bold"),
        ).pack(expand=True)
        tk.Label(
            self.content, text=f"THE RIDDLER WINS\n{reason}",
            fg=YELLOW, bg=BG, font=F_MAIN,
        ).pack()

    def _win(self):
        self.state.active = False
        self._clear()
        tk.Label(
            self.content, text="DEFUSED",
            fg=GREEN, bg=BG, font=("Courier New", 60, "bold"),
        ).pack(expand=True)
        tk.Label(
            self.content, text="YOU OUTSMARTED THE RIDDLER",
            fg=CYAN, bg=BG, font=F_MAIN,
        ).pack()

    # ─────────────────────────────────────────────────────
    # STAGE: BOOT
    # ─────────────────────────────────────────────────────

    def _show_boot(self):
        self.state.stage = "BOOT"
        self._clear()

        tk.Label(
            self.content,
            text="RIDDLER'S REVENGE",
            fg=GREEN, bg=BG, font=("Courier New", 32, "bold"),
        ).pack(pady=(60, 10))

        tk.Label(
            self.content,
            text=(
                '"If you would like to see your friend again,\n'
                'I suggest you press the silver button."\n\n'
                "— Riddler"
            ),
            fg="white", bg=BG, font=F_MAIN, justify="center",
        ).pack(pady=20)

        if not RPi:
            tk.Button(
                self.content, text="[ PRESS TO START ]",
                fg=BG, bg=GREEN,
                activeforeground=BG, activebackground=CYAN,
                font=("Courier New", 16, "bold"),
                relief="flat", padx=20, pady=10,
                command=self._activate,
            ).pack(pady=30)
            self.root.bind("<Return>", lambda e: self._activate())
            self.root.bind("<space>",  lambda e: self._activate())

    def _activate(self):
        self._start_timer()
        self._show_toggles()

    # ─────────────────────────────────────────────────────
    # STAGE: TOGGLES
    # ─────────────────────────────────────────────────────

    def _show_toggles(self):
        self.state.stage = "TOGGLES"
        self._clear()

        tk.Label(
            self.content,
            text=(
                '"Switches go up, switches go down.\n'
                "If you can't make the number 13 in binary,\n"
                'your friend will be in the ground."\n\n'
                "— Riddler"
            ),
            fg="white", bg=BG, font=F_MAIN, justify="center",
        ).pack(pady=(30, 20))

        tk.Label(
            self.content, text="SET SWITCHES TO BINARY  1 3",
            fg=RED, bg=BG, font=("Courier New", 20, "bold"),
        ).pack(pady=8)

        tk.Label(
            self.content, text="[ UP = 1  ·  DOWN = 0 ]",
            fg=CYAN, bg=BG, font=F_BODY,
        ).pack(pady=4)

        if not RPi:
            # On-screen toggle switches
            tk.Label(
                self.content, text="Click switches to toggle  (target: 1 1 0 1)",
                fg=DIM, bg=BG, font=F_SMALL,
            ).pack(pady=(10, 6))

            btn_row = tk.Frame(self.content, bg=BG)
            btn_row.pack(pady=10)

            self._toggle_state = [0, 0, 0, 0]
            self._toggle_btns  = []

            for i in range(4):
                def _make_cb(idx):
                    def cb():
                        self._toggle_state[idx] ^= 1
                        self._toggle_btns[idx].config(
                            text=f"SW{idx+1}\n{'UP' if self._toggle_state[idx] else 'DN'}",
                            fg=BG,
                            bg=GREEN if self._toggle_state[idx] else DIM,
                        )
                        if self._toggle_state == TOGGLES_TARGET:
                            self.root.after(400, self._show_anagram)
                    return cb

                b = tk.Button(
                    btn_row,
                    text=f"SW{i+1}\nDN",
                    fg=BG, bg=DIM,
                    activeforeground=BG, activebackground=GREEN,
                    font=("Courier New", 14, "bold"),
                    width=6, height=3,
                    relief="flat",
                    command=_make_cb(i),
                )
                b.pack(side="left", padx=10)
                self._toggle_btns.append(b)

    # ─────────────────────────────────────────────────────
    # STAGE: ANAGRAM  (2 rounds, 3 attempts each)
    # ─────────────────────────────────────────────────────

    def _show_anagram(self):
        self.state.stage       = "ANAGRAM"
        self.state.anagram_tries = 0
        self._clear()

        if not self.state.anagram_pool:
            self.state.anagram_pool = random.sample(ANAGRAM_POOL, len(ANAGRAM_POOL))

        self.state.anagram_word = self.state.anagram_pool.pop()

        # Scramble (never equal to original)
        letters = list(self.state.anagram_word)
        for _ in range(100):
            random.shuffle(letters)
            if "".join(letters) != self.state.anagram_word:
                break
        scrambled = "".join(letters)

        tk.Label(
            self.content, text="A N A G R A M S",
            fg=GREEN, bg=BG, font=("Courier New", 26, "bold"),
        ).pack(pady=(24, 4))

        self._ana_round_lbl = tk.Label(
            self.content,
            text=f"Round {self.state.anagram_rounds + 1} of {ANAGRAM_ROUNDS}",
            fg=CYAN, bg=BG, font=F_BODY,
        )
        self._ana_round_lbl.pack(pady=4)

        tk.Label(
            self.content,
            text=" ".join(scrambled.upper()),
            fg=YELLOW, bg=BG, font=("Courier New", 40, "bold"),
        ).pack(pady=20)

        self._ana_dots = tk.Label(
            self.content, text="◆ ◆ ◆", fg=RED, bg=BG,
            font=("Courier New", 18),
        )
        self._ana_dots.pack(pady=4)

        ef = tk.Frame(self.content, bg=BG)
        ef.pack()

        self._ana_entry = tk.Entry(
            ef,
            font=("Courier New", 22),
            fg=GREEN, bg="#0D0D1A",
            insertbackground=GREEN,
            relief="flat", bd=0, width=14,
            justify="center",
            highlightthickness=2,
            highlightbackground=GREEN,
        )
        self._ana_entry.pack(side="left", ipady=8, padx=(0, 10))
        self._ana_entry.bind("<Return>", lambda e: self._check_anagram())
        self._ana_entry.focus()

        tk.Button(
            ef, text="SUBMIT",
            fg=BG, bg=GREEN,
            activeforeground=BG, activebackground=CYAN,
            font=("Courier New", 14, "bold"),
            relief="flat", padx=14, pady=6,
            command=self._check_anagram,
        ).pack(side="left")

        self._ana_status = tk.Label(
            self.content, text="", fg=RED, bg=BG, font=F_BODY,
        )
        self._ana_status.pack(pady=12)

    def _check_anagram(self):
        guess = self._ana_entry.get().strip().lower()
        self._ana_entry.delete(0, "end")

        if guess == self.state.anagram_word:
            self.state.anagram_rounds += 1
            if self.state.anagram_rounds >= ANAGRAM_ROUNDS:
                self._ana_status.config(
                    text="✓  Both solved! Moving on...", fg=GREEN)
                self.root.after(1200, self._show_ttt)
            else:
                self._ana_status.config(
                    text=f"✓  Correct! ({self.state.anagram_word.upper()})  Next word...",
                    fg=GREEN)
                self.root.after(1200, self._show_anagram)
        else:
            self.state.anagram_tries += 1
            remaining = ANAGRAM_ATTEMPTS - self.state.anagram_tries
            self._ana_dots.config(text=("◆ " * remaining + "◇ " * self.state.anagram_tries).strip())

            if self.state.anagram_tries >= ANAGRAM_ATTEMPTS:
                self._ana_status.config(
                    text=f"✗  Failed. Word was: {self.state.anagram_word.upper()}",
                    fg=RED)
                if self._strike(f"Anagram failed! Word was: {self.state.anagram_word.upper()}"):
                    self.root.after(400, self._show_anagram)
            else:
                self._ana_status.config(
                    text=f"✗  Wrong. {remaining} attempt{'s' if remaining != 1 else ''} left.",
                    fg=RED)
                self._ana_entry.focus()

    # ─────────────────────────────────────────────────────
    # STAGE: TIC TAC TOE  (minimax AI)
    # ─────────────────────────────────────────────────────

    def _show_ttt(self):
        self.state.stage    = "TTT"
        self.state.ttt_board = [""] * 9
        self._ttt_over      = False
        self._clear()

        CELL = 150
        PAD  = 16

        tk.Label(
            self.content, text="TIC  TAC  TOE",
            fg=GREEN, bg=BG, font=("Courier New", 26, "bold"),
        ).pack(pady=(20, 2))

        tk.Label(
            self.content,
            text='"You better get three in a row, or like Mufasa you will go."  — Riddler',
            fg=DIM, bg=BG, font=F_SMALL, justify="center",
        ).pack(pady=(0, 2))

        tk.Label(
            self.content, text="You are  X  ·  Riddler is  O  ·  You must WIN",
            fg=CYAN, bg=BG, font=F_BODY,
        ).pack(pady=(0, 12))

        size = CELL * 3 + PAD * 2
        self._ttt_canvas = tk.Canvas(
            self.content,
            width=size, height=size,
            bg="#0D0D1A",
            highlightthickness=2, highlightbackground=GREEN,
        )
        self._ttt_canvas.pack()
        self._ttt_canvas.bind("<Button-1>", lambda e: self._ttt_click(e, CELL, PAD))
        self._CELL, self._PAD = CELL, PAD

        self._ttt_status = tk.Label(
            self.content, text="Your move",
            fg=GREEN, bg=BG, font=F_BODY,
        )
        self._ttt_status.pack(pady=10)

        self._ttt_draw_grid(CELL, PAD)

    def _ttt_draw_grid(self, C, P):
        cv = self._ttt_canvas
        cv.delete("all")
        for i in range(1, 3):
            cv.create_line(P, P+i*C, P+3*C, P+i*C, fill=GREEN, width=3)
            cv.create_line(P+i*C, P, P+i*C, P+3*C, fill=GREEN, width=3)

    def _ttt_center(self, idx):
        C, P = self._CELL, self._PAD
        r, c = divmod(idx, 3)
        return P + c*C + C//2, P + r*C + C//2

    def _ttt_draw_x(self, idx):
        cx, cy = self._ttt_center(idx)
        m = 42
        self._ttt_canvas.create_line(cx-m, cy-m, cx+m, cy+m,
                                     fill=RED, width=8, capstyle="round")
        self._ttt_canvas.create_line(cx+m, cy-m, cx-m, cy+m,
                                     fill=RED, width=8, capstyle="round")

    def _ttt_draw_o(self, idx):
        cx, cy = self._ttt_center(idx)
        r = 48
        self._ttt_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                     outline=CYAN, width=8)

    def _ttt_draw_win_line(self, line):
        x1, y1 = self._ttt_center(line[0])
        x2, y2 = self._ttt_center(line[2])
        self._ttt_canvas.create_line(x1, y1, x2, y2,
                                     fill=GREEN, width=6, dash=(12, 6))

    def _ttt_click(self, event, C, P):
        if self._ttt_over:
            return
        col = (event.x - P) // C
        row = (event.y - P) // C
        if not (0 <= col < 3 and 0 <= row < 3):
            return
        idx = row * 3 + col
        if self.state.ttt_board[idx]:
            return

        self.state.ttt_board[idx] = "X"
        self._ttt_draw_x(idx)

        if _ttt_winner(self.state.ttt_board, "X"):
            self._ttt_over = True
            ln = _ttt_win_line(self.state.ttt_board, "X")
            self._ttt_draw_win_line(ln)
            self._set_code("54__")
            self._ttt_status.config(text="YOU WIN!  Digit: 4", fg=GREEN)
            self.root.after(1800, self._show_wordle)
            return

        if all(self.state.ttt_board):
            self._ttt_over = True
            self._ttt_status.config(text="DRAW — no mercy.", fg=RED)
            if self._strike("Tic Tac Toe draw — you needed to WIN."):
                self.root.after(800, self._show_ttt)
            return

        self._ttt_status.config(text="Riddler is thinking...", fg=DIM)
        self.root.after(380, self._ttt_ai_move)

    def _ttt_ai_move(self):
        move = _best_move(self.state.ttt_board)
        if move is None:
            return
        self.state.ttt_board[move] = "O"
        self._ttt_draw_o(move)

        if _ttt_winner(self.state.ttt_board, "O"):
            self._ttt_over = True
            ln = _ttt_win_line(self.state.ttt_board, "O")
            self._ttt_draw_win_line(ln)
            self._ttt_status.config(text="RIDDLER WINS.  Strike incoming.", fg=RED)
            if self._strike("The Riddler won Tic Tac Toe!"):
                self.root.after(800, self._show_ttt)
            return

        if all(self.state.ttt_board):
            self._ttt_over = True
            self._ttt_status.config(text="DRAW — no mercy.", fg=RED)
            if self._strike("Tic Tac Toe draw — you needed to WIN."):
                self.root.after(800, self._show_ttt)
            return

        self._ttt_status.config(text="Your move", fg=GREEN)

    # ─────────────────────────────────────────────────────
    # STAGE: WORDLE  (6×5 tile grid + on-screen keyboard)
    # ─────────────────────────────────────────────────────

    def _show_wordle(self):
        self.state.stage     = "WORDLE"
        pool = [w for w in WORD_BANK if w != self.state.w_secret]
        self.state.w_secret  = random.choice(pool)
        self.state.w_attempt = 0
        self.state.w_current = ""
        self._w_over         = False
        self._w_key_map      = {}
        self._clear()

        tk.Label(
            self.content, text="W O R D L E",
            fg=GREEN, bg=BG, font=("Courier New", 24, "bold"),
        ).pack(pady=(16, 2))

        tk.Label(
            self.content,
            text='"Solve the word and earn the next piece.  Six chances."  — Riddler',
            fg=DIM, bg=BG, font=F_SMALL,
        ).pack(pady=(0, 2))

        tk.Label(
            self.content,
            text=f"Guess the {WORDLE_COLS}-letter word  ·  {WORDLE_ROWS} attempts",
            fg=CYAN, bg=BG, font=F_BODY,
        ).pack(pady=(0, 10))

        # Tile grid
        grid = tk.Frame(self.content, bg=BG)
        grid.pack()
        self._w_tiles = []
        for r in range(WORDLE_ROWS):
            row = []
            for c in range(WORDLE_COLS):
                cell = tk.Frame(grid, width=58, height=58,
                                bg=T_EMPTY_BG,
                                highlightbackground=T_EMPTY_FG,
                                highlightthickness=2)
                cell.grid(row=r, column=c, padx=3, pady=3)
                cell.pack_propagate(False)
                lbl = tk.Label(cell, text="", fg=T_TEXT, bg=T_EMPTY_BG, font=F_TILE)
                lbl.pack(expand=True)
                row.append({"f": cell, "l": lbl})
            self._w_tiles.append(row)

        # Status
        self._w_status = tk.Label(
            self.content, text="", fg=YELLOW, bg=BG, font=F_BODY)
        self._w_status.pack(pady=6)

        # On-screen keyboard
        kb = tk.Frame(self.content, bg=BG)
        kb.pack()
        for row_keys in KB_ROWS:
            rf = tk.Frame(kb, bg=BG)
            rf.pack()
            for key in row_keys:
                w = 5 if len(key) == 1 else 7
                lbl = tk.Label(rf, text=key.upper(), fg=T_TEXT, bg=T_ABSENT,
                               font=F_KEY, width=w, height=2)
                lbl.pack(side="left", padx=2, pady=2)
                lbl.bind("<Button-1>", lambda e, k=key: self._w_kb(k))
                if len(key) == 1:
                    self._w_key_map[key] = lbl

        # Physical keyboard
        self.root.bind("<Key>",       self._w_keypress)
        self.root.bind("<Return>",    lambda e: self._w_submit())
        self.root.bind("<BackSpace>", lambda e: self._w_backspace())

    def _w_kb(self, key):
        if self._w_over: return
        if key == "ENTER":      self._w_submit()
        elif key == "⌫":       self._w_backspace()
        elif len(key) == 1:     self._w_add(key)

    def _w_keypress(self, event):
        if self._w_over: return
        if event.char.isalpha(): self._w_add(event.char.lower())

    def _w_add(self, ch):
        if len(self.state.w_current) < WORDLE_COLS:
            self.state.w_current += ch
            col  = len(self.state.w_current) - 1
            tile = self._w_tiles[self.state.w_attempt][col]
            tile["l"].config(text=ch.upper())
            tile["f"].config(highlightbackground=CYAN)

    def _w_backspace(self):
        if self.state.w_current:
            col  = len(self.state.w_current) - 1
            tile = self._w_tiles[self.state.w_attempt][col]
            tile["l"].config(text="")
            tile["f"].config(highlightbackground=T_EMPTY_FG)
            self.state.w_current = self.state.w_current[:-1]

    def _w_submit(self):
        guess = self.state.w_current.lower()
        if len(guess) < WORDLE_COLS:
            self._w_status.config(text=f"Need {WORDLE_COLS} letters!", fg=RED)
            return
        self._w_status.config(text="")

        # Two-pass scoring
        result  = ["absent"] * WORDLE_COLS
        s_count = {}
        for i, (g, s) in enumerate(zip(guess, self.state.w_secret)):
            if g == s:   result[i] = "correct"
            else:        s_count[s] = s_count.get(s, 0) + 1
        for i, g in enumerate(guess):
            if result[i] != "correct" and s_count.get(g, 0) > 0:
                result[i] = "present"
                s_count[g] -= 1

        cmap = {"correct": T_CORRECT, "present": T_PRESENT, "absent": T_ABSENT}
        prio = {T_CORRECT: 2, T_PRESENT: 1, T_ABSENT: 0}

        for col, (letter, status) in enumerate(zip(guess, result)):
            bg   = cmap[status]
            tile = self._w_tiles[self.state.w_attempt][col]
            tile["l"].config(bg=bg, fg=T_TEXT)
            tile["f"].config(bg=bg, highlightbackground=bg)
            if letter in self._w_key_map:
                lbl = self._w_key_map[letter]
                cur = lbl.cget("bg")
                if prio.get(bg, 0) > prio.get(cur, -1):
                    lbl.config(bg=bg)

        self.state.w_attempt += 1
        self.state.w_current  = ""

        if guess == self.state.w_secret:
            self._w_over = True
            self._set_code("542_")
            self._w_status.config(text="✓  CORRECT!  Digit: 2", fg=GREEN)
            self.root.after(1800, self._show_wires)
            return

        if self.state.w_attempt >= WORDLE_ROWS:
            self._w_over = True
            self._w_status.config(
                text=f"✗  FAILED — Word was: {self.state.w_secret.upper()}", fg=RED)
            if self._strike(f"Wordle failed! Word was: {self.state.w_secret.upper()}"):
                self.root.after(1000, self._show_wordle)
            return

        rem = WORDLE_ROWS - self.state.w_attempt
        self._w_status.config(
            text=f"{rem} attempt{'s' if rem != 1 else ''} remaining", fg=YELLOW)

    # ─────────────────────────────────────────────────────
    # STAGE: WIRES
    # ─────────────────────────────────────────────────────

    def _show_wires(self):
        self.state.stage = "WIRES"
        self.state.wire_pulled = []
        self._clear()

        tk.Label(
            self.content, text="W I R E S",
            fg=GREEN, bg=BG, font=("Courier New", 26, "bold"),
        ).pack(pady=(30, 8))

        tk.Label(
            self.content,
            text="Correct wires pulled.\nFind the final clue.\nPull the correct wires.",
            fg="white", bg=BG, font=F_MAIN, justify="center",
        ).pack(pady=10)

        tk.Label(
            self.content, text="[ Cut the right wires to reveal the last digit ]",
            fg=CYAN, bg=BG, font=F_BODY,
        ).pack(pady=4)

        if not RPi:
            tk.Label(
                self.content, text="Click two wires to pull them",
                fg=DIM, bg=BG, font=F_SMALL,
            ).pack(pady=(12, 6))

            WIRE_COLORS = ["#CC3333", "#FFFFFF", "#3399FF", "#33CC33", "#FFD633"]
            wire_row = tk.Frame(self.content, bg=BG)
            wire_row.pack(pady=10)

            self._wire_btns = []
            for i, wc in enumerate(WIRE_COLORS):
                num = i + 1
                def _cb(n=num):
                    self._toggle_wire_gui(n)
                b = tk.Button(
                    wire_row,
                    text=f"WIRE {num}",
                    fg=BG, bg=wc,
                    activeforeground=BG, activebackground=wc,
                    font=("Courier New", 13, "bold"),
                    width=8, height=3,
                    relief="flat",
                    command=_cb,
                )
                b.pack(side="left", padx=8)
                self._wire_btns.append(b)

            self._wire_status = tk.Label(
                self.content, text="No wires pulled.", fg=DIM, bg=BG, font=F_BODY)
            self._wire_status.pack(pady=10)

    def _toggle_wire_gui(self, num):
        if num in self.state.wire_pulled:
            self.state.wire_pulled.remove(num)
        else:
            self.state.wire_pulled.append(num)

        # Visual feedback: dim the button if pulled
        idx = num - 1
        WIRE_COLORS = ["#CC3333", "#FFFFFF", "#3399FF", "#33CC33", "#FFD633"]
        if num in self.state.wire_pulled:
            self._wire_btns[idx].config(bg=DIM, fg="#888")
        else:
            self._wire_btns[idx].config(bg=WIRE_COLORS[idx], fg=BG)

        pulled_sorted = sorted(self.state.wire_pulled)
        self._wire_status.config(
            text=f"Pulled: {pulled_sorted if pulled_sorted else 'none'}", fg=YELLOW)

        if pulled_sorted == sorted(WIRES_TARGET):
            self._wire_status.config(text="✓  Correct wires!", fg=GREEN)
            self.root.after(800, self._wires_solved)
        elif len(self.state.wire_pulled) >= len(WIRES_TARGET) and \
                pulled_sorted != sorted(WIRES_TARGET):
            self._wire_status.config(text="✗  Wrong wires!", fg=RED)
            if self._strike("Wrong wires pulled!"):
                self.root.after(500, self._show_wires)

    def _wires_solved(self):
        self._set_code("5426")
        self._show_final()

    # ─────────────────────────────────────────────────────
    # STAGE: FINAL (keypad)
    # ─────────────────────────────────────────────────────

    def _show_final(self):
        self.state.stage    = "FINAL"
        self.state.kp_input = ""
        self._clear()

        tk.Label(
            self.content, text="ENTER THE CODE",
            fg=RED, bg=BG, font=("Courier New", 24, "bold"),
        ).pack(pady=(40, 16))

        tk.Label(
            self.content,
            text="Correct wires pulled.\nFinal digit: 6\nFull code: 5426",
            fg="white", bg=BG, font=F_MAIN, justify="center",
        ).pack(pady=8)

        self._kp_display = tk.Label(
            self.content,
            text="_ _ _ _",
            fg=GREEN, bg=BG,
            font=("Courier New", 48, "bold"),
        )
        self._kp_display.pack(pady=20)

        self._kp_status = tk.Label(
            self.content, text="", fg=RED, bg=BG, font=F_BODY)
        self._kp_status.pack(pady=6)

        if not RPi:
            # On-screen numpad
            pad_frame = tk.Frame(self.content, bg=BG)
            pad_frame.pack()

            keys_layout = [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]
            for row in keys_layout:
                rf = tk.Frame(pad_frame, bg=BG)
                rf.pack()
                for k in row:
                    tk.Button(
                        rf, text=k,
                        fg=GREEN, bg="#0D0D1A",
                        activeforeground=CYAN, activebackground="#1A1A2E",
                        font=("Courier New", 18, "bold"),
                        width=4, height=2,
                        relief="flat",
                        highlightthickness=1,
                        highlightbackground=DIM,
                        command=lambda k=k: self._keypad_key(k),
                    ).pack(side="left", padx=4, pady=4)

            # Also allow physical keyboard numbers
            self.root.bind("<Key>", self._final_keypress)

    def _final_keypress(self, event):
        ch = event.char
        if ch.isdigit():    self._keypad_key(ch)
        elif ch in ("*",):  self._keypad_key("*")
        elif event.keysym == "Return":  self._keypad_key("#")
        elif event.keysym == "BackSpace":
            self.state.kp_input = self.state.kp_input[:-1]
            self._refresh_kp_display()

    def _keypad_key(self, key):
        if key == "*":
            self.state.kp_input = ""
            self._kp_status.config(text="Cleared.", fg=DIM)
        elif key == "#":
            if self.state.kp_input == FINAL_CODE:
                self._kp_status.config(text="✓  CODE ACCEPTED", fg=GREEN)
                self.root.after(1200, self._win)
            else:
                self.state.kp_input = ""
                self._kp_status.config(text="✗  WRONG CODE", fg=RED)
                self._strike("Wrong code entered!")
        else:
            if len(self.state.kp_input) < len(FINAL_CODE):
                self.state.kp_input += str(key)
        self._refresh_kp_display()

    def _refresh_kp_display(self):
        filled  = list(self.state.kp_input)
        blanks  = ["_"] * (len(FINAL_CODE) - len(filled))
        display = "  ".join(filled + blanks)
        self._kp_display.config(text=display)


# ═══════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    game = BombGame(root)
    root.mainloop()