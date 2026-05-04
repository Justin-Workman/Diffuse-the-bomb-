import tkinter as tk
import random
import threading
import time
import sys
import os
import struct
import wave
import tempfile
from dataclasses import dataclass, field

# ── Hardware detection ─────────────────────────────────────────────────────────
try:
    import board, digitalio
    from adafruit_ht16k33.segments import Seg7x4
    from adafruit_matrixkeypad import Matrix_Keypad
    RPi = True
except ImportError:
    RPi = False

# ── Audio backend (pygame preferred, fallback to beep) ────────────────────────
AUDIO_OK = False
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.init()
    AUDIO_OK = True
except Exception:
    pass

# ── Constants ─────────────────────────────────────────────────────────────────
COUNTDOWN       = 300
NUM_STRIKES     = 3
TOGGLES_TARGET  = [1, 1, 0, 1]
WIRES_TARGET    = [2, 4]

WORD_BANK    = ["array", "model", "build", "input", "debug"]
ANAGRAM_POOL = ["python", "school", "binary", "decode", "system", "signal"]

ANAGRAM_ROUNDS   = 2
ANAGRAM_ATTEMPTS = 3
WORDLE_ROWS      = 6
WORDLE_COLS      = 5

BG        = "#050505"
GREEN     = "#00FF66"
RED       = "#FF3333"
YELLOW    = "#FFD633"
CYAN      = "#00FFFF"
DIM       = "#3A3A3C"
INPUT_BG  = "#0D0D1A"

T_CORRECT  = "#538D4E"
T_PRESENT  = "#B59F3B"
T_ABSENT   = "#3A3A3C"
T_EMPTY_BG = "#121213"
T_EMPTY_FG = "#818384"
T_TEXT     = "#FFFFFF"

WIRE_COLORS = ["#CC3333", "#EEEEEE", "#3399FF", "#33CC33", "#FFD633"]

KB_ROWS = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    ["ENTER"] + list("zxcvbnm") + ["⌫"],
]


# ══════════════════════════════════════════════════════════════════════════════
#  SOUND ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _make_sine(freq, duration_ms, volume=0.6, sample_rate=44100):
    """Return raw 16-bit PCM bytes for a sine wave."""
    n = int(sample_rate * duration_ms / 1000)
    import math
    data = bytearray()
    for i in range(n):
        v = int(32767 * volume * math.sin(2 * math.pi * freq * i / sample_rate))
        data += struct.pack('<h', v)
    return bytes(data)

def _make_wav_buffer(segments, sample_rate=44100):
    """segments = list of (freq, ms) or (freq, ms, volume)"""
    raw = b""
    for seg in segments:
        if len(seg) == 2:
            raw += _make_sine(seg[0], seg[1], 0.6, sample_rate)
        else:
            raw += _make_sine(seg[0], seg[1], seg[2], sample_rate)

    buf = bytearray()
    # WAV header
    data_size = len(raw)
    buf += b'RIFF'
    buf += struct.pack('<I', 36 + data_size)
    buf += b'WAVE'
    buf += b'fmt '
    buf += struct.pack('<I', 16)
    buf += struct.pack('<H', 1)           # PCM
    buf += struct.pack('<H', 1)           # mono
    buf += struct.pack('<I', sample_rate)
    buf += struct.pack('<I', sample_rate * 2)
    buf += struct.pack('<H', 2)
    buf += struct.pack('<H', 16)
    buf += b'data'
    buf += struct.pack('<I', data_size)
    buf += raw
    return bytes(buf)

def _load_sound(segments):
    if not AUDIO_OK:
        return None
    try:
        import io
        wav_bytes = _make_wav_buffer(segments)
        snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
        return snd
    except Exception:
        return None

# Pre-build all sounds
_SND_WIN   = None
_SND_LOSE  = None
_SND_TICK  = None
_SND_TICK_FAST = None
_SND_STRIKE = None
_SND_CORRECT = None

def _init_sounds():
    global _SND_WIN, _SND_LOSE, _SND_TICK, _SND_TICK_FAST, _SND_STRIKE, _SND_CORRECT
    if not AUDIO_OK:
        return
    # WIN: ascending fanfare
    _SND_WIN = _load_sound([
        (523, 120), (659, 120), (784, 120), (1047, 300),
        (0, 60),
        (784, 100), (1047, 100), (1319, 350),
    ])
    # LOSE: descending doom
    _SND_LOSE = _load_sound([
        (440, 180), (370, 200), (300, 250), (220, 400),
        (0, 80),
        (180, 500),
    ])
    # TICK: short click
    _SND_TICK = _load_sound([(880, 40, 0.3)])
    # FAST TICK (last 30 seconds)
    _SND_TICK_FAST = _load_sound([(1100, 35, 0.45)])
    # STRIKE
    _SND_STRIKE = _load_sound([
        (200, 100), (150, 150), (100, 200),
    ])
    # CORRECT
    _SND_CORRECT = _load_sound([
        (659, 100), (784, 100), (1047, 180),
    ])

def _play(snd):
    if AUDIO_OK and snd:
        try:
            snd.play()
        except Exception:
            pass

def play_win():    _play(_SND_WIN)
def play_lose():   _play(_SND_LOSE)
def play_tick(fast=False):
    _play(_SND_TICK_FAST if fast else _SND_TICK)
def play_strike(): _play(_SND_STRIKE)
def play_correct(): _play(_SND_CORRECT)


