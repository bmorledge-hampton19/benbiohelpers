# This script contains an abstract class for counting one thing (e.g. mutations) within another thing (e.g. nucleosomes)
# It contains a lot of modular components for, say, categorizing counts based on the strand relative to encompassing feature.
# I'm hoping this will save me a lot of time in the future!
from abc import ABC, abstractmethod
import warnings, subprocess
from typing import List
from mypyhelper.CountThisInThat.InputDataStructures import EncompassedData, EncompassingData
from mypyhelper.CountThisInThat.CounterOutputDataHandler import CounterOutputDataHandler


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
                 outputFilePath, acceptableChromosomes = None, encompassingFeatureExtraRadius = 0,
                 headersInEncompassedFeatures = False, headersInEncompassingFeatures = False,
                 checkForSortedFiles = True):

        if checkForSortedFiles:
            self.checkForSortedInput(encompassedFeaturesFilePath, encompassingFeaturesFilePath)

        # Open the encompassed and encompassing files to compare against one another.
        self.encompassedFeaturesFile = open(encompassedFeaturesFilePath, 'r')
        self.encompassingFeaturesFile = open(encompassingFeaturesFilePath,'r')

        # Store the other arguments passed to the constructor
        self.outputFilePath = outputFilePath
        self.acceptableChromosomes = acceptableChromosomes
        self.encompassingFeatureExtraRadius = encompassingFeatureExtraRadius

        # Skip headers if they are present.
        if headersInEncompassedFeatures: self.encompassedFeaturesFile.readline()
        if headersInEncompassingFeatures: self.encompassingFeaturesFile.readline()

        # Read in the first entry in each file (as the information within may be important to setting up output data structures)
        self.currentEncompassedFeature = None
        self.currentEncompassingFeature = None
        self.readNextEncompassedFeature()
        self.readNextEncompassingFeature()

        # Set up data structures for the output data and encompassed features confirmed to be within encompassing features.
        self.setUpOutputDataHandler()
        self.confirmedEncompassedFeatures: List[EncompassedData] = list()


    def checkForSortedInput(self, encompassedFeaturesFilePath, encompassingFeaturesFilePath):
        """
        Ensures that the two given files are properly sorted.
        Files should be sorted by the first column alphabetically followed by the next two columns numerically
        """
        print("Checking input files for proper sorting...")

        try:
            subprocess.check_output(("sort","-k1,1","-k2,3n", "-c", encompassedFeaturesFilePath))
        except subprocess.CalledProcessError:
            print("EncompassedFeatures file is not properly sorted.")
            quit()
            
        try:
            subprocess.check_output(("sort","-k1,1","-k2,3n", "-c", encompassingFeaturesFilePath))
        except subprocess.CalledProcessError:
            print("EncompassingFeatures file is not properly sorted.")
            quit()

        print("Files are properly sorted.")


    def readNextEncompassedFeature(self):
        """
        Reads in the next encompassed feature into currentEncompassedFeature
        """

        # Was the last feature actually encompassed? If not, pass it to the output data structure to be handled.
        if self.currentEncompassedFeature is not None and not self.isCurrentEncompassedFeatureActuallyEncompassed:
            self.outputDataHandler.onNonEncompassedFeature(self.currentEncompassedFeature)
        self.isCurrentEncompassedFeatureActuallyEncompassed = False

        # Read in the next line.
        nextLine = self.encompassedFeaturesFile.readline()

        # Check if EOF has been reached.
        if len(nextLine) == 0: 
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
        if len(nextLine) == 0: 
            self.currentEncompassingFeature = None
        # Otherwise, read in the next encompassing feature.
        else:
            self.currentEncompassingFeature = self.constructEncompassingFeature(nextLine)

        # Check confirmed encompasssed features against the new encompassing feature.  (Unless this is the first encompassing feature)
        if self.previousEncompassingFeature is not None: self.checkConfirmedEncompassedFeatures()


    def constructEncompassingFeature(self, line) -> EncompassingData:
        """
        Constructs the encompassing feature from the given line.
        Should be overridden to accommdate children of EncompassingData into children of ThisInThatCounter.
        """

        return EncompassingData(line, self.acceptableChromosomes)


    @abstractmethod
    def setUpOutputDataHandler(self):
        """
        An abstract method for setting up the output data structure(s).  
        Should probably be implemented to run one or more of the template functions in CounterOutputData or a child of it,
        but by default this sets up a very simple output data structure which just counts instances of encompassment.
        """
        self.outputDataHandler = CounterOutputDataHandler()


    def reconcileChromosomes(self):
        """
        Takes an encompassed object and encompassing object which have unequal chromosomes and reads through data until they are equal.
        """

        chromosomeChanged = False # A simple flag to determine when to inform the user that a new chromosome is being accessed

        # Until the chromosomes are the same for both mutations and genes, read through the one with the eariler chromosome.
        while (self.currentEncompassedFeature is not None and self.currentEncompassingFeature is not None and 
               self.currentEncompassedFeature.chromosome != self.currentEncompassingFeature.chromosome):
            chromosomeChanged = True
            if self.currentEncompassedFeature.chromosome < self.currentEncompassingFeature.chromosome: self.readNextEncompassedFeature()
            else: self.readNextEncompassingFeature()

        if chromosomeChanged and self.currentEncompassingFeature is not None and self.currentEncompassedFeature is not None: 
            self.printNewChromosomeMessage()


    def printNewChromosomeMessage(self):
        """
        Prints a message based on the current chromosome.  To be used when the current encompassing feature is in a new chromosome.
        """
        print("Counting in",self.currentEncompassingFeature.chromosome)


    def isEncompassedFeaturePastEncompassingFeature(self):
        """
        Determines whether or not the current encompassed feature is past the range of the current encompassing feature.
        """

        if self.currentEncompassedFeature is None:
            return True
        elif self.currentEncompassedFeature.position > self.currentEncompassingFeature.endPos + self.encompassingFeatureExtraRadius:
            return True
        elif not self.currentEncompassedFeature.chromosome == self.currentEncompassingFeature.chromosome:
            return True
        else: 
            return False


    def isEncompassedFeatureWithinEncompassingFeature(self):
        """
        Determines whether the current encompassed feature is within the range of the current encompassing feature.
        """
        return (self.currentEncompassedFeature.position >= self.currentEncompassingFeature.startPos - self.encompassingFeatureExtraRadius and
                self.currentEncompassedFeature.position <= self.currentEncompassingFeature.endPos + self.encompassingFeatureExtraRadius)


    def checkConfirmedEncompassedFeatures(self):    
        """
        For all encompassed features that are confirmed to be within the previous encompassing feature, figure out how to handle them
        based on the position of this new encompassing feature.  Record the features in the output data structures where appropriate.
        """

        # Flag any encompassed features that fall before the start position of the new encompassing feature to be recorded in their current state.

        # If this is the final validity check (no remaining encompassing features), all waiting features are exiting encompassment.
        if self.currentEncompassingFeature is None:
            featuresExitingEncompassment = self.confirmedEncompassedFeatures.copy()
        # Otherwise, check them against the range of the newest encompassing feature.
        else:
            featuresExitingEncompassment = [feature for feature in self.confirmedEncompassedFeatures 
                                            if feature.position < self.currentEncompassingFeature.startPos - self.encompassingFeatureExtraRadius or 
                                            feature.chromosome != self.currentEncompassingFeature.chromosome]

        # Handle all the features exiting encompassment.
        for feature in featuresExitingEncompassment:
            self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(feature, self.previousEncompassingFeature, True)

        # Separate out any remaining features.
        self.confirmedEncompassedFeatures = list(set(self.confirmedEncompassedFeatures) - set(featuresExitingEncompassment))

        # Next, reprocess all remaining features, provided they are not ahead of the encompassing feature's range.
        featuresToStopTracking = list()
        for feature in self.confirmedEncompassedFeatures:
            if feature.position <= self.currentEncompassingFeature.endPos + self.encompassingFeatureExtraRadius:
                continueTracking = self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(feature, self.currentEncompassingFeature, False)
                if not continueTracking: featuresToStopTracking.append(feature)

        # Remove any features that don't need to be tracked anymore.
        self.confirmedEncompassedFeatures = list(set(self.confirmedEncompassedFeatures) - set(featuresToStopTracking))


    def count(self):
        """
        Run through both files, counting encompassed features within encompassing features as detailed by classes setup.
        """

        # Double check the chromosomes in our features to make sure they are aligned and we don't have empty files.
        if self.currentEncompassedFeature is None or self.currentEncompassingFeature is None:
            warnings.warn("Empty file(s) given as input.  Output will most likely be unhelpful.")
        elif self.currentEncompassingFeature.chromosome == self.currentEncompassedFeature.chromosome: 
            self.printNewChromosomeMessage()
        else: self.reconcileChromosomes()

        # The core loop goes through each encompassing feature, one at a time, and checks encompassed feature positions against it until 
        # one exceeds its rightmost position or is on a different chromosome (or encompassed features are exhausted).  
        # Then, the next encompassing feature is checked, then the next, etc. until none are left.
        while self.currentEncompassingFeature is not None:

            # Read mutations until the encompassed feature is past the range of the encompassing feature.
            while not self.isEncompassedFeaturePastEncompassingFeature():

                # Check for any features with confirmed encompassment.
                if self.isEncompassedFeatureWithinEncompassingFeature(): 
                    self.confirmedEncompassedFeatures.append(self.currentEncompassedFeature)
                    self.outputDataHandler.onEncompassedFeatureInEncompassingFeature(self.currentEncompassedFeature, self.currentEncompassingFeature, False)
                    self.isCurrentEncompassedFeatureActuallyEncompassed = True

                # Get data on the next encompassed feature.
                self.readNextEncompassedFeature()

            # Read in a new encompassing feature and check any confirmed encompassed features.
            self.readNextEncompassingFeature()

            # Reconcile the encompassed and encompassing features to be sure that they are at the same chromosome for the next iteration
            self.reconcileChromosomes()

        # Read through any remaining encompassed features in case we are recording non-encompassed features.
        while self.currentEncompassedFeature is not None: self.readNextEncompassedFeature()

        # Close any open files.
        self.encompassedFeaturesFile.close()
        self.encompassingFeaturesFile.close()


    def writeResults(self, customStratifyingNames = None):
        """
        Use the output data handler to write the output data.
        """
        self.outputDataHandler.writeResults(self.outputFilePath, customStratifyingNames)