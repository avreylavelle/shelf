from recommender.ml_model import train_user_model, recommend_for_user

def ui_machine_learning(profile):
    print(f"Entering Machine Learning Menu for {profile['username']}.")
    while True:
        print("\n=== Machine Learning Menu ===")
        print("1. View ML Recommendations")
        print("2. Train New Model")
        print("3. Exit ML Menu")

        choice = input("Choice: ").strip()

        if choice == "1":
            print("Displaying ML Recommendations...")
            recommend_for_user(profile)

        elif choice == "2":
            print("Training New Model")
            train_user_model(profile)

        elif choice == "3":
            print("Exiting Machine Learning Menu.")
            break

        else:
            print("Invalid choice. Please try again.")