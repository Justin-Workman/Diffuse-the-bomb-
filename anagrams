import tkinter as tk
from tkinter import messagebox
import random
import sys

WORDS = [
    "python", "binary", "network", "database", "variable",
    "function", "integer", "boolean", "debug", "hardware"
]

WINS_NEEDED = 5

class AnagramGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Riddler Anagram Test")
        self.root.geometry("500x350")

        self.score = 0
        self.current_word = ""

        self.title = tk.Label(root, text="RIDDLER ANAGRAM TEST", font=("Arial", 20, "bold"))
        self.title.pack(pady=10)

        self.score_label = tk.Label(root, text="Correct: 0/5", font=("Arial", 14))
        self.score_label.pack()

        self.word_label = tk.Label(root, text="", font=("Arial", 28, "bold"), fg="green")
        self.word_label.pack(pady=25)

        self.entry = tk.Entry(root, font=("Arial", 16), justify="center")
        self.entry.pack(pady=10)
        self.entry.bind("<Return>", lambda event: self.check_guess())

        self.feedback = tk.Label(root, text="", font=("Arial", 12))
        self.feedback.pack(pady=5)

        self.submit = tk.Button(root, text="Submit", command=self.check_guess)
        self.submit.pack(pady=10)

        self.next_word()

    def scramble_word(self, word):
        letters = list(word)
        scrambled = word
        while scrambled == word:
            random.shuffle(letters)
            scrambled = "".join(letters)
        return scrambled

    def next_word(self):
        self.current_word = random.choice(WORDS)
        self.word_label.config(text=self.scramble_word(self.current_word))
        self.entry.delete(0, tk.END)
        self.entry.focus()

    def check_guess(self):
        guess = self.entry.get().strip().lower()

        if guess == self.current_word:
            self.score += 1
            self.score_label.config(text=f"Correct: {self.score}/5")
            self.feedback.config(text="Correct.", fg="green")

            if self.score >= WINS_NEEDED:
                messagebox.showinfo("Code Piece Found", "You earned code piece: 5")
                self.root.destroy()
                sys.exit(0)
            else:
                self.root.after(700, self.next_word)
        else:
            messagebox.showerror("Wrong", f"Wrong. The word was {self.current_word}.")
            self.root.destroy()
            sys.exit(1)

if __name__ == "__main__":
    root = tk.Tk()
    game = AnagramGame(root)
    root.mainloop()
