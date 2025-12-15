from recommender.ml_model import train_user_model, recommend_for_user, analyze_global_features, analyze_user_features

def ui_machine_learning(profile):
    print(f"Entering Machine Learning Menu for {profile['username']}.")
    while True:
        print("\n=== Machine Learning Menu ===")
        print("1. View ML Recommendations")
        print("2. Train New Model")
        print("3. Analyze Global Features")
        print("4. Analyze Your Features")
        print("5. Exit Machine Learning Menu")

        choice = input("Choice: ").strip()

        if choice == "1":
            print("Displaying ML Recommendations...")
            reccomendations = recommend_for_user(profile)

        elif choice == "2":
            print("Training New Model")
            train_user_model(profile)

        elif choice == "3":
            print("Analyzing Global Features...")
            results = analyze_global_features()

            print("\nTop 20 Pearson correlations:")
            print(results["pearson"].head(20))

            print("\nTop 20 Mutual Information:")
            print(results["mutual_info"].head(20))

            print("\nTop 20 RF Importances:")
            print(results["rf_importances"].head(20))

        elif choice == "4":
            print("Analyzing Your Features...")
            results = analyze_user_features(profile)

            if results is None:
                continue

            print("\nTop 20 User Pearson correlation:")
            print(results["pearson"].head(20))

            print("\nTop 20 User Mutual Information:")
            print(results["mutual_info"].head(20))

            print("\nTop 20 User RF Importances:")
            print(results["rf_importances"].head(20))

        elif choice == "5":
            print("Exiting Machine Learning Menu.")
            break

        else:
            print("Invalid choice. Please try again.")