# ══════════════════════════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class State:
    stage:          str  = "BOOT"
    timer:          int  = COUNTDOWN
    active:         bool = False
    strikes_left:   int  = NUM_STRIKES
    code:           str  = "____"

    anagram_word:   str  = ""
    anagram_pool:   list = None
    anagram_rounds: int  = 0
    anagram_tries:  int  = 0

    ttt_board:      list = None

    w_secret:       str  = ""
    w_attempt:      int  = 0
    w_current:      str  = ""

    wire_pulled:    list = None
    kp_input:       str  = ""

    def __post_init__(self):
        if self.anagram_pool is None:
            self.anagram_pool = random.sample(ANAGRAM_POOL, len(ANAGRAM_POOL))
        if self.ttt_board is None:
            self.ttt_board = [""] * 9
        if self.wire_pulled is None:
            self.wire_pulled = []


# ══════════════════════════════════════════════════════════════════════════════
#  TTT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_TTT_WINS = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6),
]

def _ttt_winner(b, p):
    return any(b[a]==b[x]==b[y]==p for a,x,y in _TTT_WINS)

def _ttt_win_line(b, p):
    for ln in _TTT_WINS:
        if all(b[i]==p for i in ln):
            return ln
    return None

def _minimax(b, is_max, depth=0):
    if _ttt_winner(b, "O"): return 10 - depth
    if _ttt_winner(b, "X"): return depth - 10
    if all(b):              return 0
    scores = []
    for i in range(9):
        if b[i] == "":
            b[i] = "O" if is_max else "X"
            scores.append(_minimax(b, not is_max, depth + 1))
            b[i] = ""
    return max(scores) if is_max else min(scores)

def _best_move(b):
    if random.randint(1, 100) <= 50:
        empty = [i for i in range(9) if b[i] == ""]
        return random.choice(empty) if empty else None
    best, move = -99, None
    for i in range(9):
        if b[i] == "":
            b[i] = "O"
            s = _minimax(b, False)
            b[i] = ""
            if s > best:
                best, move = s, i
    return move


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN GAME CLASS
# ══════════════════════════════════════════════════════════════════════════════

