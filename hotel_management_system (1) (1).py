# =============================================================================
# File Name   : hotel_management_system.py
# Author      : Mahi Rakeshbhai Patel (Student ID: 850009097)
# Course      : BBIM502 Introduction to Programming - Assessment 2 (Project)
# Date        : 27/10/2026
# Description : Console-based Hotel Management System for LANGHAM Hotels.
#               It lets hotel staff add and delete rooms, display room details,
#               allocate rooms to customers, display allocations, produce a bill
#               while releasing the room, and save / display / back up the room
#               allocation data using text files. The program is a Python
#               re-build of the earlier C# version and adds input validation
#               and exception handling so it does not crash on bad input.
# =============================================================================

# ----------------------------- Import section --------------------------------
import sys  # always available - needed first so we can exit if another import fails

# ImportError handling: stop with a clear message if a required module is missing
try:
    import os                       # file paths and folder handling
    import ast                      # safe conversion of typed text into numbers
    import math                     # isfinite() check for numbers
    from datetime import datetime   # current date and time for records and file names
except ImportError as error:
    print("A required Python module could not be imported:", error)
    print("Please check your Python installation and run the program again.")
    sys.exit(1)

# ------------------------------- Constants -----------------------------------
STUDENT_ID = "850009097"
DIVIDER = "*" * 83                  # line used to frame the menu and messages
GST_RATE = 0.15                     # New Zealand GST (15%)
MAX_ROOM_NUMBER = 9999
MAX_ROOMS_PER_ENTRY = 50
MAX_NIGHTS = 365
ROOM_TYPES = ["Standard", "Deluxe", "Suite"]


def get_base_folder():
    """Return the folder where the data files will be stored.

    Normally this is the folder that contains this script. When the code is run
    line-by-line in an interactive shell the special name __file__ does not
    exist, so Python raises a NameError and we fall back to the current folder.
    """
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


# File names follow the brief: LHMS_Studentid.txt
BASE_FOLDER = get_base_folder()
DATA_FILE_NAME = "LHMS_" + STUDENT_ID + ".txt"
DATA_FILE_PATH = os.path.join(BASE_FOLDER, DATA_FILE_NAME)

# ------------------------- Data held while the program runs ------------------
rooms = []          # each room: {"room_no", "room_type", "rate", "allocated"}
allocations = []    # each allocation: {"room_no", "room_type", "rate", "customer_no", ...}
bills = []          # bills generated in this session (also written to the file)


# =============================================================================
# Input helper functions (all keyboard input goes through these functions)
# =============================================================================
def read_line(prompt):
    """Show a prompt and return what the user typed with spaces trimmed.

    EOFError handling: if the input stream ends (for example Ctrl+Z / Ctrl+D or
    a closed input pipe) input() raises EOFError. The program then closes safely
    instead of crashing.
    """
    try:
        return input(prompt).strip()
    except EOFError:
        print("\nEnd of input reached - no more data can be read. Closing the application safely.")
        sys.exit(0)


def read_int(prompt, minimum, maximum):
    """Keep asking until the user enters a whole number between minimum and maximum."""
    while True:
        text = read_line(prompt)
        try:
            number = int(text)
        except ValueError:
            # FIXED ERROR 2 (Runtime): the C# code used Convert.ToInt32() with no
            # validation, so text such as "abc" crashed the menu with a FormatException.
            print("Invalid input. Please enter a whole number (for example 101).")
            continue
        if number < minimum or number > maximum:
            print("Please enter a number between " + str(minimum) + " and " + str(maximum) + ".")
            continue
        return number


def convert_to_number(text):
    """Convert typed text into a finite decimal number, or raise an exception.

    ast.literal_eval() safely reads Python number literals from text. It can raise:
      SyntaxError    - text is not valid Python syntax (for example "12abc" or "")
      ValueError     - text is not a literal at all (for example "abc")
      TypeError      - raised here when the value is not a number (for example "[1,2]")
      OverflowError  - a huge whole number cannot be converted to a decimal number
    """
    value = ast.literal_eval(text)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("only numbers are allowed")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("number is not finite")
    return value


