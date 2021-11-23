# This script contains an abstract class for counting one thing (e.g. mutations) within another thing (e.g. nucleosomes)
# It contains a lot of modular components for, say, categorizing counts based on the strand relative to encompassing feature.
# I'm hoping this will save me a lot of time in the future!
from abc import ABC, abstractmethod
import warnings, subprocess
from typing import List
from benbiohelpers.CountThisInThat.InputDataStructures import EncompassedData, EncompassingData, ENCOMPASSED_DATA, ENCOMPASSING_DATA
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import CounterOutputDataHandler


class ThisInThatCounter(ABC):
    """
    An abstract class with extremely modular structure to allow for easier scripting for the many "Count this in that, but also keep track of those..."
    problems that I seem to come across.
    The class should be supplied with two file paths, one for the encompassed features (e.g. mutations), 
    and one for the encompassing features (e.g. nucleosomes).
    At it's core, the class counts the encompassed features when they are within the encompassing feature, and keeps track of those counts to be written
    at the end of the class's implementation.

    NOTE:  It is VITAL that both files are sorted, first by chromosome number and then by starting and ending coordinates.
    This is because the code reads through the files in parallel to ensure linear runtime, but as a result, 
    it will crash and burn and give you a heap of garbage as output if the inputs aren't sorted.
    """

    def __init__(self, encompassedFeaturesFilePath, encompassingFeaturesFilePath, 
                 outputFilePath, acceptableChromosomes = None, checkForSortedFiles = (True,True),
                 headersInEncompassedFeatures = False, headersInEncompassingFeatures = False,
                 encompassingFeatureExtraRadius = 0, writeIncrementally = 0):

        self.checkForSortedInput(encompassedFeaturesFilePath, encompassingFeaturesFilePath, checkForSortedFiles)

        # Open the encompassed and encompassing files to compare against one another.
        self.encompassedFeaturesFile = open(encompassedFeaturesFilePath, 'r')
        self.encompassingFeaturesFile = open(encompassingFeaturesFilePath,'r')

        # Store the other arguments passed to the constructor
        self.outputFilePath = outputFilePath
        self.writeIncrementally = writeIncrementally # 0 by default, or one of the two constants: ENCOMPASSED_DATA or ENCOMPASSING_DATA
        self.acceptableChromosomes = acceptableChromosomes
        self.encompassingFeatureExtraRadius = encompassingFeatureExtraRadius

        # Skip headers if they are present.
        if headersInEncompassedFeatures: self.encompassedFeaturesFile.readline()
        if headersInEncompassingFeatures: self.encompassingFeaturesFile.readline()

        # Read in the first entry in each file (as the information within may be important to setting up output data structures)
        self.currentEncompassedFeature = None
        self.currentEncompassingFeature = None
        self.lastNonEncompassedFeature = None
        self.readNextEncompassedFeature()
        self.readNextEncompassingFeature()

        # Set up data structures for the output data and tracking the state of encompassed features.
        self.setUpOutputDataHandler()
        self.confirmedEncompassedFeatures: List[EncompassedData] = list()

        # This is normally called within readNextEncompassingFeature, but for the first pass, the output data handler doesn't exist.
        # So... Call it now instead!
        self.outputDataHandler.onNewEncompassingFeature(self.currentEncompassingFeature)


    def checkForSortedInput(self, encompassedFeaturesFilePath, encompassingFeaturesFilePath, checkForSortedFiles):
        """
        Ensures that the two given files are properly sorted.
        Files should be sorted by the first column alphabetically followed by the next two columns numerically
        The checkForSortedFiles parameter should be a two-item tuple containing boolean values telling whether to
        check the encompassed and encompassing feature files respectively.
        """
        print("Checking input files for proper sorting...")

        if checkForSortedFiles[0]:
            print("Checking encompassed features file for proper sorting...")
            try:
                subprocess.check_output(("sort","-k1,1","-k2,2n", "-k3,3n", "-s", "-c", encompassedFeaturesFilePath))
            except subprocess.CalledProcessError:
                print("Encompassed features file is not properly sorted.")
                quit()
            
        if checkForSortedFiles[1]:
            print("Checking encompassing features file for proper sorting...")
            try:
                subprocess.check_output(("sort","-k1,1","-k2,2n", "-k3,3n", "-s", "-c", encompassingFeaturesFilePath))
            except subprocess.CalledProcessError:
                print("Encompassing features file is not properly sorted.")
                quit()


    def readNextEncompassedFeature(self):
        """
        Reads in the next encompassed feature into currentEncompassedFeature
        """

        # Was the last feature actually encompassed? If not, pass it to the output data structure to be handled.
        if self.currentEncompassedFeature is not None and not self.isCurrentEncompassedFeatureActuallyEncompassed:

            # If we are writing encompassed positions individually, do we have a large number of features waiting to be written?
            # If so, this means we are tracking non-encompassed features and we have a large stretch between encompassing features.
            # So, to prevent the non-encompassed features from filling up memory, write them!
            if self.writeIncrementally == ENCOMPASSED_DATA and len(self.outputDataHandler.encompassedFeaturesToWrite) > 10000 and (
                self.lastNonEncompassedFeature < self.currentEncompassedFeature
            ):
                self.outputDataHandler.writeWaitingFeatures()

            self.outputDataHandler.onNonCountedEncompassedFeature(self.currentEncompassedFeature)
            self.lastNonEncompassedFeature = self.currentEncompassedFeature
        self.isCurrentEncompassedFeatureActuallyEncompassed = False

        # Read in the next line.
        nextLine = self.encompassedFeaturesFile.readline()

        # Check if EOF has been reached.
        if not nextLine: 
            self.currentEncompassedFeature = None
        # Otherwise, read in the next encompassed feature.
        else:
            self.currentEncompassedFeature = self.constructEncompassedFeature(nextLine)

        

    def constructEncompassedFeature(self, line) -> EncompassedData:
        """
        Constructs the encompassed feature from the given line.
        Should be overridden to accommdate children of EncompassedData into children of ThisInThatCounter.
        """

        return EncompassedData(line, self.acceptableChromosomes)


    def readNextEncompassingFeature(self):
        """
        Reads in the next encompassing feature into currentEncompassingFeature
        """

        # Keep track of the previous encompassing feature for when we check confirmed encompassed features.
        self.previousEncompassingFeature = self.currentEncompassingFeature

        # Read in the next line.
        nextLine = self.encompassingFeaturesFile.readline()

        # Check if EOF has been reached.
        if not nextLine:
            self.currentEncompassingFeature = None
        # Otherwise, read in the next encompassing feature.
        else:
            self.currentEncompassingFeature = self.constructEncompassingFeature(nextLine)
            # After the first pass, make sure to send all new encompassing features to the output data handler.
            if self.previousEncompassingFeature is not None: 
                self.outputDataHandler.onNewEncompassingFeature(self.currentEncompassingFeature)
            # Inform the user every time a new chromosome is encountered in an encompassing feature
            if (self.previousEncompassingFeature is None 
                or self.previousEncompassingFeature.chromosome != self.currentEncompassingFeature.chromosome):
                print("Counting in",self.currentEncompassingFeature.chromosome)

        # Check confirmed encompasssed features against the new encompassing feature.  (Unless this is the first encompassing feature)
        if self.previousEncompassingFeature is not None: self.checkConfirmedEncompassedFeatures()


    def constructEncompassingFeature(self, line) -> EncompassingData:
        """
        Constructs the encompassing feature from the given line.
        Should be overridden to accommdate children of EncompassingData into children of ThisInThatCounter.
        """

        return EncompassingData(line, self.acceptableChromosomes)


    def setUpOutputDataHandler(self):
        """
        An abstract method for setting up the output data structure(s).
        Calls the three functions below to achieve this.
        By default this sets up a very simple output data structure which just counts instances of encompassment.
        """
        self.initOutputDataHandler()
        self.setupOutputDataStratifiers()
        self.setupOutputDataWriter()


    def initOutputDataHandler(self):
        """
        Use this function to create the instance of the CounterOutputDataHandler object.
        Default behavior creates the output data handler and passes in the counter's "writeIncrementally" value.
        """
        self.outputDataHandler = CounterOutputDataHandler(self.writeIncrementally)


    def setupOutputDataStratifiers(self):
        """
        Use this function to set up any output data stratifiers for the output data handler.
        Default behavior sets up no stratifiers.
        """
        pass


    def setupOutputDataWriter(self):
        """
        Use this funciton to set up the output data writer.
        Default behavior creates the output data writer with the counter's "outputFilePath" value
        """
        self.outputDataHandler.createOutputDataWriter(self.outputFilePath)


    def reconcileChromosomes(self):
        """
        Takes an encompassed object and encompassing object which have unequal chromosomes and reads through data until they are equal.
        """

        # Until the chromosomes are the same for both mutations and genes, read through the one with the eariler chromosome.
        while (self.currentEncompassedFeature is not None and self.currentEncompassingFeature is not None and 
               self.currentEncompassedFeature.chromosome != self.currentEncompassingFeature.chromosome):
            if self.currentEncompassedFeature.chromosome < self.currentEncompassingFeature.chromosome: self.readNextEncompassedFeature()
            else: self.readNextEncompassingFeature()


    def isEncompassedFeaturePastEncompassingFeature(self):
        """
        Determines whether or not the current encompassed feature is past the range of the current encompassing feature.
        """

        if self.currentEncompassedFeature is None:
            return True
        elif self.currentEncompassedFeature.position > self.currentEncompassingFeature.endPos + self.encompassingFeatureExtraRadius:
            return True
        elif self.currentEncompassedFeature.chromosome != self.currentEncompassingFeature.chromosome:
            return True
        else: 
            return False


    def isEncompassedFeatureWithinEncompassingFeature(self, encompassedFeature = None, encompassingFeature = None):
        """
        Determines whether the given encompassed feature is within the range of the given encompassing feature.
        By default (the "None" case), this function uses the current encompassed and encompassing features.
        """
        if encompassedFeature is None: encompassedFeature = self.currentEncompassedFeature
        if encompassingFeature is None: encompassingFeature = self.currentEncompassingFeature

        return (encompassedFeature.position >= encompassingFeature.startPos - self.encompassingFeatureExtraRadius and
                encompassedFeature.position <= encompassingFeature.endPos + self.encompassingFeatureExtraRadius)


    def isExitingEncompassment(self, encompassedFeature: EncompassedData):
        """
        Returns a boolean value representing whether or not the feature is exiting encompassment with the given new encompassing feature.
        Also, if the feature is exiting encompassment, send it to the output data handler.
        """
        if (encompassedFeature.position < self.currentEncompassingFeature.startPos - self.encompassingFeatureExtraRadius or 
            encompassedFeature.chromosome != self.currentEncompassingFeature.chromosome):
            self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(encompassedFeature, self.previousEncompassingFeature, True)
            return True
        else: return False


    def checkConfirmedEncompassedFeatures(self):    
        """
        For all encompassed features that are confirmed to be within the previous encompassing feature, figure out how to handle them
        based on the position of this new encompassing feature.  Record the features in the output data structures where appropriate.
        """

        # Flag any encompassed features that fall before the start position of the new encompassing feature to be recorded in their current state.

        # If this is the final validity check (no remaining encompassing features), all waiting features are exiting encompassment.
        if self.currentEncompassingFeature is None:
            for feature in self.confirmedEncompassedFeatures:
                self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(feature, self.previousEncompassingFeature, True)
            self.confirmedEncompassedFeatures.clear()
        # Otherwise, check them against the range of the newest encompassing feature.
        else: self.confirmedEncompassedFeatures = [feature for feature in self.confirmedEncompassedFeatures if not self.isExitingEncompassment(feature)]

        # Next, reprocess all remaining features, provided they are not ahead of the encompassing feature's range.
        for feature in self.confirmedEncompassedFeatures:
            if self.isEncompassedFeatureWithinEncompassingFeature(feature):
                self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(feature, self.currentEncompassingFeature, False)

        # Tell the output data handler to write the current set of features if incremental writing is requested.
        if self.writeIncrementally != 0: self.outputDataHandler.writeWaitingFeatures()


    def count(self):
        """
        Run through both files, counting encompassed features within encompassing features as detailed by classes setup.
        """

        # Double check the chromosomes in our features to make sure they are aligned and we don't have empty files.
        if self.currentEncompassedFeature is None or self.currentEncompassingFeature is None:
            warnings.warn("Empty file(s) given as input.  Output will most likely be unhelpful.")
        else: self.reconcileChromosomes()

        # The core loop goes through each encompassing feature, one at a time, and checks encompassed feature positions against it until 
        # one exceeds its rightmost position or is on a different chromosome (or encompassed features are exhausted).  
        # Then, the next encompassing feature is checked, then the next, etc. until none are left.
        while self.currentEncompassingFeature is not None:

            # Read mutations until the encompassed feature is past the range of the encompassing feature.
            while not self.isEncompassedFeaturePastEncompassingFeature():

                # Check for any features with confirmed encompassment.
                if self.isEncompassedFeatureWithinEncompassingFeature():
                    self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(self.currentEncompassedFeature, self.currentEncompassingFeature, False)
                    self.confirmedEncompassedFeatures.append(self.currentEncompassedFeature)
                    self.isCurrentEncompassedFeatureActuallyEncompassed = True

                # Get data on the next encompassed feature.
                self.readNextEncompassedFeature()

            # Read in a new encompassing feature and check any confirmed encompassed features.
            self.readNextEncompassingFeature()

            # Reconcile the encompassed and encompassing features to be sure that they are at the same chromosome for the next iteration
            self.reconcileChromosomes()

        # Read through any remaining encompassed features in case we are recording non-encompassed features.
        while self.currentEncompassedFeature is not None: self.readNextEncompassedFeature()
        if self.writeIncrementally != 0: self.outputDataHandler.writeWaitingFeatures() # Can catch any waiting encompassed features.

        # Close files open for reading.
        self.encompassedFeaturesFile.close()
        self.encompassingFeaturesFile.close()

        # Write (or finish writing) as necessary.
        if self.writeIncrementally: self.outputDataHandler.writer.finishIndividualFeatureWriting()
        else: self.outputDataHandler.writer.writeResults()