from utils.lookup import pick_top_from_counts, get_all_unique
from services.library import save_user_profile
from services.recommendations import get_recommendations

# ui_collect_current_prefrences
def ui_collect_current_preferences(profile, manga_df):
    print("\n=== Preferences for Recommendations ===")

    # THis uses a function to find the most commonly occuring ones.      \/ <- Right here, you can alter how many. I currently have it for 3 genres, 2 themes.
    suggested_genres = pick_top_from_counts(profile["preferred_genres"], 3)
    suggested_themes = pick_top_from_counts(profile["preferred_themes"], 2)

    # If anything is found
    if suggested_genres or suggested_themes:
        # Asks user to use previous preferences.
        # Im thinking this is not going to be in UI, perhaps just fill in the dropdown boxes with the most commonly occuring?
        print("Suggested based on your history:")
        print("  Genres:", suggested_genres)
        print("  Themes:", suggested_themes)
        choice = input("Use these? (y/n) (e for empty): ").strip().lower()
        if choice == "y":
            return suggested_genres, suggested_themes
        elif choice == "e":
            return [], []
    # Ask for new ones
    print("\nAvailable Genres:")
    print(", ".join(get_all_unique(manga_df, "genres")))
    g = input("Enter genres (comma-separated): ")
    current_genres = [x.strip() for x in g.split(",") if x.strip()]

    print("\nAvailable Themes:")
    print(", ".join(get_all_unique(manga_df, "themes")))
    t = input("Enter themes (comma-separated): ")
    
    current_themes = [x.strip() for x in t.split(",") if x.strip()]

    print(",  ".join(get_all_unique(manga_df, "item_type")))

    # Update running counts
    for g in current_genres:
        profile["preferred_genres"][g] = profile["preferred_genres"].get(g, 0) + 1
    for t in current_themes:
        profile["preferred_themes"][t] = profile["preferred_themes"].get(t, 0) + 1

    return current_genres, current_themes

# UI for recommending
def ui_recommend(manga_df, user_df, profile):
    current_genres, current_themes = ui_collect_current_preferences(profile, manga_df) # gather pervious preferences

    # Update running weights
    user_df = save_user_profile(user_df, profile)

    # sanity print
    print("\nRecommending...")

    # find recommendations based on all data
    ranked, used_current = get_recommendations(
        profile["username"], current_genres, current_themes, k=20
    )
    if ranked is None:
        print("No user profile found.")
        return user_df, profile, ranked

    # printing
    print("\n=== Recommendations ===")
    # If nothing is returned (shouldn't happen, it'll return 0 scores)
    if ranked.empty:
        print("No matches found")
        return user_df, profile, ranked
    
    # If the requested genres/themes do not exist, or nothing else is left
    if not used_current:
        print("No matches found for requested Genres and Themes")
        print("   Showing recommendations based on profile history.")

    # print recommendations
    row_history = []
    for i, (_, row) in enumerate(ranked.iterrows(), 1):
        row_history.append(row)
        print(f"\n#{i}: {row['title_name']}")
        print("Genres:", row["genres"])
        print("Themes:", row["themes"])
        print("Internal Score:", row["internal_score"])
        print("Match Score:", round(row["match_score"], 3))
        print("Combined Score: ", round(row["combined_score"], 3))
        # print("Publishing Date:", row.get("publishing_date", "Unknown"))
        # print("Status:", row.get("status", "Unknown_print")) # Finished, Publishing
        print()
        print("-" * 40)

        
        #  print 5, ask to see more
        if i % 5 == 0:
            cont_print = False
            choice = input("Show more? (y/n)").lower()   
            if choice != "y":
                break

    while True:
        choice = input("View more Details for Entry? (number): ").lower()

        try:
            choice = int(choice)
            req_row = row_history[choice - 1]
            print(f"\nDetails for entry {choice}:\n")
            print(f"Name: {req_row.get('title_name', 'Unknown')}")
            print("Type:", req_row.get("item_type", "Unknown"))
            print("Volumes:", req_row.get("volumes", "Unknown"))
            print("Chapters:", req_row.get("chapters", "Unknown"))
            print("Status:", req_row.get("status", "Unknown_print"))
            print("Publishing Date:", req_row.get("publishing_date", "Unknown"))
            print("Authors:", req_row.get("authors", []))
            print("Demographic:", req_row.get("demographic", []))
            print("Description:", req_row.get("description", "None"))
            print("Background:", req_row.get("background", "None")) # Added .get, if empty it crashes
            print()
            print("-" * 40)
        
        except:
            break

        

    # WE need a way to click on recommendations and add them to the list. Gonna wait til the UI
    return user_df, profile, ranked

