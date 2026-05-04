import tkinter as tk
from tkinter import messagebox
import random
from dataclasses import dataclass
import threading
import time

# --- Hardware Detection ---
try:
    import board
    import digitalio
    from adafruit_ht16k33.segments import Seg7x4
    from adafruit_matrixkeypad import Matrix_Keypad
    RPi = True
except ImportError:
    RPi = False

# --- Constants & Config ---
COUNTDOWN      = 300
NUM_STRIKES    = 3
TOGGLES_TARGET = [1, 1, 0, 1]
WIRES_TARGET   = [2, 4]
WORD_BANK      = ["array", "model", "build", "input", "debug"]
ANAGRAM_POOL   = ["python", "school", "binary", "decode", "system", 'signal']
ANAGRAM_ROUNDS   = 2
ANAGRAM_ATTEMPTS = 3
WORDLE_ROWS      = 6
WORDLE_COLS      = 5

# Styling
BG, GREEN, RED, YELLOW, CYAN, DIM, INPUT_BG = "#050505", "#00FF66", "#FF3333", "#FFD633", "#00FFFF", "#3A3A3C", "#0D0D1A"
T_CORRECT, T_PRESENT, T_ABSENT, T_EMPTY_BG = "#538D4E", "#B59F3B", "#3A3A3C", "#121213"
T_TEXT = "#FFFFFF"
WIRE_COLORS = ["#CC3333", "#EEEEEE", "#3399FF", "#33CC33", "#FFD633"]
KB_ROWS = [list("qwertyuiop"), list("asdfghjkl"), ["ENTER"] + list("zxcvbnm") + ["⌫"]]

@dataclass
class State:
    stage: str = "BOOT"
    timer: int = COUNTDOWN
    active: bool = False
    strikes_left: int = NUM_STRIKES
    code: str = "____"
    anagram_word: str = ""
    anagram_pool: list = None
    anagram_rounds: int = 0
    anagram_tries: int = 0
    ttt_board: list = None
    w_secret: str = ""
    w_attempt: int = 0
    w_current: str = ""
    wire_pulled: list = None
    kp_input: str = ""

    def __post_init__(self):
        if self.anagram_pool is None: self.anagram_pool = random.sample(ANAGRAM_POOL, len(ANAGRAM_POOL))
        if self.ttt_board is None: self.ttt_board = [""] * 9
        if self.wire_pulled is None: self.wire_pulled = []

# --- Logic Helpers ---
_TTT_WINS = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

def _ttt_winner(b, p): return any(b[a]==b[x]==b[y]==p for a,x,y in _TTT_WINS)

def _ttt_win_line(b, p):
    for ln in _TTT_WINS:
        if all(b[i]==p for i in ln): return ln
    return None

def _minimax(b, is_max, depth=0):
    if _ttt_winner(b, "O"): return 10 - depth
    if _ttt_winner(b, "X"): return depth - 10
    if all(b): return 0
    scores = []
    for i in range(9):
        if b[i] == "":
            b[i] = "O" if is_max else "X"
            scores.append(_minimax(b, not is_max, depth + 1))
            b[i] = ""
    return max(scores) if is_max else min(scores)

def _best_move(b):
    if random.randint(1, 100) <= 30: # AI is slightly less perfect
        empty = [i for i in range(9) if b[i] == ""]
        return random.choice(empty) if empty else None
    best, move = -99, None
    for i in range(9):
        if b[i] == "":
            b[i] = "O"
            s = _minimax(b, False)
            b[i] = ""
            if s > best: best, move = s, i
    return move

