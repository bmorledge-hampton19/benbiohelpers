# This script frees up storage space by recursively deleting the contents of any ".tmp" directories under a given directory.
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
import os

def cleanDataDirectory(directory):

    itemsRemoved = 0

    # Iterate through the given directory
    for item in os.listdir(directory):
        path = os.path.join(directory,item)

        # When a .tmp directory is encountered, delete all the files within.
        if os.path.isdir(path) and item == ".tmp":
            for itemToDelete in os.listdir(path):
                pathToDelete = os.path.join(path,itemToDelete)
                if os.path.isdir(pathToDelete): os.rmdir(pathToDelete)
                else: os.remove(pathToDelete)
                itemsRemoved += 1

        # Recursively search any directories that are not .tmp directories
        elif os.path.isdir(path):
            itemsRemoved += cleanDataDirectory(path)

    return itemsRemoved



def main():
    
    with TkinterDialog(workingDirectory = os.getenv("HOME"), title = "Clean .tmp Directories") as dialog:
        dialog.createFileSelector("Root directory to clean .tmp directories from:", 0, directory = True)
        dialog.createLabel("**CAUTION: This function is recursive!**", 1, 0,
                           sticky = False, columnSpan = 2)
        dialog.createLabel("DO NOT select a directory above any .tmp directories you want to preserve.", 2, 0,
                           columnSpan = 2, sticky = False)

    print(f"Cleaning {dialog.selections.getIndividualFilePaths()[0]}...")
    itemsRemoved = cleanDataDirectory(dialog.selections.getIndividualFilePaths()[0])
    print(f"Deleted {itemsRemoved} items within intermediate directories.")

if __name__ == "__main__": main()