def read_amount(prompt, minimum, maximum):
    """Keep asking until the user enters a money amount between minimum and maximum."""
    while True:
        text = read_line(prompt)
        try:
            amount = convert_to_number(text)
        except SyntaxError:
            print("Invalid format. A valid amount looks like 150 or 199.50")
        except ValueError:
            print("That is not a valid number. Please use digits only (for example 150).")
        except TypeError:
            print("Wrong data type. Please enter a number, not text or a list.")
        except OverflowError:
            print("That number is too large to be processed. Please enter a smaller amount.")
        else:
            if minimum <= amount <= maximum:
                return round(amount, 2)
            print("Please enter an amount between " + str(minimum) + " and " + str(maximum) + ".")


def read_customer_name():
    """Keep asking until the user enters a sensible customer name."""
    while True:
        # split() and join() remove extra spaces between words
        name = " ".join(read_line("Please enter Customer Name: ").split())
        letters_only = name.replace(" ", "").replace("-", "").replace("'", "")
        # FIXED ERROR 9 (Logical): the C# code accepted empty customer names.
        if len(name) >= 2 and len(name) <= 40 and letters_only.isalpha():
            return name
        print("Invalid name. Use 2-40 letters, spaces, hyphens or apostrophes only.")


def choose_room_type():
    """Show the room types and return the one the user picks."""
    print("Room types:")
    for position, type_name in enumerate(ROOM_TYPES, start=1):
        print("  " + str(position) + ". " + type_name)
    while True:
        choice = read_int("Select room type number (1-" + str(len(ROOM_TYPES)) + "): ", 1, 999)
        try:
            return ROOM_TYPES[choice - 1]
        except IndexError:
            # IndexError handling: the number is larger than the list of room types
            print("There is no room type " + str(choice) + ". Choose 1 to "
                  + str(len(ROOM_TYPES)) + ".")


# =============================================================================
# Search helper functions
# =============================================================================
def get_room_number(room):
    """Return the room number of a room record (used to sort the room list)."""
    return room["room_no"]


def find_room(room_number):
    """Return the room record with this room number, or None if it does not exist."""
    for room in rooms:
        if room["room_no"] == room_number:
            return room
    return None


def find_allocation(room_number):
    """Return the allocation record for this room number, or None if not allocated."""
    for allocation in allocations:
        if allocation["room_no"] == room_number:
            return allocation
    return None


# =============================================================================
# Menu option 1 - Add Rooms
# =============================================================================
def add_rooms():
    """Add one or more new rooms to the list of rooms."""
    print("You have selected 'ADD ROOMS' from menu")
    print(DIVIDER)
    count = read_int("How many rooms would you like to add (1-" + str(MAX_ROOMS_PER_ENTRY) + ")? ",
                     1, MAX_ROOMS_PER_ENTRY)
    for number in range(1, count + 1):
        print("\nRoom " + str(number) + " of " + str(count))
        # FIXED ERROR 4 (Logical): the C# duplicate check only compared against part of
        # the list and allowed zero/negative numbers. find_room() checks every room.
        while True:
            room_number = read_int("Please enter room number (1-" + str(MAX_ROOM_NUMBER) + "): ",
                                   1, MAX_ROOM_NUMBER)
            if find_room(room_number) is None:
                break
            print("Same room number already exists. Please enter a new room number.")
        room_type = choose_room_type()
        rate = read_amount("Enter the nightly rate in NZD (50 - 5000): ", 50, 5000)
        # FIXED ERROR 3 (Logical): the C# code created a brand-new array on every call,
        # erasing rooms added earlier. append() keeps the existing rooms.
        rooms.append({"room_no": room_number, "room_type": room_type,
                      "rate": rate, "allocated": False})
        rooms.sort(key=get_room_number)
        print("Room " + str(room_number) + " (" + room_type + ") added at $"
              + format(rate, ".2f") + " per night.")
    print("\nHotel now has " + str(len(rooms)) + " room(s) in total")


