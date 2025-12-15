from utils.input import input_nonempty
from difflib import get_close_matches

# ui_edit_profile
def edit_profile(profile, manga_df):
    print("\n=== Edit Profile ===")

    # If you wish to update name, do it here
    while True:
        username = profile["username"]
        
        # Ask user, prompt for changes
        print(f"Welcome back, {username}.")
        print("1. Username")
        print("2. Age")
        print("3. Gender")
        print("4. Clear History (NOT FINISHED MANGAS)")
        print("5. Adjust Finished Entries")
        print("6. Exit")

        choice = input("Choice: ").strip()

        if choice == "1":
            new_name = input(f"Username ({profile['username']}): ").strip()
            if new_name:
                profile["username"] = new_name

        elif choice == "2":
            age_str = input(f"Age ({profile['age']}): ").strip()
            if age_str:
                try:
                    profile["age"] = int(age_str)
                except:
                    print("Invalid age")

        elif choice == "3":
            gender = input(f"Gender ({profile['gender']}): ").strip()
            if gender:
                profile["gender"] = gender

        elif choice == "4":
            hist_str = input("Are you sure? (y/n)")
            if hist_str !="y":
                continue
            profile["preferred_genres"] = {}
            profile["preferred_themes"] = {}
            print("History Deleted.")

        elif choice == "5":
            ui_adjust_manga_entries(profile, manga_df)

        elif choice == "6":
            print("Profile Saved")
            break

        else:
            print("Invalid choice.")

    return profile

# ui_adjust_manga_entires
def ui_adjust_manga_entries(profile, manga_df):
    
    df = manga_df.copy() # gonna be altered, messed up the cleaned dataset if you dont makea  copy
    all_titles = df["title_name"].astype(str).tolist()
    title_lookup = {t.lower(): t for t in all_titles} # lookupw with lower and names (keys are the real names)
    
    print("\n=== Read Manga ===")
    for i, (title, rating) in enumerate(profile["read_manga"].items(), start=1):
        print(f"{i}:  {title}: {rating}")

    while True:
        print("\nRead manga options:")
        print("1. Add/update manga rating")
        print("2. Remove manga")
        print("3. Sort list")
        print("4. Done")

        ch = input("Choice: ").strip()
        # add and rate a manga
        if ch == "1":
            add_manga_rating(profile, df, title_lookup)
        # remove a manga (not needed?)
        elif ch == "2":
            title = input_nonempty("Title to remove: ")
            profile["read_manga"].pop(title, None)

        elif ch == "3":
            sort_read_manga_list(profile)

        elif ch == "4":
            break

        else:
            print("Invalid Choice.")
        
