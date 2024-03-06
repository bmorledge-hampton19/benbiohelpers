import os
from abc import ABC, abstractmethod
from benbiohelpers.CustomErrors import checkIfPathExists, UserInputError, InvalidPathError
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs


class DataDir(ABC):
    """
    A class for managing the data directory of a particular pipeline.
    This is accomplished primarily through the class method, getDataDirectory which returns the path to the data directory.
    If the directory does not exist when the getDataDirectory function is called, the user is automatically prompted to create it.
    """

    @staticmethod
    @abstractmethod
    def _getPackageDirectory():
        """
        The first of the three abstract methods defined by the DataDir class.
        This one should return a path to the package directory to be used by the child of the DataDir class. It should also ensure that directory exists.
        This directory will be used to store the text file that will contain the path to the data directory so that its location is static and reliable.
        It will also be used as the default location for the directory selection GUI.

        See DataDirChildTemplate.py for an example implementation.
        """

    @staticmethod
    @abstractmethod
    def _getDataDirectoryPath(dataDirectoryDirectory):
        """
        The second of the three abstract methods defined by the DataDir class.
        This one should return a path to the data directory given its parent directory.

        See DataDirChildTemplate.py for an example implementation.
        """


    @staticmethod
    @abstractmethod
    def _getPackageName():
        """
        The final abstract method defined by the DataDir class.
        This one is easy. Simply return the name of the package, which will be used in the tkinter dialog prompting the user to create the data directory.

        See DataDirChildTemplate.py for an example implementation.
        """


    @classmethod
    def _getDataDirectoryTextFilePath(dataDirChild):
        """
        Returns the path to the data-directory-containing text file.
        """
        return os.path.join(dataDirChild._getPackageDirectory(), "data_dir.txt")


    @staticmethod
    def _createAdditionalDirectories(dataDirectory):
        """
        A method that is meant to be overridden to define other directories to create inside the main data directory whenever it is first created.
        By default, no additional directories are created.
        """
        pass

        
    @classmethod
    def getDataDirectory(dataDirChild, newDataDirectoryDirectory = None):

        # If a new directory was given, make sure it exists.
        if newDataDirectoryDirectory is not None: checkIfPathExists(newDataDirectoryDirectory)

        # Check for the text file which should contain the path to the data directory.
        dataDirectoryTextFilePath = dataDirChild._getDataDirectoryTextFilePath()

        # If it exists, return the directory path within. (Or overwrite it if a new directory path was supplied.)
        if os.path.exists(dataDirectoryTextFilePath):
            
            useExistingDataDirectoryTextFile = True

            if newDataDirectoryDirectory is not None:
                userChoice = ''
                userChoice = input(f"A new location for the data directory has been given: {newDataDirectoryDirectory}\n"
                                "Are you sure you want to update the current data directory location? ")
                while userChoice.upper() not in ('Y', "YES", 'N', "NO"):
                    userChoice = input("Invalid choice. Please answer (y)es or (n)o ")

                if userChoice.upper() == 'Y' or userChoice.upper() == "YES":
                    dataDirectoryDirectory = newDataDirectoryDirectory
                    useExistingDataDirectoryTextFile = False
                else:
                    print("Not updating data directory. Proceeding with current directory.")

            if useExistingDataDirectoryTextFile:
                with open(dataDirectoryTextFilePath, 'r') as dataDirectoryTextFile:
                    
                    dataDirectory = dataDirectoryTextFile.readline().strip()
                    
                    # Double check to make sure the data directory is still intact.  
                    # If it isn't, inform the user, and progress through the function to recreate it.
                    if not os.path.isdir(dataDirectory):
                        print("Data directory not found at expected location: {}".format(dataDirectory))
                        print("Please select a new location to create a data directory.")
                    else: return dataDirectory

        # Create a simple dialog to select a new data directory location.
        # NOTE: The following code is not part of an else statement because the above "if" block will return
        # the data directory if it proceeds correctly, and if it doesn't, the data directory text file
        # needs to be recreated anyway.
        if newDataDirectoryDirectory is not None:
            dataDirectoryDirectory = newDataDirectoryDirectory
        else:
            # Only import tkinter if we absolutely need it, as this class may function purely from a command-line interface on a computer
            # where tkinter is not actually installed.
            from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog, Selections
            from _tkinter import TclError
            try:
                dialog = TkinterDialog(workingDirectory = dataDirChild._getPackageDirectory(), title = "Data Directory Selection")
                dialog.createFileSelector(f"Location to create {dataDirChild._getPackageName()} data directory:",0,("Fasta Files",".fa"), directory = True)

                # Run the UI
                dialog.mainloop()

                # If no input was received (i.e. the UI was terminated prematurely), then quit!
                if dialog.selections is None: quit()

                selections: Selections = dialog.selections
                dataDirectoryDirectory = selections.getIndividualFilePaths()[0]
            except TclError:
                dataDirectoryDirectory = input("Unable to open the GUI to select a data directory. Please supply one here: ")
                while not os.path.exists(dataDirectoryDirectory):
                    dataDirectoryDirectory = input("The given path does not exist. Please give the full path to an existing directory. ")

        # Make sure a valid, writeable directory was given.  Then create the new directory (if it doesn't exist already), 
        # write it to the text file, and return it!  (Also create any additional directories through _createAdditionalDirectories.)
        if not os.path.exists(dataDirectoryDirectory): 
            raise UserInputError("Given directory: " + dataDirectoryDirectory + " does not exist.")

        dataDirectory = dataDirChild._getDataDirectoryPath(dataDirectoryDirectory)
        try:
            checkDirs(dataDirectory)
        except IOError:
            raise InvalidPathError(dataDirectoryDirectory, "Given location for data directory is not writeable:")
        with open(dataDirectoryTextFilePath, 'w') as dataDirectoryTextFile:
            dataDirectoryTextFile.write(dataDirectory + '\n')
        dataDirChild._createAdditionalDirectories(dataDirectory)
        return dataDirectory
