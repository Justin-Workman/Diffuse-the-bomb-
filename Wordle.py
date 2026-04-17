import tkinter as tk
from tkinter import messagebox
import random

COLOR_CORRECT = "#6aaa64"  
COLOR_PRESENT = "#c9b458"  
COLOR_ABSENT = "#787c7e"   
COLOR_BG = "#121213"       
COLOR_TEXT = "#ffffff"     

class WordleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Wordle Pro")
        self.root.geometry("400x600")
        self.root.configure(bg=COLOR_BG)

        self.word_bank = ["DEBUG", "INPUT", "ARRAY", "BYTES", "VIRUS", "CODER", "PRINT", "BOARD"]
        self.secret_word = random.choice(self.word_bank).upper()
        self.current_guess_num = 0
        self.guesses = []

        self.title_label = tk.Label(root, text="Difuse the BOMB Wordle", font=("Helvetica", 36, "bold"), bg=COLOR_BG, fg=COLOR_TEXT, pady=20)
        self.title_label.pack()

        self.grid_frame = tk.Frame(root, bg=COLOR_BG)
        self.grid_frame.pack(pady=10)
        
        self.cells = []
        for r in range(6):
            row_cells = []
            for c in range(5):
                cell = tk.Label(self.grid_frame, text="", font=("Helvetica", 30, "bold"),
                                width=2, height=1, fg=COLOR_TEXT, bg=COLOR_BG,
                                highlightbackground="#3a3a3c", highlightthickness=2, bd=0)
                cell.grid(row=r, column=c, padx=3, pady=3)
                row_cells.append(cell)
            self.cells.append(row_cells)

        self.entry = tk.Entry(root, font=("Helvetica", 24), width=10, justify="center", insertbackground="white", bg="#3a3a3c", fg="white", bd=0)
        self.entry.pack(pady=20)
        self.entry.bind("<Return>", lambda event: self.submit_guess())
        self.entry.focus_set()

        self.submit_btn = tk.Button(root, text="SUBMIT GUESS", command=self.submit_guess, bg="#818384", fg="white", font=("Helvetica", 12, "bold"))
        self.submit_btn.pack()

    def submit_guess(self):
        guess = self.entry.get().upper()
        
        if len(guess) != 5 or not guess.isalpha():
            messagebox.showwarning("Invalid", "Please enter a 5-letter word!")
            return

        if self.current_guess_num < 6:
            self.update_grid(guess)
            self.current_guess_num += 1
            self.entry.delete(0, tk.END)

            if guess == self.secret_word:
                messagebox.showinfo("Winner!", f"Splendid! The word was {self.secret_word}")
                self.root.destroy()
            elif self.current_guess_num == 6:
                messagebox.showinfo("Game Over", f"The word was {self.secret_word}")
                self.root.destroy()

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
