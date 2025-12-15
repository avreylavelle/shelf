# ensures its a nonempty field (for required stuff, like text)
def input_nonempty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Please enter something. (exit)")
