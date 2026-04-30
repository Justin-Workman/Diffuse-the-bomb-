import tkinter as tk
from tkinter import messagebox
import random
import sys

COLOR_CORRECT = "#6aaa64"
COLOR_PRESENT = "#c9b458"
COLOR_ABSENT = "#787c7e"
COLOR_BG = "#121213"
COLOR_TEXT = "#ffffff"

class WordleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Riddler Wordle")
        self.root.geometry("400x600")
        self.root.configure(bg=COLOR_BG)

        self.word_bank = ["DEBUG", "INPUT", "ARRAY", "BYTES", "VIRUS", "CODER", "PRINT", "BOARD"]
        self.secret_word = random.choice(self.word_bank)
        self.current_guess_num = 0

        title = tk.Label(
            root,
            text="RIDDLER WORDLE",
            font=("Helvetica", 28, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT
        )
        title.pack(pady=20)

        self.grid_frame = tk.Frame(root, bg=COLOR_BG)
        self.grid_frame.pack(pady=10)

        self.cells = []
        for r in range(6):
            row_cells = []
            for c in range(5):
                cell = tk.Label(
                    self.grid_frame,
                    text="",
                    font=("Helvetica", 30, "bold"),
                    width=2,
                    height=1,
                    fg=COLOR_TEXT,
                    bg=COLOR_BG,
                    highlightbackground="#3a3a3c",
                    highlightthickness=2
                )
                cell.grid(row=r, column=c, padx=3, pady=3)
                row_cells.append(cell)
            self.cells.append(row_cells)

        self.entry = tk.Entry(root, font=("Helvetica", 24), width=10, justify="center")
        self.entry.pack(pady=20)
        self.entry.bind("<Return>", lambda event: self.submit_guess())

        self.submit_btn = tk.Button(root, text="SUBMIT", command=self.submit_guess)
        self.submit_btn.pack()

    def submit_guess(self):
        guess = self.entry.get().upper().strip()

        if len(guess) != 5 or not guess.isalpha():
            messagebox.showwarning("Invalid", "Enter a 5-letter word.")
            return

        self.update_grid(guess)
        self.current_guess_num += 1
        self.entry.delete(0, tk.END)

        if guess == self.secret_word:
            messagebox.showinfo("Code Piece Found", "You earned code piece: 2")
            self.root.destroy()
            sys.exit(0)

        if self.current_guess_num == 6:
            messagebox.showerror("Game Over", f"The word was {self.secret_word}.")
            self.root.destroy()
            sys.exit(1)

    def update_grid(self, guess):
        for i, char in enumerate(guess):
            cell = self.cells[self.current_guess_num][i]
            cell.config(text=char)

            if char == self.secret_word[i]:
                cell.config(bg=COLOR_CORRECT, highlightbackground=COLOR_CORRECT)
            elif char in self.secret_word:
                cell.config(bg=COLOR_PRESENT, highlightbackground=COLOR_PRESENT)
            else:
                cell.config(bg=COLOR_ABSENT, highlightbackground=COLOR_ABSENT)

if __name__ == "__main__":
    root = tk.Tk()
    game = WordleGUI(root)
    root.mainloop()