# =============================================================================
# Menu option 2 - Delete Rooms
# =============================================================================
def delete_rooms():
    """Delete one or more rooms from the list (rooms in use cannot be deleted)."""
    print("You have selected 'DELETE ROOMS' from menu")
    print(DIVIDER)
    if len(rooms) == 0:
        print("No rooms to delete\nPlease add rooms first")
        return
    count = read_int("How many rooms would you like to delete (1-" + str(len(rooms)) + ")? ",
                     1, len(rooms))
    deleted = 0
    while deleted < count:
        print("\nRoom Deletion " + str(deleted + 1) + " of " + str(count))
        room_number = read_int("Please enter Room Number to delete (0 to cancel): ",
                               0, MAX_ROOM_NUMBER)
        if room_number == 0:
            print("Deletion cancelled.")
            break
        room = find_room(room_number)
        if room is None:
            print("Could not find matching room number to delete")
        elif room["allocated"]:
            print("Room " + str(room_number) + " is currently allocated. "
                  + "Use Billing & De-Allocation first.")
        else:
            rooms.remove(room)
            deleted += 1
            print("Room " + str(room_number) + " has been deleted")
    print("\n" + str(deleted) + " room(s) deleted. Rooms remaining: " + str(len(rooms)))


# =============================================================================
# Menu option 3 - Display Room Details
# =============================================================================
def display_rooms():
    """Show the features (type, rate and status) of every room before booking."""
    print("You have selected 'DISPLAY ROOMS DETAILS' from menu")
    print(DIVIDER)
    if len(rooms) == 0:
        print("No rooms to display\nPlease add rooms first")
        return
    print("{:<10}{:<14}{:<20}{:<12}".format("Room No", "Room Type", "Rate/Night (NZD)", "Status"))
    print("-" * 56)
    for room in rooms:
        if room["allocated"]:
            status = "Occupied"
        else:
            status = "Available"
        print("{:<10}{:<14}{:<20}{:<12}".format(room["room_no"], room["room_type"],
                                               "$" + format(room["rate"], ",.2f"), status))
    print("-" * 56)
    print("Total rooms: " + str(len(rooms)))


# =============================================================================
# Menu option 4 - Allocate Rooms
# =============================================================================
def allocate_rooms():
    """Book one or more rooms for customers."""
    print("You have selected 'ALLOCATE ROOMS' from menu")
    print(DIVIDER)
    # FIXED ERROR 5 (Runtime): the C# code used the room array before any rooms were
    # added, which caused a NullReferenceException. We check the list first.
    if len(rooms) == 0:
        print("No rooms available\nPlease add rooms first")
        return
    available_rooms = [room for room in rooms if not room["allocated"]]
    if len(available_rooms) == 0:
        print("All rooms are currently occupied")
        return
    # FIXED ERROR 6 (Logical): the C# code only checked the count against the total
    # number of rooms and accepted 0 or negative numbers. We limit it to free rooms.
    count = read_int("How many rooms would you like to allocate (1-"
                     + str(len(available_rooms)) + ")? ",
                     1, len(available_rooms))
    done = 0
    # FIXED ERROR 10 (Logical): the C# code changed the for-loop counter (i -= 1) to
    # retry. A while loop with a counter is clearer and cannot skip a booking.
    while done < count:
        print(DIVIDER)
        print("Room Allocation " + str(done + 1) + " of " + str(count) + ":")
        room_number = read_int("Please enter Room Number to allocate (0 to cancel): ",
                               0, MAX_ROOM_NUMBER)
        if room_number == 0:
            print("Allocation cancelled.")
            break
        room = find_room(room_number)
        if room is None:
            print("Could not find matching room number to allocate\n"
                  + "Please enter correct room number or add room first")
            continue
        if room["allocated"]:
            print("Room " + str(room_number) + " is already occupied\n"
                  + "Please enter another room to allocate")
            continue
        print("Found matching room number to allocate")
        print("Room " + str(room_number) + " (" + room["room_type"] + ") is empty")
        customer_number = read_int("Please enter Customer Number (1-999999): ", 1, 999999)
        customer_name = read_customer_name()
        nights = read_int("Please enter number of nights (1-" + str(MAX_NIGHTS) + "): ",
                          1, MAX_NIGHTS)
        room["allocated"] = True
        allocations.append({"room_no": room_number, "room_type": room["room_type"],
                            "rate": room["rate"], "customer_no": customer_number,
                            "customer_name": customer_name, "nights": nights,
                            "check_in": datetime.now().strftime("%d/%m/%Y")})
        print("Allocation has been done")
        done += 1


