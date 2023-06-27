# import


class CustomTkError(Exception):
    "An error class to be raised when something goes wrong with a tkinter dialog that isn't covered by other errors."


class NoSavedSelectionsError(CustomTkError):
    "Raised when the user tries to restore selections but none are stored for the given dialog."

    def __str__(self):
        return "No dialog selections have been saved for this dialog."
    

class IncompatibleSelectionRestoreError(CustomTkError):
    "Raised when selections cannot be restored because the saved file is incompatible with the current dialog."

    def __str__(self):
        return "Uh-oh! The saved dialog selections are incompatible with the current dialog. Did Ben forget to give it a unique name?"