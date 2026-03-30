from tkinter import *
import random

root = Tk()
root.title("Tic Tac Toe")

board = [""] * 9
buttons = []

def check_winner(player):
    win_combos = [
        (0,1,2), (3,4,5), (6,7,8),
        (0,3,6), (1,4,7), (2,5,8),
        (0,4,8), (2,4,6)
    ]
    for combo in win_combos:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] == player:
            return True
    return False

def check_tie():
    return "" not in board

def computer_move():
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            if check_winner("O"):
                update_button(i, "O")
                return
            board[i] = ""

    for i in range(9):
        if board[i] == "":
            board[i] = "X"
            if check_winner("X"):
                board[i] = "O"
                update_button(i, "O")
                return
            board[i] = ""

    if board[4] == "":
        update_button(4, "O")
        return

    empty = [i for i in range(9) if board[i] == ""]
    if empty:
        move = random.choice(empty)
        update_button(move, "O")

def update_button(index, player):
    board[index] = player
    buttons[index]["text"] = player
    buttons[index]["state"] = DISABLED

    if check_winner(player):
        status.config(text=f"{player} wins!")
        disable_all()
    elif check_tie():
        status.config(text="It's a tie!")
    elif player == "X":
        root.after(500, computer_move)

def player_move(index):
    if board[index] == "":
        update_button(index, "X")

def disable_all():
    for b in buttons:
        b["state"] = DISABLED

def reset():
    global board
    board = [""] * 9
    for b in buttons:
        b["text"] = ""
        b["state"] = NORMAL
    status.config(text="Your turn!")

for i in range(9):
    button = Button(root, text="", font=("Arial", 20), width=5, height=2,
                    command=lambda i=i: player_move(i))
    button.grid(row=i//3, column=i%3)
    buttons.append(button)

status = Label(root, text="Your turn!", font=("Arial", 14))
status.grid(row=3, column=0, columnspan=3)

reset_btn = Button(root, text="Reset", command=reset)
reset_btn.grid(row=4, column=0, columnspan=3)

root.mainloop()