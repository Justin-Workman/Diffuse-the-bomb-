import random

# List of words for the game
WORDS = [
    "python", "planet", "school", "computer", "garden",
    "friend", "puzzle", "orange", "animal", "library"
]

def scramble_word(word):
    """Return a scrambled version of the word."""
    letters = list(word)
    while True:
        random.shuffle(letters)
        scrambled = "".join(letters)
        if scrambled != word:  # make sure it is actually scrambled
            return scrambled

def play_game():
    print("Welcome to the Anagrams Game!")
    print("Unscramble the letters to make the correct word.")
    print("Type 'quit' anytime to stop.\n")

    score = 0

    while True:
        word = random.choice(WORDS)
        scrambled = scramble_word(word)

        print(f"Unscramble this word: {scrambled}")
        guess = input("Your guess: ").lower().strip()

        if guess == "quit":
            print(f"\nThanks for playing! Final score: {score}")
            break

        if guess == word:
            score += 1
            print("Correct!\n")
        else:
            print(f"Wrong! The word was: {word}\n")

        print(f"Score: {score}\n")

if __name__ == "__main__":
    play_game()