# --- Main Game Class ---
class BombGame:
    def __init__(self, root):
        self.root = root
        self.state = State()
        self.root.title("Riddler's Revenge")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self._d = [random.randint(0, 9) for _ in range(4)]
        self._final_code = "".join(str(x) for x in self._d)

        self._build_ui()
        self._setup_hardware()
        self._show_boot()
        self._hw_loop()

    def _build_ui(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        top = tk.Frame(self.root, bg=BG)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=6)
        self._timer_lbl = tk.Label(top, text="05:00", font=("Courier New", 26, "bold"), fg=RED, bg=BG)
        self._timer_lbl.pack(side="left", padx=(0, 20))
        self._code_lbl = tk.Label(top, text="CODE: ____", font=("Courier New", 20, "bold"), fg=GREEN, bg=BG)
        self._code_lbl.pack(side="left", padx=20)
        self._stage_lbl = tk.Label(top, text="BOOT", font=("Courier New", 13), fg=CYAN, bg=BG)
        self._stage_lbl.pack(side="left", padx=20)
        self._strike_lbl = tk.Label(top, text=f"STRIKES: {NUM_STRIKES}", font=("Courier New", 26, "bold"), fg=YELLOW, bg=BG)
        self._strike_lbl.pack(side="right")
        self.content = tk.Frame(self.root, bg=BG)
        self.content.grid(row=1, column=0, sticky="nsew")

    def _clear(self):
        for w in self.content.winfo_children(): w.destroy()
        for s in ("<Key>", "<Return>", "<BackSpace>"):
            try: self.root.unbind(s)
            except: pass

    def _C(self):
        f = tk.Frame(self.content, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor="center")
        return f

    def _set_code(self, code):
        self.state.code = code
        self._code_lbl.config(text=f"CODE: {code}")

    def _update_top(self):
        self._stage_lbl.config(text=self.state.stage)
        self._strike_lbl.config(text=f"STRIKES: {self.state.strikes_left}")

    def _setup_hardware(self):
        if not RPi: return
        i2c = board.I2C()
        self._seg = Seg7x4(i2c)
        self._toggles = [digitalio.DigitalInOut(p) for p in (board.D12, board.D16, board.D20, board.D21)]
        for t in self._toggles: 
            t.direction, t.pull = digitalio.Direction.INPUT, digitalio.Pull.DOWN
        self._wires = [digitalio.DigitalInOut(p) for p in (board.D14, board.D15, board.D18, board.D23, board.D24)]
        for w in self._wires:
            w.direction, w.pull = digitalio.Direction.INPUT, digitalio.Pull.DOWN
        self._btn = digitalio.DigitalInOut(board.D4)
        self._btn.direction, self._btn.pull = digitalio.Direction.INPUT, digitalio.Pull.DOWN
        cols = [digitalio.DigitalInOut(p) for p in (board.D10, board.D9, board.D11)]
        rows = [digitalio.DigitalInOut(p) for p in (board.D5, board.D6, board.D13, board.D19)]
        self._keypad = Matrix_Keypad(rows, cols, ((1,2,3),(4,5,6),(7,8,9),("*",0,"#")))
        self._prev_kp = []

    def _hw_loop(self):
        if RPi:
            if self.state.stage == "BOOT" and self._btn.value: self._activate()
            elif self.state.stage == "TOGGLES":
                if [1 if t.value else 0 for t in self._toggles] == TOGGLES_TARGET:
                    self._set_code(f"{self._d[0]}___")
                    self._show_anagram()
            elif self.state.stage == "FINAL":
                keys = list(self._keypad.pressed_keys)
                for k in [k for k in keys if k not in self._prev_kp]: self._keypad_key(k)
                self._prev_kp = keys
        self.root.after(100, self._hw_loop)

    def _tick(self):
        if not self.state.active or self.state.timer <= 0:
            if self.state.timer <= 0: self._explode("TIME OUT")
            return
        self.state.timer -= 1
        m, s = divmod(self.state.timer, 60)
        self._timer_lbl.config(text=f"{m:02}:{s:02}")
        if RPi: self._seg.print(f"{m:02}{s:02}")
        self.root.after(1000, self._tick)

    def _strike(self, reason="Strike!"):
        self.state.strikes_left -= 1
        self._update_top()
        if self.state.strikes_left <= 0:
            self._explode(reason)
            return False
        messagebox.showwarning("STRIKE", f"{reason}\n{self.state.strikes_left} left.")
        return True

    def _explode(self, reason=""):
        self.state.active = False
        self._clear()
        c = self._C()
        tk.Label(c, text="💥 BOOM 💥", fg=RED, bg=BG, font=("Courier New", 50, "bold")).pack()
        tk.Label(c, text=f"THE RIDDLER WINS\n{reason}", fg=YELLOW, bg=BG, font=("Courier New", 20)).pack(pady=20)

    def _win(self):
        self.state.active = False
        self._clear()
        c = self._C()
        tk.Label(c, text="D E F U S E D", fg=GREEN, bg=BG, font=("Courier New", 50, "bold")).pack()
        tk.Label(c, text="YOU OUTSMARTED THE RIDDLER", fg=CYAN, bg=BG, font=("Courier New", 20)).pack(pady=20)

    # --- Stages ---
    def _show_boot(self):
        self.state.stage = "BOOT"
        self._clear()
        c = self._C()
        tk.Label(c, text="RIDDLER'S REVENGE", fg=GREEN, bg=BG, font=("Courier New", 38, "bold")).pack(pady=20)
        if not RPi:
            tk.Button(c, text="[ PRESS TO START ]", bg=GREEN, command=self._activate).pack(pady=30)

    def _activate(self):
        self.state.active = True
        self._tick()
        self._show_toggles()

    def _show_toggles(self):
        self.state.stage = "TOGGLES"
        self._clear()
        c = self._C()
        tk.Label(c, text="SET SWITCHES TO BINARY 13 (1101)", fg=RED, bg=BG, font=("Courier New", 20)).pack()
        if not RPi:
            self._toggle_state = [0,0,0,0]
            row = tk.Frame(c, bg=BG); row.pack()
            def _toggle(i, b):
                self._toggle_state[i] ^= 1
                b.config(bg=GREEN if self._toggle_state[i] else DIM)
                if self._toggle_state == TOGGLES_TARGET:
                    self._set_code(f"{self._d[0]}___")
                    self.root.after(500, self._show_anagram)
            for i in range(4):
                btn = tk.Button(row, text=f"SW {i+1}", bg=DIM, width=8, height=3)
                btn.config(command=lambda i=i, b=btn: _toggle(i, b))
                btn.pack(side="left", padx=5)

    def _show_anagram(self):
        self.state.stage = "ANAGRAM"
        self._clear()
        c = self._C()
        self.state.anagram_word = self.state.anagram_pool.pop()
        scrambled = list(self.state.anagram_word)
        random.shuffle(scrambled)
        tk.Label(c, text=" ".join(scrambled).upper(), fg=YELLOW, bg=BG, font=("Courier New", 40)).pack(pady=20)
        self._ana_entry = tk.Entry(c, font=("Courier New", 20), justify="center")
        self._ana_entry.pack()
        self._ana_entry.bind("<Return>", lambda e: self._check_anagram())

    def _check_anagram(self):
        if self._ana_entry.get().strip().lower() == self.state.anagram_word:
            self.state.anagram_rounds += 1
            if self.state.anagram_rounds >= ANAGRAM_ROUNDS: self._show_ttt()
            else: self._show_anagram()
        else:
            if self._strike("Anagram Failed"): self._show_anagram()

    def _show_ttt(self):
        self.state.stage, self.state.ttt_board, self._ttt_over = "TTT", [""] * 9, False
        self._clear()
        c = self._C()
        tk.Label(c, text="TIC TAC TOE", fg=GREEN, bg=BG, font=("Courier New", 24)).pack()
        self._ttt_canvas = tk.Canvas(c, width=300, height=300, bg=INPUT_BG)
        self._ttt_canvas.pack()
        self._ttt_canvas.bind("<Button-1>", self._ttt_click)
        # Draw lines
        for i in range(1,3):
            self._ttt_canvas.create_line(100*i, 0, 100*i, 300, fill=GREEN)
            self._ttt_canvas.create_line(0, 100*i, 300, 100*i, fill=GREEN)

    def _ttt_click(self, e):
        idx = (e.y // 100) * 3 + (e.x // 100)
        if self._ttt_over or self.state.ttt_board[idx]: return
        self.state.ttt_board[idx] = "X"
        self._ttt_canvas.create_text((idx%3)*100+50, (idx//3)*100+50, text="X", fill=RED, font=("Arial", 40))
        if _ttt_winner(self.state.ttt_board, "X"):
            self._set_code(f"{self._d[0]}{self._d[1]}__")
            self.root.after(1000, self._show_wordle)
        else: self.root.after(400, self._ttt_ai)

    def _ttt_ai(self):
        move = _best_move(self.state.ttt_board)
        if move is not None:
            self.state.ttt_board[move] = "O"
            self._ttt_canvas.create_text((move%3)*100+50, (move//3)*100+50, text="O", fill=CYAN, font=("Arial", 40))
            if _ttt_winner(self.state.ttt_board, "O"): self._strike("Riddler Won TTT")

    def _show_wordle(self):
        self.state.stage, self.state.w_secret, self.state.w_attempt, self.state.w_current = "WORDLE", random.choice(WORD_BANK), 0, ""
        self._clear()
        c = self._C()
        tk.Label(c, text="W O R D L E", fg=GREEN, font=("Courier New", 24)).pack()
        self._w_entry = tk.Entry(c, font=("Courier New", 20))
        self._w_entry.pack()
        self._w_entry.bind("<Return>", lambda e: self._check_wordle())

    def _check_wordle(self):
        guess = self._w_entry.get().strip().lower()
        if guess == self.state.w_secret:
            self._set_code(f"{self._d[0]}{self._d[1]}{self._d[2]}_")
            self._show_wires()
        else:
            self.state.w_attempt += 1
            if self.state.w_attempt >= WORDLE_ROWS: self._strike("Wordle Failed")

    def _show_wires(self):
        self.state.stage = "WIRES"
        self._clear()
        c = self._C()
        tk.Label(c, text="PULL WIRES 2 & 4", fg=YELLOW, bg=BG, font=("Courier New", 20)).pack()
        if not RPi:
            row = tk.Frame(c, bg=BG); row.pack()
            self.state.wire_pulled = []
            def _pull(i):
                self.state.wire_pulled.append(i)
                if sorted(self.state.wire_pulled) == WIRES_TARGET: 
                    self._set_code(self._final_code)
                    self._show_final()
            for i in range(1, 6):
                tk.Button(row, text=f"W{i}", bg=WIRE_COLORS[i-1], command=lambda i=i: _pull(i)).pack(side="left", padx=5)

    def _show_final(self):
        self.state.stage, self.state.kp_input = "FINAL", ""
        self._clear()
        c = self._C()
        tk.Label(c, text="ENTER CODE", fg=RED, font=("Courier New", 30)).pack()
        self._kp_lbl = tk.Label(c, text="____", font=("Courier New", 40), fg=GREEN, bg=BG)
        self._kp_lbl.pack()
        if not RPi:
            self.root.bind("<Key>", lambda e: self._keypad_key(e.char) if e.char.isdigit() else None)
            self.root.bind("<Return>", lambda e: self._keypad_key("#"))

    def _keypad_key(self, key):
        if key == "#":
            if self.state.kp_input == self._final_code: self._win()
            else: 
                self.state.kp_input = ""
                self._strike("Wrong Code")
        elif len(self.state.kp_input) < 4:
            self.state.kp_input += key
            self._kp_lbl.config(text=self.state.kp_input)

if __name__ == "__main__":
    root = tk.Tk()
    game = BombGame(root)
    root.mainloop()