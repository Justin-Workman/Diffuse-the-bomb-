import tkinter as tk
from tkinter import messagebox
import random

WORDS = [
    "python", "binary", "network", "database", "variable", "function", "integer", "boolean", "debugging", "hardware", "keyboard",
    "internet", "program", "loop", "string"
]

TOTAL_ROUNDS = 5
POINTS_TO_WIN = 3

class AnagramGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Anagrams")
        self.root.geometry("500x350")
        self.root.resizable(False, False)

        self.score = 0
        self.round_number = 0
        self.current_word = ""
        self.used_words = []

        self.title_label = tk.Label(root, text="Anagrams", font=("Arial", 20, "bold"))
        self.title_label.pack(pady=10)

        self.round_label = tk.Label(root, text="Round: 0/5", font=("Arial", 12))
        self.round_label.pack()

        self.score_label = tk.Label(root, text="Score: 0", font=("Arial", 12))
        self.score_label.pack(pady=5)

        self.word_label = tk.Label(root, text="", font=("Arial", 24, "bold"), fg="blue")
        self.word_label.pack(pady=20)

        self.guess_entry = tk.Entry(root, font=("Arial", 14), justify="center")
        self.guess_entry.pack(pady=10)

        self.feedback_label = tk.Label(root, text="", font=("Arial", 12))
        self.feedback_label.pack(pady=5)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)

        self.submit_button = tk.Button(self.button_frame, text="Submit Guess", font=("Arial", 12), command=self.check_guess)
        self.submit_button.grid(row=0, column=0, padx=5)

        self.hint_button = tk.Button(self.button_frame, text="Hint", font=("Arial", 12), command=self.show_hint)
        self.hint_button.grid(row=0, column=1, padx=5)

        self.restart_button = tk.Button(self.button_frame, text="Restart", font=("Arial", 12), command=self.restart_game)
        self.restart_button.grid(row=0, column=2, padx=5)

        self.guess_entry.bind("<Return>", lambda event: self.check_guess())

        self.next_round()

    def scramble_word(self, word):
        letters = list(word)
        scrambled = word
        while scrambled == word:
            random.shuffle(letters)
            scrambled = "".join(letters)
        return scrambled

    def next_round(self):
        if self.round_number >= TOTAL_ROUNDS:
            self.end_game()
            return

        self.round_number += 1
        self.round_label.config(text=f"Round: {self.round_number}/{TOTAL_ROUNDS}")
        self.score_label.config(text=f"Score: {self.score}")

        available_words = [word for word in WORDS if word not in self.used_words]
        if not available_words:
            self.end_game()
            return

        self.current_word = random.choice(available_words)
        self.used_words.append(self.current_word)

        scrambled = self.scramble_word(self.current_word)
        self.word_label.config(text=scrambled)
        self.guess_entry.delete(0, tk.END)
        self.feedback_label.config(text="")
        self.guess_entry.focus()

    def check_guess(self):
        guess = self.guess_entry.get().strip().lower()

        if guess == "":
            self.feedback_label.config(text="Please enter a guess.", fg="red")
            return

        if guess == self.current_word:
            self.score += 1
            self.feedback_label.config(text="Correct!", fg="green")
        else:
            self.feedback_label.config(
                text=f"Wrong! The word was '{self.current_word}'.",
                fg="red"
            )

        self.score_label.config(text=f"Score: {self.score}")
        self.root.after(1200, self.next_round)

    def show_hint(self):
        first_letter = self.current_word[0].upper()
        word_length = len(self.current_word)
        messagebox.showinfo("Hint", f"The word starts with '{first_letter}' and has {word_length} letters.")

    def end_game(self):
        self.word_label.config(text="")
        self.guess_entry.delete(0, tk.END)

        if self.score >= POINTS_TO_WIN:
            self.feedback_label.config(
                text=f"You WIN! Final Score: {self.score}/{TOTAL_ROUNDS}",
                fg="green"
            )
            messagebox.showinfo("Game Over", f"You WIN!\nFinal Score: {self.score}/{TOTAL_ROUNDS}")
        else:
            self.feedback_label.config(
                text=f"You LOSE! Final Score: {self.score}/{TOTAL_ROUNDS}",
                fg="red"
            )
            messagebox.showinfo("Game Over", f"You LOSE!\nFinal Score: {self.score}/{TOTAL_ROUNDS}")

    def restart_game(self):
        self.score = 0
        self.round_number = 0
        self.current_word = ""
        self.used_words = []
        self.feedback_label.config(text="")
        self.next_round()

if __name__ == "__main__":
    root = tk.Tk()
    game = AnagramGame(root)
    root.mainloop()
