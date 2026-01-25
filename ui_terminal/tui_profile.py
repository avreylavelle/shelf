from utils.input import input_nonempty
from services.library import search_manga

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
            add_manga_rating(profile)
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
        
def add_manga_rating(profile):
    while True:
        chosen_title = ""
        requested_title = input_nonempty("-------------------" \
        "\nTitle (exit to exit): ").strip() # request title
        if requested_title == "exit": # if user says exit, exit
            break

        search = search_manga(requested_title, limit=10)
        title_lookup = search["title_lookup"]
        substring_match = search["substring"]
        suggestions = search["fuzzy"]

        # NEED TO ADD
        # USE SYNONYMS IN THIS SECTION
        # NEED TO ADD

        if search["exact"]:
            chosen_title = search["exact"]
        else:
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
