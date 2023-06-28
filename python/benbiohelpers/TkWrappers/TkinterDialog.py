# A modular dialog window used to select relevant files and options for a script.

import tkinter as tk
import tkinter.font as tkFont
import os
from tkinter import filedialog, messagebox
from typing import List, Dict, Tuple, TextIO
from benbiohelpers.TkWrappers.MultipleFileSelector import MultipleFileSelector
from benbiohelpers.TkWrappers.DynamicSelector import DynamicSelector
from benbiohelpers.CustomErrors import NonexistantPathError
from benbiohelpers.TkWrappers.MyTkErrors import *
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs


class TkinterDialog(tk.Frame):
    """
    A modular dialog window used to select relevant files and options for a script.
    """

    def __init__(self, master=None, workingDirectory = os.path.dirname(os.path.realpath(__file__)), 
                 row = 0, column = 0, pady = 0, columnSpan = 1, title = "tkinter dialog", ID = "Root", 
                 scrollable = False, scrollableWindowMaxHeight = 500):
        
        # Store important variables.
        self.title = title
        self.scrollable = scrollable
        self.workingDirectory = workingDirectory
        self.ID = ID
        self.scrollableWindowMaxHeight = scrollableWindowMaxHeight

        # Initialize the tkinter dialogue based on whether or not it is the root dialogue (master is none).

        if master is None: 

            # If this is the root dialog, some special considerations need to be made to frame it
            # properly in the root window.
            self.isRoot = True
            self.rootWindow = tk.Tk()
            self.rootWindow.columnconfigure(column, weight=1)
            self.rootWindow.rowconfigure(row, weight=1)
            parentFrame = tk.Frame(self.rootWindow)
            parentFrame.columnconfigure(column, weight=1)
            parentFrame.rowconfigure(row, weight=1)
            parentFrame.grid(sticky="news")
            self.root = self
            
            self.rootWindow.report_callback_exception = self.report_callback_exception


            # Fix the window size if the root is scrollable.
            if self.scrollable: self.rootWindow.geometry("1000x"+str(self.scrollableWindowMaxHeight))

            # Set the title and put in a nice visual!
            self.rootWindow.title(title)
            img = tk.PhotoImage(file = os.path.dirname(os.path.realpath(__file__)) + "/test_tube.png")
            self.rootWindow.iconphoto(False, img)

            # Set up the list of queued scroll bars for proper scroll wheel implementation.
            self.scrollableQueue: List[tk.Canvas] = list()

        else: 

            # Otherwise, just set up some basic stuff.
            self.isRoot = False
            parentFrame: TkinterDialog = master
            self.root = parentFrame.root
            self.scrollableQueue = None
            

        # Set up a parent canvas for things like the scroll bar.
        self.parentCanvas = tk.Canvas(parentFrame, borderwidth= 0, width = 0, height = 0, highlightthickness=0)
        self.parentCanvas.grid(row = row, column = column, columnspan = columnSpan, pady = pady, sticky = "news")
        self.parentCanvas.columnconfigure(0, weight = 1)
        self.parentCanvas.rowconfigure(0, weight = 1)

        # If this dialogue is meant to be scrollable, set it up accordingly.
        if self.scrollable: 
            self.mainScrollBar = tk.Scrollbar(parentFrame, orient="vertical", command=self.parentCanvas.yview)
            self.mainScrollBar.grid(row = row, column = column + columnSpan, sticky = "ns")
            self.parentCanvas.configure(yscrollcommand=self.mainScrollBar.set)

        # If this is the root, set up the exit buttons underneath the canvas.
        if self.isRoot:
            exitButtonsFrame = tk.Frame(parentFrame)
            exitButtonsFrame.grid(row = 1, columnspan = 2, pady = 5, sticky = tk.W+tk.E)
            exitButtonsFrame.grid_columnconfigure((0,1,2), weight = 1)

            tk.Button(exitButtonsFrame, text = "Go", command = self.go).grid(row = 0, column = 1)
            tk.Button(exitButtonsFrame, text = "Quit", command = quit).grid(row = 0, column = 2)
            tk.Button(exitButtonsFrame, text = "Restore Selections", command = self.beginRestore).grid(row = 0, column = 0)

        # Initialize the internal frame
        super().__init__(self.parentCanvas)

        # Initialize the grid used to organize UI elements
        self.grid(sticky = "news")

        # Fit the internal frame to the canvas
        self.canvasWindow = self.parentCanvas.create_window((0,0), window=self, anchor=tk.NW)

        # Bind configuration events to handle special resizing of the canvas and (potentially) scrolling.
        self.bind("<Configure>", self.onSelfConfigure)
        if self.scrollable:
           self.parentCanvas.bind("<Enter>", self.onEnterScrollableCanvas)
           self.parentCanvas.bind("<Leave>", self.onLeaveScrollableCanvas)

        # Prepare lists for the selections object.
        self.individualFileEntries: List[Tuple[tk.Entry,bool]] = list() # A list of two-item tuples containing first the file entry objects from individual 
                                            # file selections and also a boolean value telling whether or not they are for new files.
        self.plainTextEntries: List[tk.Entry] = list() # A list of entry objects from createTextField
        self.dropdownVars: List[tk.StringVar] = list() # A list of stringVars associated with dropdowns
        self.checkboxVars: List[tk.BooleanVar] = list() # A list of intVars associated with checkboxes
        self.multipleFileSelectors: List[MultipleFileSelector] = list() # A list of MultipleFileSelectors, which contain a list of filePaths.
        self.dynamicSelectors: List[DynamicSelector] = list() # A list of DynamicSelector objects, which contain TkinterDialog objects of their own.
        self.subDialogs: List[TkinterDialog] = list() # A list of TkinterDialog objects designated "sub-dialogs"
        self.selections: Selections = None # A selections object to be populated at the end of the dialog


    # Functions for "with" compatibility.
    def __enter__(self): return self
    
    def __exit__(self, type, value, tb): 
        self.mainloop()
        if self.selections is None: quit()


    def report_callback_exception(self, exc, val, tb):
        messagebox.showerror("Error", message = str(val))


    ### A series of functions to bind to gui events.
    def onSelfConfigure(self, event: tk.Event):
        "Handle events on the reconfiguration of the main frame"

        # First, resize the canvas as necessary.
        self.parentCanvas.config(width = event.width, height = event.height)
        if self.scrollable and event.height > self.scrollableWindowMaxHeight:
            self.parentCanvas.config(height = self.scrollableWindowMaxHeight)

        # If this is the top level dialog, update the root window too.
        if self.isRoot and not self.scrollable:
            self.rootWindow.update()
            self.rootWindow.geometry("")

        # Now, set the scroll bar.
        if self.scrollable:
            self.update_idletasks()
            self.parentCanvas.config(scrollregion=self.parentCanvas.bbox("all"))

    def onEnterScrollableCanvas(self, event = None):
        "Bind this canvas's scroll bar to the scroll wheel and add it to the queue"

        # If there are no scrollable canvases in the queue, rebind the mousewheel.
        if len(self.root.scrollableQueue) == 0:
            self.bind_all("<Button-4>", lambda event: self.onMouseWheelScroll(-1))
            self.bind_all("<Button-5>", lambda event: self.onMouseWheelScroll(1))

        # Add this scrollable canvas to the queue.
        self.root.scrollableQueue.append(self.parentCanvas)

    def onLeaveScrollableCanvas(self, event):
        "Handle unbinding and potential rebinding of the scroll wheel."

        # Shift to the next scrollable canvas in the queue, if there is one.
        # If there isn't, unbind the scrollwheel.
        self.root.scrollableQueue.pop()
        if len(self.root.scrollableQueue) == 0:
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")

    def onMouseWheelScroll(self, direction):
        self.root.scrollableQueue[-1].yview_scroll(direction, "units")


    def hide(self):
        self.parentCanvas.grid_remove()

    def show(self):
        self.parentCanvas.grid()


    def createWidgets(self):
        "Mainly used as an example.  Probably don't run this function; run the functions it calls."
        
        print ("Creating Widgets...")

        # Create two file selectors and store the entry objects that will hold the filenames.
        self.createFileSelector("First File: ", 0)
        self.createFileSelector("Second File: ", 1)

        #Create two buttons, one to print the selected filenames, and one to quit
        self.createReturnButton(2, 0, 2)
        self.createQuitButton(2,2,2)


    def createSubDialog(self, row, column = 0, selectionsID = None, columnSpan = 1, workingDirectory = None):
        "Creates and returns another TkinterDialog within the parent dialog."

        # Create the dialog object.
        if workingDirectory is None: workingDirectory = self.workingDirectory
        tkinterDialog = TkinterDialog(master = self, title = None, ID = selectionsID, 
                                      row = row, column = column, columnSpan = columnSpan,
                                      workingDirectory = workingDirectory, pady = 15)

        self.subDialogs.append(tkinterDialog)
        return tkinterDialog


    def createLabel(self, text, row, column, columnSpan = 1, sticky = True, header = False):
        "Create a simple text label"
        myFont = tkFont.nametofont("TkDefaultFont").copy()
        
        if header: myFont.config(size = "12", weight = "bold")
        label = tk.Label(self, text = text, font = myFont)
        label.grid(row = row, column = column, columnspan = columnSpan)
        if sticky: label.grid(sticky = tk.W)


    def createFileSelector(self, title: str, row: int, *fileTypes, defaultFile = "No file Selected", column = 0,
                           columnSpan = 2, verbose = False, newFile = False, directory = False):
        """
        Creates a file selector for choosing relevant files from the dialog.
        The whole file selector is contained in a single tk.Frame object and has 3 components:
        The title for the selector occupies the first column.
        The selector itself as a tk.Entry object.
        The final column holds the "browse" button.
        """

        if verbose: print ("Creating file selector: " + title)

        fileSelectorFrame = tk.Frame(self)
        fileSelectorFrame.grid(row = row, column = column, columnspan = columnSpan, sticky = tk.W)

        #Create the title for the selector.
        tk.Label(fileSelectorFrame,text = title).grid(row = 0, column = 0)

        #Create the selector itself as a tk.entry object.
        textField = tk.Entry(fileSelectorFrame, width = 40)
        textField.grid(row = 0, column = 1, columnspan = 2, pady = 10, padx = 5)
        textField.insert(0, defaultFile)
        textField.xview(len(defaultFile))

        #Create the "browse" button.
        tk.Button(fileSelectorFrame, text = "Browse", command = lambda: self.browseForFile(textField,title,newFile,directory,*fileTypes)).grid(row = 0, column = 3)

        self.individualFileEntries.append((textField,newFile))


    def createMultipleFileSelector(self, title: str, row: int, fileEnding, *fileTypes, columnSpan = 2,
                                   additionalFileEndings = list(), basenameContains = list()):
        "Create a file selector which can dynamically add and remove multiple file paths to a given group."

        # Create an instance of the the MultipleFileSelector class, and place it in the dialog at the given row.
        multipleFileSelector = MultipleFileSelector(self, title, self.workingDirectory, 
                                                    fileEnding, additionalFileEndings, *fileTypes, basenameContains = basenameContains)
        multipleFileSelector.grid(row = row, columnspan = columnSpan, sticky = tk.W, pady = 10)

        # Keep track of the file selector so we can access the file paths it contains later.
        self.multipleFileSelectors.append(multipleFileSelector)


    def createDropdown(self, labelText, row, column, options, columnSpan = 1):
        "Create a dropdown menu to select something from a list of options."
        
        # Initialize the stringVar to be modified by the dropdown.
        dropdownStringVar = tk.StringVar()
        dropdownStringVar.set(options[0])
        self.dropdownVars.append(dropdownStringVar)

        # Create a tk.Frame to encompass the dropdown.
        dropdownFrame = tk.Frame(self)
        dropdownFrame.grid(row = row, column = column, columnspan = columnSpan, sticky = tk.W)

        # Add the label
        tk.Label(dropdownFrame, text = labelText).grid(row = 0, column = 0)

        # Initialize the dropdown.
        dropdown = tk.OptionMenu(dropdownFrame, dropdownStringVar,*options)
        dropdown.grid(row = 0, column = 1, pady = 5, padx = 5)

    
    def createCheckbox(self, text, row, column, columnSpan = 1):
        "Create a checkbox that holds a bool input from the user."
        
        # Initialize the intVar to be modified by the checkbox
        checkboxBooleanVar = tk.BooleanVar()
        self.checkboxVars.append(checkboxBooleanVar)

        # Create the checkbox
        tk.Checkbutton(self, text = text, variable = checkboxBooleanVar).grid(row = row, column = column, columnspan = columnSpan, pady = 3, sticky = tk.W)


    def createButton(self, text, row, column, command, columnSpan = 1):
        "Create a button to execute a given function."
        tk.Button(self, text=text, command=command).grid(row = row, column = column, columnspan = columnSpan)


    def createQuitButton(self, row, column, columnSpan = 1):
        """
        DEPRECATED.  Buttons are created in constructor now.
        Create a button that exits the python script.
        """
        self.createButton("Quit",row,column,quit, columnSpan=columnSpan)


    def createReturnButton(self, row, column, columnSpan = 1):
        """
        DEPRECATED.  Buttons are created in constructor now.
        Create a button that returns the user input to the selections object
        """
        self.createButton("Go",row,column,self.generateSelections, columnSpan=columnSpan)


    def createExitButtons(self, row, column, columnSpan = 2):
        """
        DEPRECATED.  Buttons are created in constructor now.
        Creates the quit and return buttons in a single tk.Frame that centers them within that frame.
        """
        buttonFrame = tk.Frame(self)
        buttonFrame.grid(row = row, column = column, columnspan = columnSpan, sticky = tk.W+tk.E)
        buttonFrame.grid_columnconfigure((0,1), weight = 1)

        tk.Button(buttonFrame, text = "Go", command = self.generateSelections).grid(row = 0, column = 0)
        tk.Button(buttonFrame, text = "Quit", command = quit).grid(row = 0, column = 1)


    def createTextField(self, labelText, row, column, columnSpan = 2, defaultText = "Type here", width = 20):
        "Creates an editable text field."

        # Create an instance of the the text field, and place it in the dialog at the given row.
        textField = tk.Frame(master = self)
        textField.grid()
        textField.grid(row = row, column = column, columnspan = columnSpan, pady = 10, sticky = tk.W)

        # Create the label and text box in the text field object.
        tk.Label(textField, text = labelText).grid(row = 0, column = 0, sticky = tk.W)
        textBox = tk.Entry(textField, width = width)
        textBox.grid(row = 1, columnspan = 2, pady = 2, padx = 5, sticky = tk.W)
        textBox.insert(0, defaultText)

        self.plainTextEntries.append(textBox)


    def createNucMutGroupSubDialog(self, groupID, row, column = 0, columnSpan = 1):
        "Creates a sub-dialog for selecting nucleosome mutation files of specific characteristics"

        group = self.createSubDialog(row = row, column = column, columnSpan = columnSpan, selectionsID = groupID)
        group.columnconfigure(0, minsize = 200)
        group.columnconfigure(1, minsize = 200)
        row = 0
        group.createLabel(groupID, row, 0, 3, header = True)
        row += 1

        group.createLabel("Normalization Method:", row, 0, 3)
        row += 1
        group.createCheckbox("Singlenuc/Dinuc", row, 0, )
        group.createCheckbox("Trinuc/Quadrunuc", row, 1)
        group.createCheckbox("Pentanuc/Hexanuc", row, 2)
        row += 1
        group.createCheckbox("Custom", row, 0)
        group.createCheckbox("Raw", row, 1)
        row += 1
        group.createLabel("",row,0)
        row += 1

        group.createLabel("Nucleosome Radius:", row, 0, 3)
        row += 1
        group.createCheckbox("Single Nucleosome", row, 0, 2)
        group.createCheckbox("Nucleosome Group", row, 2)
        row += 1
        group.createLabel("",row,0)
        row += 1

        group.createLabel("Cohort Designations:", row, 0, 3)
        row += 1
        MSDynamicSelector = group.createDynamicSelector(row, 0, 4)
        MSDynamicSelector.initCheckboxController("Stratify by microsatellite status")
        group.checkboxVars.append(MSDynamicSelector.controllerVar)
        MSDynamicSelector.initDisplay(True, groupID + "MS").createDropdown("Microsatellite Status:", 0, 0, ("Any", "MSS", "MSI"))
        MSDynamicSelector.initDisplayState()
        row += 1
        mutSigDynamicSelector = group.createDynamicSelector(row, 0, 4)
        mutSigDynamicSelector.initCheckboxController("Startify by mutation signature")
        group.checkboxVars.append(mutSigDynamicSelector.controllerVar)
        mutSigDynamicSelector.initDisplay(True, groupID + "MutSig").createFileSelector("Signatures File:", 0, ("Text File", ".txt"))
        mutSigDynamicSelector.initDisplayState()
        row += 1
        customDynamicSelector = group.createDynamicSelector(row, 0, 4)
        customDynamicSelector.initCheckboxController("Designate Custom Cohorts")
        group.checkboxVars.append(customDynamicSelector.controllerVar)
        customDynamicSelector.initDisplay(True, groupID + "CustomCohorts").createFileSelector("Custom Cohort Designations:", 0, ("Text File",".txt"))
        customDynamicSelector.initDisplayState()
        row += 1

        nucleosomeMapSelector = group.createDynamicSelector(row, 0, 4)
        nucleosomeMapSelector.initCheckboxController("Stratify by nucleosome map")
        group.checkboxVars.append(nucleosomeMapSelector.controllerVar)
        nucleosomeMapSelector.initDisplay(True, groupID + "NucleosomeMaps").createFileSelector("Nucleosome Map Designations:", 0, ("Text File",".txt"))
        nucleosomeMapSelector.initDisplayState()
        row += 1

        group.createLabel("",row,0)


    def createDynamicSelector(self, row, column, columnSpan = 1, workingDirectory = None):
        "Creates a dynamic selector object at the given location and returns it so it can be further modified."

        if workingDirectory is None: workingDirectory = self.workingDirectory
        dynamicSelector = DynamicSelector(self, workingDirectory)
        dynamicSelector.grid(row = row, column = column, columnspan = columnSpan, sticky = "w")
        self.dynamicSelectors.append(dynamicSelector)
        return dynamicSelector


    def browseForFile(self,textField: tk.Entry, title, newFile, directory, *fileTypes):
        "Opens a UI for selecting a file starting from the working directory."

        fileTypes = fileTypes + (("Any File Type", ".*"),)
        
        if directory:

            filename = filedialog.askdirectory(initialdir = self.workingDirectory, title = title)

        else:
            if not newFile:
                filename = filedialog.askopenfilename(filetypes = fileTypes,
                    initialdir = self.workingDirectory, title = title)
            else:
                filename = filedialog.asksaveasfilename(filetypes = fileTypes,
                    initialdir = self.workingDirectory, title = title)

        if (filename != ""):
            textField.delete(0, tk.END)
            textField.insert(0, filename)
            textField.xview(len(filename))
    

    def go(self):
        "This function is invoked when the \"Go\" button is pressed."

        self.generateSelections()

        # Open the file to save selections to.
        selectionStorageFilePath = os.path.join(os.getenv("HOME"), ".benbiohelpers", "tkinter_selection_storage",
                                                self.root.title+".txt")
        checkDirs(os.path.dirname(selectionStorageFilePath))
        with open(selectionStorageFilePath, 'w') as selectionStorageFile: self.saveSelections(selectionStorageFile)

        self.rootWindow.destroy()


    def beginRestore(self):
        "This function is invoked when the \"Restore Selections\" button is pressed."

        selectionStorageFilePath = os.path.join(os.getenv("HOME"), ".benbiohelpers", "tkinter_selection_storage",
                                                self.root.title+".txt")
        if not os.path.exists(selectionStorageFilePath): raise NoSavedSelectionsError
        with open(selectionStorageFilePath, 'r') as selectionStorageFile:
            try: self.restoreSelections(selectionStorageFile)
            except: raise IncompatibleSelectionRestoreError


    def generateSelections(self):
        "Populates the selections object with the user's input and then destroys the widget."

        individualFilePaths = list() # A list of the filenames selected with the dialog
        filePathGroups = list() # A list of the groups of filepaths selected through MultipleFileSelectors.
        textEntries = list()
        toggleStates = list() # A list of the states of the toggles in the dialog
        dropdownSelections = list() # A list of the selections from dropdown menus

        # Get all the different Selections-relevant variables from this dialog object
        if self.ID is not None:
            for individualFileEntry in self.individualFileEntries:
                individualFilePaths.append(individualFileEntry[0].get())
                # Also check to make sure the file path exists if it's not a new file path.
                if not individualFileEntry[1] and not os.path.exists(individualFilePaths[-1]):
                    #self.root.rootWindow.destroy()
                    raise NonexistantPathError(individualFilePaths[-1])

            for multipleFileSelector in self.multipleFileSelectors:
                filePathGroups.append(multipleFileSelector.getFilePaths())

            for plainTextEntry in self.plainTextEntries:
                textEntries.append(plainTextEntry.get())

            for checkboxVar in self.checkboxVars:
                toggleStates.append(checkboxVar.get())

            for stringVar in self.dropdownVars:
                dropdownSelections.append(stringVar.get())

            # Generate the Selections object from the above variables.
            self.selections = Selections(self.ID,individualFilePaths,filePathGroups, 
                                         textEntries, toggleStates,dropdownSelections)
        
        # Generate a blank selections object if the ID is NoneType,
        else: self.selections = Selections(None)

        # Add any Selections objects from any dialogs included in dynamic displays
        for dynamicSelector in self.dynamicSelectors:
            dynamicSelector.getCurrentDisplay().generateSelections()
            self.selections.addSelections(dynamicSelector.getCurrentDisplay().selections)      

        # Add any Selections objects from sub-dialogs
        for subDialog in self.subDialogs:
            subDialog.generateSelections()
            self.selections.addSelections(subDialog.selections)


    def saveSelections(self, selectionStorageFile: TextIO, nestingLevel = 0):
        "Stores the current selections in a text file so that they can be quickly restored."

        # Get all the different Selections-relevant variables from this dialog object
        for individualFileEntry in self.individualFileEntries:
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write(f"Individual_File_Path:{individualFileEntry[0].get()}\n")

        for multipleFileSelector in self.multipleFileSelectors:
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write(f"File_Path_Group:{':'.join(multipleFileSelector.getPaths())}\n")

        for plainTextEntry in self.plainTextEntries:
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write(f"Plain_Text_Entry:{plainTextEntry.get()}\n")

        for checkboxVar in self.checkboxVars:
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write(f"Toggle_State:{checkboxVar.get()}\n")

        for stringVar in self.dropdownVars:
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write(f"Dropdown_Selection:{stringVar.get()}\n")

        # Store selections from active dialogs in dynamic displays
        for i, dynamicSelector in enumerate(self.dynamicSelectors):
            selectionStorageFile.write('\t'*nestingLevel)
            if isinstance(dynamicSelector.controllerVar, tk.StringVar):
                selectionStorageFile.write(f"Start_Dynamic_StringVar_Selector:{dynamicSelector.getControllerVar()}\n")
            elif isinstance(dynamicSelector.controllerVar, tk.BooleanVar):
                selectionStorageFile.write(f"Start_Dynamic_BooleanVar_Selector:{dynamicSelector.getControllerVar()}\n")
            dynamicSelector.getCurrentDisplay().saveSelections(selectionStorageFile, nestingLevel + 1)
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write("End_Dynamic_Selector\n")

        # Store selections from sub-dialogs
        for subDialog in self.subDialogs:
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write("Start_Sub_Dialog\n")
            subDialog.saveSelections(selectionStorageFile, nestingLevel = nestingLevel + 1)
            selectionStorageFile.write('\t'*nestingLevel)
            selectionStorageFile.write("End_Sub_Dialog\n")

    def restoreSelections(self, selectionsStorageFile: TextIO):
        "Restores the dialog selections from the file corresponding to the dialog's title."
        
        # Iterate through lines until EOF or one of the "End..." lines are encountered.
        # Each group of elements should be present in its own cluster, in a predictable order.
        # We can take advantage of this and use sequential while loops to track each group.
        line = selectionsStorageFile.readline().strip()

        count = 0
        while line.startswith("Individual_File_Path"):
            self.individualFileEntries[count][0].delete(0, tk.END)
            self.individualFileEntries[count][0].insert(0, line.split(':')[1])
            line = selectionsStorageFile.readline().strip(); count += 1

        count = 0
        while line.startswith("File_Path_Group"):
            self.multipleFileSelectors[count].clearPathDisplays()
            for filePath in line.split(':')[1:]:
                self.multipleFileSelectors[count].addPathDisplay(filePath)
            line = selectionsStorageFile.readline().strip(); count += 1
            
        count = 0
        while line.startswith("Plain_Text_Entry"):
            self.plainTextEntries[count].delete(0, tk.END)
            self.plainTextEntries[count].insert(0, line.split(':')[1])
            line = selectionsStorageFile.readline().strip(); count += 1

        count = 0
        while line.startswith("Toggle_State"):
            self.checkboxVars[count].set(line.split(':')[1] == "True")
            line = selectionsStorageFile.readline().strip(); count += 1

        count = 0
        while line.startswith("Dropdown_Selection"):
            self.dropdownVars[count].set(line.split(':')[1])
            line = selectionsStorageFile.readline().strip(); count += 1

        count = 0
        while line.startswith("Start_Dynamic"):
            if line.startswith("Start_Dynamic_StringVar_Selector"):
                self.dynamicSelectors[count].setControllerVar(line.split(':')[1])
            elif line.startswith("Start_Dynamic_BooleanVar_Selector"):
                self.dynamicSelectors[count].setControllerVar(line.split(':')[1] == "True")
            self.dynamicSelectors[count].checkController()
            self.dynamicSelectors[count].getCurrentDisplay().restoreSelections(selectionsStorageFile)
            line = selectionsStorageFile.readline().strip(); count += 1

        count = 0
        while line.startswith("Start_Sub_Dialog"):
            self.subDialogs[count].saveSelections(selectionsStorageFile)
            line = selectionsStorageFile.readline().strip(); count += 1

        # Make sure we haven't ended prematurely.
        assert line.startswith("End") or not line