# =============================================================================
# Menu option 5 - Display Room Allocation Details
# =============================================================================
def display_room_allocations():
    """Show every room that is currently allocated and who it is allocated to."""
    print("You have selected 'DISPLAY ROOM ALLOCATION DETAILS' from menu")
    if len(allocations) == 0:
        print("No allocated rooms to display\nPlease allocate rooms first")
        return
    for allocation in allocations:
        print(DIVIDER)
        print("Room Number     : " + str(allocation["room_no"]))
        print("Room Type       : " + allocation["room_type"])
        print("Customer Number : " + str(allocation["customer_no"]))
        print("Customer Name   : " + allocation["customer_name"])
        print("Nights Booked   : " + str(allocation["nights"]))
        print("Check-in Date   : " + allocation["check_in"])
    print(DIVIDER)
    print("Total allocated rooms: " + str(len(allocations)))


# =============================================================================
# Menu option 6 - Billing & De-Allocation
# =============================================================================
def calculate_bill(rate, nights):
    """Return (subtotal, gst, total) for a stay, or None if it cannot be calculated.

    OverflowError  - the number of nights is too large to be multiplied
    TypeError      - the rate or nights is missing or is not a number
    """
    try:
        # FIXED ERROR 12 (Logical): GST and total were rounded separately, so the
        # printed subtotal + GST could differ from the total by one cent. Each
        # amount is now rounded once and the total is built from the rounded parts.
        subtotal = round(rate * nights, 2)
        gst = round(subtotal * GST_RATE, 2)
        total = round(subtotal + gst, 2)
        return subtotal, gst, total
    except OverflowError:
        print("The bill is too large to calculate.")
        return None
    except TypeError:
        print("The room rate or number of nights has the wrong data type.")
        return None


def calculate_average_per_night(total, nights):
    """Return the average cost per night, or 0.0 if the number of nights is zero."""
    try:
        return total / nights
    except ZeroDivisionError:
        print("Cannot calculate the average cost because the number of nights is zero.")
        return 0.0


def billing_and_deallocation():
    """Print the bill for a room and release the room for the next booking."""
    print("You have selected 'BILLING & DE-ALLOCATION' from menu")
    print(DIVIDER)
    # FIXED ERROR 8 (Logical): Billing was only a message "under construction" in the
    # C# program and De-Allocation was a separate option. Both are now one feature.
    if len(allocations) == 0:
        print("No allocated rooms to bill\nPlease allocate rooms first")
        return
    while True:
        room_number = read_int("Please enter Room Number to bill and de-allocate (0 to cancel): ",
                               0, MAX_ROOM_NUMBER)
        if room_number == 0:
            print("Billing cancelled.")
            return
        allocation = find_allocation(room_number)
        if allocation is not None:
            break
        print("Room " + str(room_number) + " has no active allocation\n"
              + "Please enter an allocated room number")

    result = calculate_bill(allocation["rate"], allocation["nights"])
    if result is None:
        print("The bill could not be generated. The room stays allocated.")
        return
    subtotal, gst, total = result
    average = calculate_average_per_night(total, allocation["nights"])
    bill_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    print(DIVIDER)
    print("                         LANGHAM HOTELS - CUSTOMER BILL")
    print(DIVIDER)
    print("Bill Date            : " + bill_date)
    print("Customer             : " + allocation["customer_name"]
          + " (No. " + str(allocation["customer_no"]) + ")")
    print("Room                 : " + str(allocation["room_no"])
          + " (" + allocation["room_type"] + ")")
    print("Check-in Date        : " + allocation["check_in"])
    print("Nights               : " + str(allocation["nights"]))
    print("Rate per Night       : $" + format(allocation["rate"], ",.2f"))
    print("Subtotal (excl. GST) : $" + format(subtotal, ",.2f"))
    print("GST (15%)            : $" + format(gst, ",.2f"))
    print("TOTAL (incl. GST)    : $" + format(total, ",.2f"))
    print("Average per Night    : $" + format(average, ",.2f"))
    print(DIVIDER)

    # De-allocate: free the room and remove the allocation record
    room = find_room(room_number)
    if room is not None:
        room["allocated"] = False
    allocations.remove(allocation)
    bills.append({"room_no": room_number, "customer_name": allocation["customer_name"],
                  "nights": allocation["nights"], "total": total, "bill_date": bill_date})
    print("Room " + str(room_number) + " has been de-allocated and is now available "
          + "for the next booking.")