class BombGame:

    def __init__(self, root):
        self.root  = root
        self.state = State()
        self._anim_ids = []   # track after() IDs for cancel on screen change

        self.root.title("Riddler's Revenge")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.root.update_idletasks()
        self._sw = self.root.winfo_screenwidth()
        self._sh = self.root.winfo_screenheight()

        self._d = [random.randint(0, 9) for _ in range(4)]
        self._final_code = "".join(str(x) for x in self._d)

        _init_sounds()
        self._build_ui()
        self._setup_hardware()
        self._show_boot()

    # ── UI skeleton ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        top = tk.Frame(self.root, bg=BG)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=6)

        self._timer_lbl = tk.Label(top, text="05:00",
            font=("Courier New", 26, "bold"), fg=RED, bg=BG)
        self._timer_lbl.pack(side="left", padx=(0, 20))

        self._code_lbl = tk.Label(top, text="CODE: ____",
            font=("Courier New", 20, "bold"), fg=GREEN, bg=BG)
        self._code_lbl.pack(side="left", padx=20)

        self._stage_lbl = tk.Label(top, text="BOOT",
            font=("Courier New", 13), fg=CYAN, bg=BG)
        self._stage_lbl.pack(side="left", padx=20)

        self._strike_lbl = tk.Label(top, text=f"STRIKES: {NUM_STRIKES}",
            font=("Courier New", 26, "bold"), fg=YELLOW, bg=BG)
        self._strike_lbl.pack(side="right")

        tk.Frame(self.root, bg=DIM, height=1).grid(row=0, column=0, sticky="sew")

        self.content = tk.Frame(self.root, bg=BG)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

    def _clear(self):
        # Cancel any pending animation callbacks
        for aid in self._anim_ids:
            try: self.root.after_cancel(aid)
            except: pass
        self._anim_ids = []

        for w in self.content.winfo_children():
            w.destroy()
        for seq in ("<Key>", "<Return>", "<BackSpace>"):
            try: self.root.unbind(seq)
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

    # ── Hardware ──────────────────────────────────────────────────────────────

    def _setup_hardware(self):
        if not RPi:
            return
        i2c = board.I2C()
        self._seg = Seg7x4(i2c)
        self._seg.brightness = 0.7

        self._toggles = []
        for pin in (board.D12, board.D16, board.D20, board.D21):
            d = digitalio.DigitalInOut(pin)
            d.direction = digitalio.Direction.INPUT
            d.pull      = digitalio.Pull.DOWN
            self._toggles.append(d)

        self._wires = []
        for pin in (board.D14, board.D15, board.D18, board.D23, board.D24):
            d = digitalio.DigitalInOut(pin)
            d.direction = digitalio.Direction.INPUT
            d.pull      = digitalio.Pull.DOWN
            self._wires.append(d)

        self._btn           = digitalio.DigitalInOut(board.D4)
        self._btn.direction = digitalio.Direction.INPUT
        self._btn.pull      = digitalio.Pull.DOWN

        cols = [digitalio.DigitalInOut(p) for p in (board.D10, board.D9, board.D11)]
        rows = [digitalio.DigitalInOut(p) for p in (board.D5, board.D6, board.D13, board.D19)]
        keys = ((1,2,3),(4,5,6),(7,8,9),("*",0,"#"))
        self._keypad  = Matrix_Keypad(rows, cols, keys)
        self._prev_kp = []

    def _hw_loop(self):
        self._update_top()
        if RPi:
            s = self.state.stage
            if s == "BOOT" and self._btn.value:
                # Debounce: wait 80ms and confirm still pressed before activating
                self.root.after(80, self._check_boot_button)
                return  # stop this loop instance; _check_boot_button re-arms it
            elif s == "TOGGLES":
                vals = [1 if t.value else 0 for t in self._toggles]
                if vals == TOGGLES_TARGET:
                    self.state.stage = "ANAGRAM"
                    self._set_code(f"{self._d[0]}___")
                    self.root.after(50, self._show_anagram)
            elif s == "WIRES":
                pulled = sorted([i+1 for i, w in enumerate(self._wires) if not w.value])
                if pulled == sorted(WIRES_TARGET):
                    self.state.stage = "FINAL"
                    self._wires_solved()
                elif len(pulled) >= len(WIRES_TARGET) and pulled != sorted(WIRES_TARGET):
                    self.state.stage = "WIRES_ERR"
                    if self._strike("Wrong wires pulled!"):
                        self.root.after(500, self._show_wires)
            elif s == "FINAL":
                self._poll_keypad()
        self.root.after(100, self._hw_loop)

    def _check_boot_button(self):
        """Debounce: only activate if button is still held after 80 ms."""
        if RPi and self.state.stage == "BOOT" and self._btn.value:
            self._activate()
        else:
            # Button was a bounce or released — keep polling
            self.root.after(100, self._hw_loop)

    def _poll_keypad(self):
        current  = list(self._keypad.pressed_keys)
        new_keys = [k for k in current if k not in self._prev_kp]
        self._prev_kp = current
        for key in new_keys:
            self._keypad_key(key)

    # ── Timer ─────────────────────────────────────────────────────────────────

    def _start_timer(self):
        self.state.active = True
        self._tick()

    def _tick(self):
        if not self.state.active:
            return
        if self.state.timer <= 0:
            self._explode("TIME OUT")
            return

        # Tick sound
        fast = self.state.timer <= 30
        play_tick(fast)

        self.state.timer -= 1
        m, s = divmod(self.state.timer, 60)

        if self.state.timer <= 30:
            colour = RED
        elif self.state.timer <= 60:
            colour = YELLOW
        else:
            colour = RED

        self._timer_lbl.config(text=f"{m:02}:{s:02}", fg=colour)

        # Pulse the timer label when under 60s
        if self.state.timer <= 60:
            self._timer_lbl.config(fg=RED)
            aid = self.root.after(250, lambda: self._timer_lbl.config(fg=YELLOW) if self.state.active else None)
            self._anim_ids.append(aid)

        if RPi:
            self._seg.print(f"{m:02}{s:02}")

        self.root.after(1000, self._tick)

    # ── Strikes & end conditions ───────────────────────────────────────────────

    def _strike(self, reason="Strike!"):
        play_strike()
        self.state.strikes_left -= 1
        self._update_top()
        # Flash strike label
        self._flash_label(self._strike_lbl, RED, YELLOW, 4)
        if self.state.strikes_left <= 0:
            self._explode(reason)
            return False
        # Show strike overlay instead of messagebox
        self._show_strike_overlay(reason)
        return True

    def _show_strike_overlay(self, reason):
        """Non-blocking strike warning that disappears after 2s."""
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.configure(bg="#220000")
        overlay.attributes("-topmost", True)
        w, h = 480, 160
        x = (self._sw - w) // 2
        y = (self._sh - h) // 2
        overlay.geometry(f"{w}x{h}+{x}+{y}")
        tk.Label(overlay, text="⚡  S T R I K E  ⚡",
                 fg=RED, bg="#220000", font=("Courier New", 26, "bold")).pack(pady=(18, 4))
        tk.Label(overlay, text=reason,
                 fg=YELLOW, bg="#220000", font=("Courier New", 14)).pack()
        tk.Label(overlay, text=f"{self.state.strikes_left} strike(s) remaining",
                 fg="white", bg="#220000", font=("Courier New", 12)).pack(pady=6)
        overlay.after(2000, overlay.destroy)

    def _flash_label(self, lbl, col_a, col_b, times):
        def _do(n):
            if n <= 0:
                return
            lbl.config(fg=col_a if n % 2 == 0 else col_b)
            self.root.after(120, lambda: _do(n - 1))
        _do(times * 2)

    # ── EXPLODE (lose screen) ─────────────────────────────────────────────────

    def _explode(self, reason=""):
        play_lose()
        self.state.active = False
        self._clear()
        c = self._C()

        canvas = tk.Canvas(c, width=700, height=400, bg="black", highlightthickness=0)
        canvas.pack()

        # Background
        canvas.create_rectangle(0, 0, 700, 400, fill="#0A0000", outline=RED, width=4)

        # Draw explosion circles (decorative)
        for i in range(8):
            import math
            angle = i * (360 / 8) * math.pi / 180
            rx = 350 + int(90 * math.cos(angle))
            ry = 120 + int(50 * math.sin(angle))
            r = random.randint(12, 28)
            canvas.create_oval(rx-r, ry-r, rx+r, ry+r, fill=YELLOW, outline=RED)

        canvas.create_text(350, 110, text="💥  B O O M  💥",
                           fill=RED, font=("Courier New", 50, "bold"))
        canvas.create_text(350, 210, text="THE RIDDLER WINS",
                           fill=YELLOW, font=("Courier New", 26, "bold"))
        canvas.create_text(350, 260, text=reason,
                           fill="white", font=("Courier New", 16))
        canvas.create_text(350, 310, text="Press Escape to quit",
                           fill=DIM, font=("Courier New", 12))

        # Flashing red border animation
        self._boom_flash(canvas, 0)

        # Restart button
        tk.Button(c, text="PLAY AGAIN",
                  fg=BG, bg=RED,
                  activeforeground=BG, activebackground=YELLOW,
                  font=("Courier New", 14, "bold"),
                  relief="flat", padx=20, pady=10,
                  command=self._restart).pack(pady=(12, 0))

    def _boom_flash(self, canvas, tick):
        colors = [RED, YELLOW, "#FF6600", RED, "#FF0000"]
        col = colors[tick % len(colors)]
        canvas.config(highlightthickness=6, highlightbackground=col)
        aid = self.root.after(300, lambda: self._boom_flash(canvas, tick + 1))
        self._anim_ids.append(aid)

    # ── WIN SCREEN ────────────────────────────────────────────────────────────

    def _win(self):
        play_win()
        self.state.active = False
        self._clear()
        c = self._C()

        canvas = tk.Canvas(c, width=700, height=400, bg="black", highlightthickness=0)
        canvas.pack()

        canvas.create_rectangle(0, 0, 700, 400, fill="#000A05", outline=GREEN, width=4)

        # Star/sparkle decorations
        for _ in range(18):
            x = random.randint(30, 670)
            y = random.randint(20, 380)
            r = random.randint(3, 9)
            canvas.create_oval(x-r, y-r, x+r, y+r,
                               fill=random.choice([GREEN, CYAN, YELLOW]),
                               outline="")

        canvas.create_text(350, 100, text="✔  D E F U S E D  ✔",
                           fill=GREEN, font=("Courier New", 44, "bold"))
        canvas.create_text(350, 185, text="YOU OUTSMARTED THE RIDDLER",
                           fill=CYAN, font=("Courier New", 22, "bold"))
        canvas.create_text(350, 240, text=f"Code entered: {self._final_code}",
                           fill=YELLOW, font=("Courier New", 16))
        canvas.create_text(350, 300, text="Gotham is safe... for now.",
                           fill="white", font=("Courier New", 14, "italic"))
        canvas.create_text(350, 360, text="Press Escape to quit",
                           fill=DIM, font=("Courier New", 11))

        # Twinkling animation
        self._sparkle(canvas, 0)

        tk.Button(c, text="PLAY AGAIN",
                  fg=BG, bg=GREEN,
                  activeforeground=BG, activebackground=CYAN,
                  font=("Courier New", 14, "bold"),
                  relief="flat", padx=20, pady=10,
                  command=self._restart).pack(pady=(12, 0))

    def _sparkle(self, canvas, tick):
        # Animate a random sparkle dot
        try:
            x = random.randint(30, 670)
            y = random.randint(20, 380)
            r = random.randint(2, 6)
            dot = canvas.create_oval(x-r, y-r, x+r, y+r,
                                     fill=random.choice([GREEN, CYAN, YELLOW]),
                                     outline="")
            canvas.after(400, lambda: canvas.delete(dot))
        except Exception:
            return
        aid = self.root.after(180, lambda: self._sparkle(canvas, tick + 1))
        self._anim_ids.append(aid)

    # ── Restart ───────────────────────────────────────────────────────────────

    def _restart(self):
        self._clear()
        self.state = State()
        self._hw_loop_running = False  # allow hw_loop to restart
        self._d = [random.randint(0, 9) for _ in range(4)]
        self._final_code = "".join(str(x) for x in self._d)
        self._timer_lbl.config(text="05:00", fg=RED)
        self._code_lbl.config(text="CODE: ____")
        self._show_boot()

    # ── BOOT SCREEN ───────────────────────────────────────────────────────────

    def _show_boot(self):
        self.state.stage = "BOOT"
        self._clear()
        c = self._C()

        # Animated title
        title_lbl = tk.Label(c, text="RIDDLER'S REVENGE",
                 fg=GREEN, bg=BG, font=("Courier New", 38, "bold"))
        title_lbl.pack(pady=(0, 20))

        tk.Label(c,
                 text=('"If you would like to see your friend again,\n'
                       'I suggest you press the silver button."\n\n— Riddler'),
                 fg="white", bg=BG, font=("Courier New", 18),
                 justify="center").pack(pady=10)

        if not RPi:
            tk.Button(c, text="[ PRESS TO START ]",
                      fg=BG, bg=GREEN,
                      activeforeground=BG, activebackground=CYAN,
                      font=("Courier New", 16, "bold"),
                      relief="flat", padx=24, pady=12,
                      command=self._activate).pack(pady=30)
            self.root.bind("<Return>", lambda e: self._activate())
            self.root.bind("<space>",  lambda e: self._activate())

        # Pulse the title
        self._pulse_label(title_lbl, GREEN, CYAN)

        # On Pi: start polling hardware immediately so button press is detected
        if RPi and not getattr(self, "_hw_loop_running", False):
            self._hw_loop_running = True
            self.root.after(100, self._hw_loop)

    def _pulse_label(self, lbl, c1, c2):
        """Gently alternate a label between two colors (boot screen only)."""
        def _do(use_c1=True):
            if self.state.stage != "BOOT":
                return
            try:
                lbl.config(fg=c1 if use_c1 else c2)
            except Exception:
                return
            aid = self.root.after(700, lambda: _do(not use_c1))
            self._anim_ids.append(aid)
        _do()

    def _activate(self):
        if self.state.stage != "BOOT":
            return  # guard against double-fire
        self._start_timer()
        # _hw_loop is already running (started in _show_boot); don't start again
        self._show_toggles()

    # ── TOGGLES ───────────────────────────────────────────────────────────────

    def _show_toggles(self):
        self.state.stage = "TOGGLES"
        self._clear()
        c = self._C()
        tk.Label(c,
                 text=('"Switches go up, switches go down.\n'
                       "If you can't make the number 13 in binary,\n"
                       'your friend will be in the ground."\n\n— Riddler'),
                 fg="white", bg=BG, font=("Courier New", 17),
                 justify="center").pack(pady=(0, 16))
        tk.Label(c, text="SET SWITCHES TO BINARY  1 3",
                 fg=RED, bg=BG, font=("Courier New", 22, "bold")).pack(pady=6)
        tk.Label(c, text="[ UP = 1  ·  DOWN = 0  ·  Target: 1101 = 13 ]",
                 fg=CYAN, bg=BG, font=("Courier New", 14)).pack(pady=4)

        if not RPi:
            tk.Label(c, text="Click the switches to toggle them",
                     fg=DIM, bg=BG, font=("Courier New", 11)).pack(pady=(14, 8))
            row = tk.Frame(c, bg=BG)
            row.pack(pady=6)
            self._toggle_state = [0, 0, 0, 0]
            self._toggle_btns  = []
            for i in range(4):
                def _make(idx):
                    def cb():
                        self._toggle_state[idx] ^= 1
                        up = self._toggle_state[idx]
                        self._toggle_btns[idx].config(
                            text=f"SW {idx+1}\n{'▲  UP' if up else '▼  DN'}",
                            fg=BG, bg=GREEN if up else DIM)
                        if self._toggle_state == TOGGLES_TARGET:
                            play_correct()
                            self.state.stage = "ANAGRAM"
                            self._set_code(f"{self._d[0]}___")
                            self.root.after(400, self._show_anagram)
                    return cb
                b = tk.Button(row, text=f"SW {i+1}\n▼  DN",
                              fg=BG, bg=DIM,
                              activeforeground=BG, activebackground=GREEN,
                              font=("Courier New", 14, "bold"),
                              width=8, height=3, relief="flat",
                              command=_make(i))
                b.pack(side="left", padx=12)
                self._toggle_btns.append(b)

    # ── ANAGRAM ───────────────────────────────────────────────────────────────

    def _show_anagram(self):
        self.state.stage       = "ANAGRAM"
        self.state.anagram_tries = 0
        self._clear()
        c = self._C()

        if not self.state.anagram_pool:
            self.state.anagram_pool = random.sample(ANAGRAM_POOL, len(ANAGRAM_POOL))
        self.state.anagram_word = self.state.anagram_pool.pop()

        letters = list(self.state.anagram_word)
        for _ in range(100):
            random.shuffle(letters)
            if "".join(letters) != self.state.anagram_word:
                break
        scrambled = "".join(letters)

        tk.Label(c, text="A N A G R A M S",
                 fg=GREEN, bg=BG, font=("Courier New", 28, "bold")).pack(pady=(0, 6))
        self._ana_round_lbl = tk.Label(
            c, text=f"Round {self.state.anagram_rounds + 1} of {ANAGRAM_ROUNDS}",
            fg=CYAN, bg=BG, font=("Courier New", 15))
        self._ana_round_lbl.pack(pady=4)
        tk.Label(c, text=" ".join(scrambled.upper()),
                 fg=YELLOW, bg=BG, font=("Courier New", 44, "bold")).pack(pady=20)
        self._ana_dots = tk.Label(c, text="◆  ◆  ◆",
                                  fg=RED, bg=BG, font=("Courier New", 20))
        self._ana_dots.pack(pady=6)

        ef = tk.Frame(c, bg=BG)
        ef.pack(pady=8)
        self._ana_entry = tk.Entry(ef, font=("Courier New", 22),
                                   fg=GREEN, bg=INPUT_BG,
                                   insertbackground=GREEN,
                                   relief="flat", bd=0, width=14, justify="center",
                                   highlightthickness=2, highlightbackground=GREEN)
        self._ana_entry.pack(side="left", ipady=8, padx=(0, 10))
        self._ana_entry.bind("<Return>", lambda e: self._check_anagram())
        self._ana_entry.focus()
        tk.Button(ef, text="SUBMIT",
                  fg=BG, bg=GREEN, activeforeground=BG, activebackground=CYAN,
                  font=("Courier New", 14, "bold"),
                  relief="flat", padx=16, pady=8,
                  command=self._check_anagram).pack(side="left")

        self._ana_status = tk.Label(c, text="",
                                    fg=RED, bg=BG, font=("Courier New", 15))
        self._ana_status.pack(pady=10)

    def _check_anagram(self):
        guess = self._ana_entry.get().strip().lower()
        self._ana_entry.delete(0, "end")
        if guess == self.state.anagram_word:
            play_correct()
            self.state.anagram_rounds += 1
            if self.state.anagram_rounds >= ANAGRAM_ROUNDS:
                self._ana_status.config(text="✓  Both solved!  Moving on...", fg=GREEN)
                self.root.after(1200, self._show_ttt)
            else:
                self._ana_status.config(
                    text=f"✓  Correct! ({self.state.anagram_word.upper()})  Next word...",
                    fg=GREEN)
                self.root.after(1200, self._show_anagram)
        else:
            self.state.anagram_tries += 1
            rem = ANAGRAM_ATTEMPTS - self.state.anagram_tries
            self._ana_dots.config(
                text=("◆  " * rem + "◇  " * self.state.anagram_tries).strip())
            if self.state.anagram_tries >= ANAGRAM_ATTEMPTS:
                self._ana_status.config(
                    text=f"✗  Failed.  Word was: {self.state.anagram_word.upper()}", fg=RED)
                if self._strike("Anagram failed!"):
                    self.root.after(2400, self._show_anagram)
            else:
                self._ana_status.config(
                    text=f"✗  Wrong.  {rem} attempt{'s' if rem != 1 else ''} left.", fg=RED)
                self._ana_entry.focus()

    # ── TIC TAC TOE ───────────────────────────────────────────────────────────

    def _show_ttt(self):
        self.state.stage     = "TTT"
        self.state.ttt_board = [""] * 9
        self._ttt_over       = False
        self._clear()

        avail = self._sh - 160
        CELL  = max(90, min(170, avail // 3))
        PAD   = 14
        self._CELL, self._PAD = CELL, PAD

        c = self._C()
        tk.Label(c, text="TIC  TAC  TOE",
                 fg=GREEN, bg=BG, font=("Courier New", 26, "bold")).pack(pady=(0, 4))
        tk.Label(c, text='"You better get three in a row, or like Mufasa you will go."  — Riddler',
                 fg=DIM, bg=BG, font=("Courier New", 11)).pack()
        tk.Label(c, text="You are  X  ·  Riddler is  O  ·  WIN to earn a code digit  ·  Draws restart free",
                 fg=CYAN, bg=BG, font=("Courier New", 13)).pack(pady=(4, 12))

        size = CELL * 3 + PAD * 2
        self._ttt_canvas = tk.Canvas(c, width=size, height=size,
                                     bg=INPUT_BG,
                                     highlightthickness=2, highlightbackground=GREEN)
        self._ttt_canvas.pack()
        self._ttt_canvas.bind("<Button-1>", lambda e: self._ttt_click(e, CELL, PAD))

        self._ttt_status = tk.Label(c, text="Your move",
                                    fg=GREEN, bg=BG, font=("Courier New", 15))
        self._ttt_status.pack(pady=12)
        self._ttt_draw_grid(CELL, PAD)

    def _ttt_draw_grid(self, C, P):
        cv = self._ttt_canvas
        cv.delete("all")
        for i in range(1, 3):
            cv.create_line(P, P+i*C, P+3*C, P+i*C, fill=GREEN, width=3)
            cv.create_line(P+i*C, P, P+i*C, P+3*C, fill=GREEN, width=3)

    def _ttt_centre(self, idx):
        C, P = self._CELL, self._PAD
        r, col = divmod(idx, 3)
        return P + col*C + C//2, P + r*C + C//2

    def _ttt_draw_x(self, idx):
        cx, cy = self._ttt_centre(idx)
        m = max(28, self._CELL // 4)
        self._ttt_canvas.create_line(cx-m, cy-m, cx+m, cy+m, fill=RED, width=7, capstyle="round")
        self._ttt_canvas.create_line(cx+m, cy-m, cx-m, cy+m, fill=RED, width=7, capstyle="round")

    def _ttt_draw_o(self, idx):
        cx, cy = self._ttt_centre(idx)
        r = max(28, self._CELL // 3)
        self._ttt_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=CYAN, width=7)

    def _ttt_draw_win_line(self, line):
        x1, y1 = self._ttt_centre(line[0])
        x2, y2 = self._ttt_centre(line[2])
        self._ttt_canvas.create_line(x1, y1, x2, y2, fill=GREEN, width=6, dash=(14, 6))

    def _ttt_click(self, event, C, P):
        if self._ttt_over: return
        col = (event.x - P) // C
        row = (event.y - P) // C
        if not (0 <= col < 3 and 0 <= row < 3): return
        idx = row * 3 + col
        if self.state.ttt_board[idx]: return

        self.state.ttt_board[idx] = "X"
        self._ttt_draw_x(idx)

        if _ttt_winner(self.state.ttt_board, "X"):
            self._ttt_over = True
            self._ttt_draw_win_line(_ttt_win_line(self.state.ttt_board, "X"))
            play_correct()
            self._set_code(f"{self._d[0]}{self._d[1]}__")
            self._ttt_status.config(text=f"YOU WIN!  Digit: {self._d[1]}", fg=GREEN)
            self.root.after(1800, self._show_wordle)
            return
        if all(self.state.ttt_board):
            self._ttt_over = True
            self._ttt_status.config(text="DRAW — no strike, try again!", fg=YELLOW)
            self.root.after(1400, self._show_ttt)
            return

        self._ttt_status.config(text="Riddler is thinking...", fg=DIM)
        self.root.after(380, self._ttt_ai_move)

    def _ttt_ai_move(self):
        move = _best_move(self.state.ttt_board)
        if move is None: return
        self.state.ttt_board[move] = "O"
        self._ttt_draw_o(move)
        if _ttt_winner(self.state.ttt_board, "O"):
            self._ttt_over = True
            self._ttt_draw_win_line(_ttt_win_line(self.state.ttt_board, "O"))
            self._ttt_status.config(text="RIDDLER WINS.  Strike.", fg=RED)
            if self._strike("The Riddler won Tic Tac Toe!"):
                self.root.after(2400, self._show_ttt)
            return
        if all(self.state.ttt_board):
            self._ttt_over = True
            self._ttt_status.config(text="DRAW — no strike, try again!", fg=YELLOW)
            self.root.after(1400, self._show_ttt)
            return
        self._ttt_status.config(text="Your move", fg=GREEN)

    # ── WORDLE ────────────────────────────────────────────────────────────────

    def _show_wordle(self):
        self.state.stage     = "WORDLE"
        pool                 = [w for w in WORD_BANK if w != self.state.w_secret]
        self.state.w_secret  = random.choice(pool)
        self.state.w_attempt = 0
        self.state.w_current = ""
        self._w_over         = False
        self._w_key_map      = {}
        self._clear()

        tile_sz   = max(36, min(62, (self._sh - 220) // WORDLE_ROWS))
        tile_font = max(13, tile_sz // 2)
        key_h     = 1 if tile_sz < 50 else 2

        c = self._C()
        tk.Label(c, text="W O R D L E",
                 fg=GREEN, bg=BG, font=("Courier New", 24, "bold")).pack(pady=(0, 2))
        tk.Label(c,
                 text='"Solve the word and earn the next piece.  Six chances."  — Riddler',
                 fg=DIM, bg=BG, font=("Courier New", 11)).pack()
        tk.Label(c, text=f"Guess the {WORDLE_COLS}-letter word  ·  {WORDLE_ROWS} attempts",
                 fg=CYAN, bg=BG, font=("Courier New", 13)).pack(pady=(4, 10))

        grid_frame = tk.Frame(c, bg=BG)
        grid_frame.pack()
        self._w_tiles = []
        for r in range(WORDLE_ROWS):
            row = []
            for col in range(WORDLE_COLS):
                cell = tk.Frame(grid_frame, width=tile_sz, height=tile_sz,
                                bg=T_EMPTY_BG,
                                highlightbackground=T_EMPTY_FG, highlightthickness=2)
                cell.grid(row=r, column=col, padx=3, pady=3)
                cell.pack_propagate(False)
                lbl = tk.Label(cell, text="", fg=T_TEXT, bg=T_EMPTY_BG,
                               font=("Courier New", tile_font, "bold"))
                lbl.pack(expand=True)
                row.append({"f": cell, "l": lbl})
            self._w_tiles.append(row)

        self._w_status = tk.Label(c, text="", fg=YELLOW, bg=BG, font=("Courier New", 13))
        self._w_status.pack(pady=6)

        kb = tk.Frame(c, bg=BG)
        kb.pack()
        for row_keys in KB_ROWS:
            rf = tk.Frame(kb, bg=BG)
            rf.pack()
            for key in row_keys:
                w = 5 if len(key) == 1 else 7
                lbl = tk.Label(rf, text=key.upper(), fg=T_TEXT, bg=T_ABSENT,
                               font=("Courier New", 11, "bold"), width=w, height=key_h)
                lbl.pack(side="left", padx=2, pady=2)
                lbl.bind("<Button-1>", lambda e, k=key: self._w_kb(k))
                if len(key) == 1:
                    self._w_key_map[key] = lbl

        self.root.bind("<Key>",       self._w_keypress)
        self.root.bind("<Return>",    lambda e: self._w_submit())
        self.root.bind("<BackSpace>", lambda e: self._w_backspace())

    def _w_kb(self, key):
        if self._w_over: return
        if key == "ENTER":  self._w_submit()
        elif key == "⌫":   self._w_backspace()
        elif len(key) == 1: self._w_add(key)

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

        result  = ["absent"] * WORDLE_COLS
        s_count = {}
        for i, (g, s) in enumerate(zip(guess, self.state.w_secret)):
            if g == s:  result[i] = "correct"
            else:       s_count[s] = s_count.get(s, 0) + 1
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
            play_correct()
            self._w_over = True
            self._set_code(f"{self._d[0]}{self._d[1]}{self._d[2]}_")
            self._w_status.config(text=f"✓  CORRECT!  Digit: {self._d[2]}", fg=GREEN)
            self.root.after(1800, self._show_wires)
            return
        if self.state.w_attempt >= WORDLE_ROWS:
            self._w_over = True
            self._w_status.config(
                text=f"✗  FAILED — Word was: {self.state.w_secret.upper()}", fg=RED)
            if self._strike("Wordle failed!"):
                self.root.after(2400, self._show_wordle)
            return
        rem = WORDLE_ROWS - self.state.w_attempt
        self._w_status.config(
            text=f"{rem} attempt{'s' if rem != 1 else ''} remaining", fg=YELLOW)

    # ── WIRES ─────────────────────────────────────────────────────────────────

    def _show_wires(self):
        self.state.stage       = "WIRES"
        self.state.wire_pulled = []
        self._clear()
        c = self._C()
        tk.Label(c, text="W I R E S",
                 fg=GREEN, bg=BG, font=("Courier New", 28, "bold")).pack(pady=(0, 10))
        tk.Label(c, text="Find the final clue.\nPull the correct wires.",
                 fg="white", bg=BG, font=("Courier New", 17), justify="center").pack(pady=8)
        tk.Label(c, text="[ Cut the right wires to reveal the last digit ]",
                 fg=CYAN, bg=BG, font=("Courier New", 13)).pack(pady=4)

        if not RPi:
            tk.Label(c, text="Click two wires to pull them",
                     fg=DIM, bg=BG, font=("Courier New", 11)).pack(pady=(14, 8))
            row = tk.Frame(c, bg=BG)
            row.pack(pady=8)
            self._wire_btns = []
            wire_labels = ["RED", "WHITE", "BLUE", "GREEN", "YELLOW"]
            for i, wc in enumerate(WIRE_COLORS):
                num = i + 1
                text_col = BG if wc != "#EEEEEE" else "#111"
                b = tk.Button(row,
                              text=f"WIRE {num}\n{wire_labels[i]}",
                              fg=text_col, bg=wc,
                              activeforeground=BG, activebackground=wc,
                              font=("Courier New", 13, "bold"),
                              width=9, height=3, relief="flat",
                              command=lambda n=num: self._toggle_wire(n))
                b.pack(side="left", padx=10)
                self._wire_btns.append(b)
            self._wire_status = tk.Label(c, text="No wires pulled.",
                                         fg=DIM, bg=BG, font=("Courier New", 14))
            self._wire_status.pack(pady=12)

    def _toggle_wire(self, num):
        if num in self.state.wire_pulled:
            self.state.wire_pulled.remove(num)
            wc = WIRE_COLORS[num-1]
            self._wire_btns[num-1].config(
                bg=wc,
                fg=BG if wc != "#EEEEEE" else "#111")
        else:
            self.state.wire_pulled.append(num)
            self._wire_btns[num-1].config(bg=DIM, fg="#999")

        pulled = sorted(self.state.wire_pulled)
        self._wire_status.config(
            text=f"Pulled: {pulled if pulled else 'none'}", fg=YELLOW)

        if pulled == sorted(WIRES_TARGET):
            play_correct()
            self._wire_status.config(text="✓  Correct wires!", fg=GREEN)
            self.state.stage = "FINAL"
            self.root.after(800, self._wires_solved)
        elif len(pulled) >= len(WIRES_TARGET) and pulled != sorted(WIRES_TARGET):
            self._wire_status.config(text="✗  Wrong wires!", fg=RED)
            if self._strike("Wrong wires pulled!"):
                self.root.after(2400, self._show_wires)

    def _wires_solved(self):
        self._set_code(self._final_code)
        self._show_final()

    # ── FINAL CODE ────────────────────────────────────────────────────────────

    def _show_final(self):
        self.state.stage    = "FINAL"
        self.state.kp_input = ""
        self._clear()
        c = self._C()
        tk.Label(c, text="ENTER THE CODE",
                 fg=RED, bg=BG, font=("Courier New", 26, "bold")).pack(pady=(0, 10))
        tk.Label(c, text=f"Correct wires pulled.\nFinal digit: {self._d[3]}\nFull code: {self._final_code}",
                 fg="white", bg=BG, font=("Courier New", 17), justify="center").pack(pady=8)

        self._kp_display = tk.Label(c, text="_ _ _ _",
                                    fg=GREEN, bg=BG,
                                    font=("Courier New", 52, "bold"))
        self._kp_display.pack(pady=16)
        self._kp_status = tk.Label(c, text="", fg=RED, bg=BG, font=("Courier New", 15))
        self._kp_status.pack(pady=4)

        if not RPi:
            pad = tk.Frame(c, bg=BG)
            pad.pack(pady=8)
            for row in [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]:
                rf = tk.Frame(pad, bg=BG)
                rf.pack()
                for k in row:
                    tk.Button(rf, text=k,
                              fg=GREEN, bg=INPUT_BG,
                              activeforeground=CYAN, activebackground="#1A1A2E",
                              font=("Courier New", 18, "bold"),
                              width=4, height=2, relief="flat",
                              highlightthickness=1, highlightbackground=DIM,
                              command=lambda k=k: self._keypad_key(k)).pack(
                                  side="left", padx=4, pady=4)
            self.root.bind("<Key>", self._final_keypress)

    def _final_keypress(self, event):
        ch = event.char
        if ch.isdigit():               self._keypad_key(ch)
        elif ch == "*":                self._keypad_key("*")
        elif event.keysym == "Return": self._keypad_key("#")
        elif event.keysym == "BackSpace":
            self.state.kp_input = self.state.kp_input[:-1]
            self._refresh_kp()

    def _keypad_key(self, key):
        if key == "*":
            self.state.kp_input = ""
            self._kp_status.config(text="Cleared.", fg=DIM)
        elif key == "#":
            if self.state.kp_input == self._final_code:
                self._kp_status.config(text="✓  CODE ACCEPTED", fg=GREEN)
                self.root.after(1200, self._win)
            else:
                self.state.kp_input = ""
                self._kp_status.config(text="✗  WRONG CODE", fg=RED)
                self._strike("Wrong code entered!")
        else:
            if len(self.state.kp_input) < len(self._final_code):
                self.state.kp_input += str(key)
        self._refresh_kp()

    def _refresh_kp(self):
        filled = list(self.state.kp_input)
        blanks = ["_"] * (len(self._final_code) - len(filled))
        self._kp_display.config(text="  ".join(filled + blanks))


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    game = BombGame(root)
    root.mainloop()
