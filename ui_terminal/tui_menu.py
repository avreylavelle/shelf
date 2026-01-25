from utils.input import input_nonempty
from services.library import (
    load_manga_dataset,
    load_user_index,
    get_profile,
    similar_username,
    save_user_profile,
)
from ui_terminal.tui_recommend import ui_recommend
from ui_terminal.tui_profile import edit_profile

# Main loop for everything
def ui_sign_in(manga_df, user_df):
    while True:
        print("\n=== Sign In ===")
        username = input_nonempty("Username: ") # get username

        profile = get_profile(user_df, username) # find profile

        if profile: # if a profile exists 
            return sign_in_loop(manga_df, user_df, profile)

        # Username not found
        print("User not found.")
        suggestions = similar_username(user_df, username, n=1) # if nothing is found, recommend a closely related name
        if suggestions:
            print("Did you mean:")
            s = ""
            for i in range(len(suggestions)): # suggest it
                s = suggestions[i]
                print(" -", s)
            if input("Use suggested? (y/n): ").lower() == "y": # if yes proceed
                chosen = s
                profile = get_profile(user_df, chosen)
                if profile:
                    return sign_in_loop(manga_df, user_df, profile)
                print("Still not found. Creating new instead.") # move to creating a new profile instead (done in main)

        user_df, profile = create_profile(user_df, default_username=username)
        
        if profile:
            return user_df

        print("Account Creation Failed.")
        


# sign_in_loop
def sign_in_loop(manga_df, user_df, profile):

    while True:
        username = profile["username"]

        # TEMP

        
        print(f"Welcome back, {username}.")
        print("1. Edit your profile?")
        print("2. Proceed to Recommender")
        print("3. Sign out")

        choice = input("Choice: ").strip()

        if choice == "1":
            profile = edit_profile(profile, manga_df)
            user_df = save_user_profile(user_df, profile)
            print("Profile updated.")

        elif choice == "2":
            user_df, profile, _ = ui_recommend(manga_df, user_df, profile)

        elif choice == "3":
            print(f"Signing out {username}.")
            return user_df

        else:
            print("Invalid choice.")

# ui_create_profile
def create_profile(user_df, default_username=None):
    suggested = False

    print("\n=== Create Profile ===")
    # If there is a username, from suggested
    if default_username:
        print(f"Suggested username: {default_username}\n") # ask about it
        suggested = True

    while True:
        name = ""
        message = "Username"
        message += " (or press Enter to accept, exit to exit): " if suggested else ": "
        name = input(message).strip()
        username = name if name else default_username

        if username == "exit":
            return user_df, None
        # Ensures users will not be overwritten and accidentally deleted
        existing_usernames = []
        for user in user_df["username"]:
            existing_usernames.append(user)
        if username in existing_usernames:
            print(f"Username {username} found in database.")
            choice = input_nonempty(f" === Overwrite {username}? (y/n) === ")

            if choice != "y":
                continue
        
        break


    # text to ask for other values
    age = input("Age: ").strip()
    age = int(age) if age.isdigit() else None

    gender = input("Gender: ").strip()

    # g = input("Favorite genres: ").strip()
    # t = input("Favorite themes: ").strip()

    # genres = [x.strip() for x in g.split(",") if x.strip()]
    # themes = [x.strip() for x in t.split(",") if x.strip()]

    profile = {
        "username": username,
        "age": age,
        "gender": gender,
        "preferred_genres": {},
        "preferred_themes": {},
    }

    # Create the new profile
    user_df = save_user_profile(user_df, profile)
    print("Profile created.")
    return user_df, profile

def main_menu():
    print("=== Manga Recommender ===")

    manga = load_manga_dataset()
    users = load_user_index()

    while True:
        print("\nMain Menu:")
        print("1. Sign In / Sign Up")
        # print("2. Create/Edit Profile")
        print("3. Quit")

        choice = input("Choice: ").strip()

        if choice == "1":
            users = ui_sign_in(manga, users)
        
        # elif choice == "2":
        #     username = input_nonempty("Username to edit/create: ")
        #     profile = get_profile(users, username)
        #     if profile:
        #         profile = ui_edit_profile(profile, manga)
        #         users = update_user_profile(users, profile)
        #     else:
        #         users, profile = ui_create_profile(users, default_username=username)
        #     print("Profile saved.")

        elif choice == "3":
            print("Goodbye.")
            break

        else:
            print("Invalid choice.")
