import tkinter as tk
from tkinter import messagebox
import random
import sys

class TicTacToe:
    def __init__(self, root):
        self.root = root
        self.root.title("Riddler Tic-Tac-Toe")
        self.root.geometry("360x430")

        self.board = [""] * 9
        self.buttons = []

        title = tk.Label(root, text="BEAT THE RIDDLER", font=("Arial", 20, "bold"))
        title.pack(pady=10)

        frame = tk.Frame(root)
        frame.pack()

        for i in range(9):
            button = tk.Button(
                frame,
                text="",
                font=("Arial", 28, "bold"),
                width=4,
                height=2,
                command=lambda i=i: self.player_move(i)
            )
            button.grid(row=i // 3, column=i % 3)
            self.buttons.append(button)

    def player_move(self, index):
        if self.board[index] != "":
            return

        self.board[index] = "X"
        self.buttons[index].config(text="X")

        if self.check_winner("X"):
            messagebox.showinfo("Code Piece Found", "You earned code piece: 4")
            self.root.destroy()
            sys.exit(0)

        if "" not in self.board:
            messagebox.showinfo("Tie", "Tie. No strike.")
            self.reset_board()
            return

        self.riddler_move()

        if self.check_winner("O"):
            messagebox.showerror("Lost", "The Riddler beat you.")
            self.root.destroy()
            sys.exit(1)

        if "" not in self.board:
            messagebox.showinfo("Tie", "Tie. No strike.")
            self.reset_board()

    def riddler_move(self):
        empty = [i for i, value in enumerate(self.board) if value == ""]
        move = random.choice(empty)
        self.board[move] = "O"
        self.buttons[move].config(text="O")

    def check_winner(self, symbol):
        wins = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]

        for combo in wins:
            if all(self.board[i] == symbol for i in combo):
                return True

        return False

    def reset_board(self):
        self.board = [""] * 9
        for button in self.buttons:
            button.config(text="")

if __name__ == "__main__":
    root = tk.Tk()
    game = TicTacToe(root)
    root.mainloop()