def add_manga_rating(profile, df, title_lookup):
    while True:
        chosen_title = ""
        requested_title = input_nonempty("-------------------" \
        "\nTitle (exit to exit): ").strip() # request title
        if requested_title == "exit": # if user says exit, exit
            break
        requested_lower = requested_title.lower() # make lower (for matching

        # NEED TO ADD
        # USE SYNONYMS IN THIS SECTION
        # NEED TO ADD


        if requested_lower in title_lookup: # matching
            chosen_title = title_lookup[requested_lower] # matches, move on
        else:
            # checks if the substring entered is in the name (these names are fucking massive)
            substring_match = []

            # goes through names, if its in any name, add it (some entries are in here multiple times?)
            import string
            for title_name in title_lookup.keys():
                translator = str.maketrans({p: " " for p in string.punctuation})
                translated_title_name = title_name.translate(translator)
                if "darling" in translated_title_name.lower() and "dress" in translated_title_name.lower(): print(title_name.lower()) 
                if requested_lower in translated_title_name.lower():
                    substring_match.append(title_name)

            # ADDED after the fact, sorts names by internal rating ( most popular first )   
            temp = []
            for name in substring_match:
                real_title = title_lookup[name]
                try: 
                    score = float(df.loc[df["title_name"] == real_title, "score"].fillna(0).iloc[0]) # gets score for name
                except:
                    score = 0.0

                temp.append((score, name))

            temp.sort(reverse=True)

            substring_match = []
            for score, name in temp:
                substring_match.append(name)

            # if you get one
            if substring_match:
                print(f"Did you mean:") # print them all
                for i in range(len(substring_match)):
                    print(f"{i+1}: {substring_match[i]}")
                while True:
                    print(f"{len(substring_match) + 1}: --- Continue to Suggestions ---")
                    try:
                        title_choice = input_nonempty("Choice: ").strip() # decision
                        title_choice = int(title_choice) # turns string to int
                        break
                    except:
                        print("Invalid Choice.")

                if title_choice == len(substring_match) + 1: # this prints "Proceed to suggestions" ^^^
                    pass
                else:
                    chosen_title = title_lookup[substring_match[title_choice-1]]
            
            # if no direct match
            if not chosen_title:
                suggestions = get_close_matches(requested_lower, list(title_lookup.keys()), n=10, cutoff=0.1) # gather suggestions
                for name in suggestions:
                    real_title = title_lookup[name]
                    try: 
                        score = float(df.loc[df["title_name"] == real_title, "score"].fillna(0).iloc[0]) # gets score for name
                    except:
                        score = 0.0

                    temp.append((score, name))

                temp.sort(reverse=True)
                suggestions = []
                for score, name in temp:
                    suggestions.append(name)
                    
                if suggestions: # if they were generated
                    cont_print = True
                    print("Did you mean:") # recommend
                    for i in range(len(suggestions)):
                        if cont_print:
                            print(f"{i+1}: {suggestions[i]}")
                            if (i+1) % 5 == 0:
                                while True:
                                    print("--- See more? (y/n) ---")
                                    try:
                                        title_choice = input_nonempty("Choice: ").strip()
                                        title_choice = int(title_choice) # turns string to int
                                        cont_print = False
                                        break
                                    except:
                                        if title_choice != "y":
                                            cont_print = False
                                        break
                        else:
                            break
                                        

                    if title_choice == "n": # this prints "None" ^^^
                        continue
                    try:
                        chosen_title = title_lookup[suggestions[title_choice-1]] # assign title
                    except:
                        continue
                else: 
                    print("Title not found.")
                    continue
                    
        t=""
        prev_rating = profile["read_manga"].get(chosen_title, None)
        if prev_rating is not None:
            print(f"This title exists. Rating: {prev_rating}")
            t = "Update "
        rating = input(f"{t}Rating (0-10): ").strip() # rating
        if rating:
            try:
                profile["read_manga"][chosen_title] = float(rating) # input entry
            except:
                print("Invalid rating.")
        else:
            profile["read_manga"][chosen_title] = None # no rating

def sort_read_manga_list(profile):
    while True:
        print("\nSort by:")
        print("1. Alphabetical (A->Z)")
        print("2. Chronological (Default)")
        print("3. Rating (High->Low)")
        print("4. Return")

        sort_choice = input("Choice: ")
        items = list(profile["read_manga"].items())

        if sort_choice == "1":
            # Alphabetical
            sorted_items = sorted(items)
            break

        elif sort_choice == "2":
            sorted_items = items[:]
            break

        elif sort_choice == "3":
            rating_pairs = []
            for title, rating in items:
                if rating is None:
                    rating_value = 9999
                else:
                    rating_value = rating
                rating_pairs.append((rating_value, title))

            sorted_pairs = sorted(rating_pairs, reverse=True)

            sorted_items = []
            for rating_value, title in sorted_pairs:
                sorted_items.append((title, profile["read_manga"][title]))

            break

        elif sort_choice == "4":
            break

        else:
            print("Invalid choice.")

    if sorted_items is not None:   
        print("\n=== Read Manga ===")
        for i, (title, rating) in enumerate(sorted_items, start=1):
            print(f"{i}:  {title}: {rating}")