class Selections:
    "A data structure to hold the results from the TkinterDialog"

    def __init__(self, ID, individualFilePaths = None, filePathGroups = None, 
                 textEntries = None, toggleStates = None, dropdownSelections = None):

        # This is a dictionary for storing a list of input values as lists themselves.  (See key below)
        self.selectionSets: Dict[str, List[List]] = dict()
        self.selectionSets[ID] = list()

        # Sort the file path groups.
        if filePathGroups is not None:
            for i in range(len(filePathGroups)): filePathGroups[i] = sorted(filePathGroups[i])

        # Populate the selectionSet associated with the given ID.  List indices are given below
        # 0: individual file paths
        # 1: file path groups
        # 2: text entries
        # 3: toggle states
        # 4: dropdown selections
        if ID is not None:
            self.selectionSets[ID].append(individualFilePaths)
            self.selectionSets[ID].append(filePathGroups)
            self.selectionSets[ID].append(textEntries)
            self.selectionSets[ID].append(toggleStates)
            self.selectionSets[ID].append(dropdownSelections)


    # DEPRECATED: diverts to getIndividualFilePaths
    def getFilePaths(self, ID = "Root") -> List[str]:
        return self.getIndividualFilePaths(ID)

    def getIndividualFilePaths(self, ID = "Root") -> List[str]:
        return self.selectionSets[ID][0]

    def getFilePathGroups(self, ID = "Root") -> List[List[str]]:
        return self.selectionSets[ID][1]

    def getTextEntries(self, ID = "Root") -> List[str]:
        return self.selectionSets[ID][2]

    def getToggleStates(self, ID = "Root") -> List[bool]:
        return self.selectionSets[ID][3]

    def getDropdownSelections(self, ID = "Root") -> List[str]:
        return self.selectionSets[ID][4]


    def addSelections(self, newSelections):
        "Combines this Selections object with the given Selections object."

        newSelections: Selections
        for ID in newSelections.selectionSets:
            if ID is not None:
                assert ID not in self.selectionSets, "ID: " + ID + " is already present in the selection sets."
                self.selectionSets[ID] = newSelections.selectionSets[ID]
