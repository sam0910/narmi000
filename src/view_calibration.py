import os


def cat_file(filename):
    try:
        with open(filename, "r") as file:
            for line in file:
                print(line, end="")
    except Exception as e:
        print(f"Error reading file: {e}")


# Example usage
cat_file("calibration.py")