# =============================================================================
# Menu options 7, 8, 9 - File operations
# =============================================================================
def build_file_lines():
    """Return the text lines (list of strings) that are saved to the data file."""
    lines = []
    lines.append(DIVIDER)
    lines.append("LANGHAM HOTEL MANAGEMENT SYSTEM - ROOM ALLOCATION DATA")
    lines.append("Saved on: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    lines.append(DIVIDER)
    lines.append("ACTIVE ROOM ALLOCATIONS: " + str(len(allocations)))
    for allocation in allocations:
        lines.append(DIVIDER)
        lines.append("Room Number     : " + str(allocation["room_no"]))
        lines.append("Room Type       : " + allocation["room_type"])
        lines.append("Customer Number : " + str(allocation["customer_no"]))
        lines.append("Customer Name   : " + allocation["customer_name"])
        lines.append("Nights Booked   : " + str(allocation["nights"]))
        lines.append("Check-in Date   : " + allocation["check_in"])
    lines.append(DIVIDER)
    lines.append("BILLS GENERATED THIS SESSION: " + str(len(bills)))
    for bill in bills:
        lines.append("Room " + str(bill["room_no"]) + " | " + bill["customer_name"] + " | "
                     + str(bill["nights"]) + " night(s) | Total $" + format(bill["total"], ",.2f")
                     + " | " + bill["bill_date"])
    lines.append(DIVIDER)
    return lines


def save_room_allocations():
    """Menu option 7: create the data file if needed, store the data, close the file."""
    print("You have selected 'SAVE ROOM ALLOCATION TO A FILE' from menu")
    print(DIVIDER)
    file = None
    try:
        # FIXED ERROR 7 (Logical): the C# code used FileMode.OpenOrCreate, which does not
        # clear the file, so old text was left behind when the new data was shorter.
        # Mode "w" creates the file if it does not exist and replaces old content.
        file = open(DATA_FILE_PATH, "w", encoding="utf-8")
        for line in build_file_lines():
            file.write(line + "\n")
        print("Room allocation data saved to '" + DATA_FILE_NAME + "'")
    except FileNotFoundError:
        print("The folder for the file could not be found, so the data was not saved.")
    except IOError as error:
        print("The file could not be written: " + str(error))
    finally:
        if file is not None:
            file.close()
            print("File closed.")


def show_room_allocations_from_file():
    """Menu option 8: read the data file, display it on screen, close the file."""
    print("You have selected 'DISPLAY ROOM ALLOCATION FROM THE FILE' from menu")
    print(DIVIDER)
    file = None
    try:
        file = open(DATA_FILE_PATH, "r", encoding="utf-8")
        lines = file.readlines()
        if len(lines) == 0:
            print("The file '" + DATA_FILE_NAME + "' is empty. Use option 7 to save data first.")
        else:
            for line in lines:
                print(line.rstrip("\n"))
    except FileNotFoundError:
        # FIXED ERROR 11 (Runtime): a missing file must give a helpful message, not a crash.
        print("The file '" + DATA_FILE_NAME + "' was not found.")
        print("Please use option 7 (Save Room Allocation to a File) first.")
    except IOError as error:
        print("The file could not be read: " + str(error))
    finally:
        if file is not None:
            file.close()
            print("File closed.")


def backup_and_clear_file():
    """Menu option 9: append the data file to a time-stamped backup file, then clear it."""
    print("You have selected 'BACKUP AND CLEAR ROOM ALLOCATION FILE' from menu")
    print(DIVIDER)
    stamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    backup_name = "LHMS_" + STUDENT_ID + "_Backup_" + stamp + ".txt"
    backup_path = os.path.join(BASE_FOLDER, backup_name)
    source_file = None
    backup_file = None
    try:
        # Step 1: read the content of the main data file
        source_file = open(DATA_FILE_PATH, "r", encoding="utf-8")
        content = source_file.read()
        source_file.close()
        if content.strip() == "":
            print("The file '" + DATA_FILE_NAME + "' is empty, so there is nothing to back up.")
            return
        # Step 2: append the content to the backup file (created if it does not exist)
        backup_file = open(backup_path, "a", encoding="utf-8")
        backup_file.write(content)
        backup_file.close()
        # Step 3: delete the content of the main file by re-opening it in write mode
        source_file = open(DATA_FILE_PATH, "w", encoding="utf-8")
        source_file.close()
        print("Backup saved as '" + backup_name + "'")
        print("The content of '" + DATA_FILE_NAME + "' has been cleared.")
    except FileNotFoundError:
        # FIXED ERROR 11 (Runtime): the C# code crashed when the file did not exist.
        print("The file '" + DATA_FILE_NAME + "' was not found, so it cannot be backed up.")
        print("Please use option 7 (Save Room Allocation to a File) first.")
    except IOError as error:
        print("The backup could not be completed: " + str(error))
    finally:
        # Make sure both files are closed whatever happened above
        for handle in (source_file, backup_file):
            if handle is not None and not handle.closed:
                handle.close()
        print("Files closed.")


# =============================================================================
# Menu option 0 - Exit Application
# =============================================================================
def exit_application():
    """Display a goodbye message and close the application."""
    print("You have selected 'EXIT'")
    print("Thank you for using the LANGHAM Hotel Management System. Goodbye!")
    sys.exit(0)


# =============================================================================
# Main menu
# =============================================================================
def show_menu():
    """Display the application menu."""
    print(DIVIDER)
    print("                      LANGHAM HOTEL MANAGEMENT SYSTEM")
    print("                                 MENU")
    print(DIVIDER)
    print("1. Add Rooms")
    print("2. Delete Rooms")
    print("3. Display Room Details")
    print("4. Allocate Rooms")
    print("5. Display Room Allocation Details")
    print("6. Billing & De-Allocation")
    print("7. Save Room Allocation to a File")
    print("8. Display Room Allocation from the File")
    print("9. Backup and Clear Room Allocation File")
    print("0. Exit")
    print(DIVIDER)


# Dictionary that links each menu number to the function that does the work
MENU_ACTIONS = {
    0: exit_application,
    1: add_rooms,
    2: delete_rooms,
    3: display_rooms,
    4: allocate_rooms,
    5: display_room_allocations,
    6: billing_and_deallocation,
    7: save_room_allocations,
    8: show_room_allocations_from_file,
    9: backup_and_clear_file,
}


def main():
    """Run the menu until the user chooses Exit (option 0)."""
    # FIXED ERROR 1 (Logical): the C# Menu() method called itself again from a
    # finally block, so menus stacked up and could cause a stack overflow.
    # One while loop now repeats the menu safely.
    while True:
        show_menu()
        choice = read_int("Enter Your Choice Number Here (0-9): ", 0, 9)
        try:
            MENU_ACTIONS[choice]()
        except KeyboardInterrupt:
            print("\nOperation interrupted. Returning to the menu.")
        except Exception as error:
            # Last safety net so an unexpected problem never closes the whole program
            print("An unexpected error occurred: " + str(error))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication closed by the user (Ctrl+C).")
