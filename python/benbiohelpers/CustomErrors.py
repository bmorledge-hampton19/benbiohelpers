import os


class UserInputError(Exception):
    """
    An error class to be raised when invalid input is given at any point in the pipeline,
    whether from improperly formatted files or from invalid UI selections.
    """


class UnsortedInputError(UserInputError):
    """
    An error class for when input should be sorted but isn't.  (Especially in the "ThisInThatCounter")
    """

    def __init__(self, path: str, expectedSorting = None):
        self.path = path
        self.expectedSorting = expectedSorting

    def __str__(self):
        errorAsString = "The contents of the file at " + self.path + " are improperly sorted."
        if self.expectedSorting is not None:
            errorAsString += "\n" + self.expectedSorting
        return errorAsString


class InvalidPathError(UserInputError):
    """
    An error class for when a given path does not exist, does not conform to expected standards, etc.,
    seemingly from user error.
    """

    def __init__(self, path: str, message = None, postPathMessage = None):
        self.path = path
        self.message = message
        self.postPathMessage = postPathMessage
        self.setDefaultMessage()

    
    def setDefaultMessage(self):
        self.defaultMessage = "Invalid path: "


    def __str__(self):
        if self.message is None: errorAsString = self.defaultMessage + '\"' + self.path + '\"'
        else: errorAsString = self.message + '\n' + self.path

        if self.postPathMessage is not None: errorAsString += '\n' + self.postPathMessage

        return errorAsString


class MetadataError(Exception):
    """
    A parent error class for metadata-associated errors.
    """


class MetadataPathError(InvalidPathError, MetadataError):
    """
    An error class for when metadata isn't found at the expected path, probably because the user moved things around or 
    deleted things they shouldn't.  (Or because my code is buggy, which is always a possibility...)
    """


class MetadataAutoGenerationError(UserInputError, MetadataError):
    """
    An error class for when metadata cannot be unambiguously generated from a given string (usually a filename).
    """


class NonexistantPathError(InvalidPathError):
    """
    An error class for when a path given by user input does not exist
    """

    def setDefaultMessage(self):
        self.defaultMessage = "Given path does not exist: "


def checkIfPathExists(path):
    """
    Simple function to check if a path exists and raise a NonexistantPathError if it doesn't
    """

    if os.path.exists(path): return True
    else: raise NonexistantPathError(path)