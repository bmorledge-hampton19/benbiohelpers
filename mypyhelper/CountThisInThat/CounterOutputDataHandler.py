# The class for parsing, formatting, and writing data from the ThisInThatCounter
from mypyhelper.CountThisInThat.InputDataStructures import EncompassedData, EncompassingData
from mypyhelper.CountThisInThat.OutputDataStratifiers import *
from typing import List


class CounterOutputDataHandler:
    """
    This class receives information on which encompassed features are within which encompassing features and determines how to
    record their data for the final output form.
    This class also handles data writing.
    *Places sticky note on back: "Inherit from me"*
    """

    def __init__(self, countNonEncompassed = False):
        """
        Initialize the object by setting default values 
        """

        self.countNonEncompassed = countNonEncompassed

        self.outputDataStratifiers: List[OutputDataStratifier] = list() # The ODS's used to stratify the data.

        # Placeholders for the features being examined at a given time.
        self.encompassedFeature = None
        self.encompassingFeature = None

        # Set up the most basic output data structre: If the feature is encompassed, include it!
        self.outputDataStructure = 0


    def getNewStratificationLevelDictionaries(self):
        """
        Creates and returns all dictionaries at the object's stratification level in the ODS
        """

        if len(self.outputDataStratifiers) == 0: self.outputDataStructure = dict()
        dictionariesToReturn = [self.outputDataStructure,]
        for _ in range(len(self.outputDataStratifiers)):
            tempDictionariesToReturn = list()
            for dictionary in dictionariesToReturn:
                for key in dictionary:
                    dictionary[key] = dict()
                    tempDictionariesToReturn.append(dictionary[key])
            dictionariesToReturn = tempDictionariesToReturn

        return dictionariesToReturn


    def addNewStratifier(self, stratifier: OutputDataStratifier):
        """
        Adds a new stratifier, assigning it as the child stratifier to the last stratifier added, if necessary.
        """
        self.outputDataStratifiers.append(stratifier)
        if len(self.outputDataStratifiers) > 1: self.outputDataStratifiers[-2].childDataStratifier = stratifier

    
    def addStrandComparisonStratifier(self, strandAmbiguityHandling = AmbiguityHandling.record, outputName = "Strand_Comparison"):
        """
        Adds a layer onto the output data structure to stratify by whether or not the strands of the encompassed and encompassing features match.
        """
        self.addNewStratifier(StrandComparisonODS(strandAmbiguityHandling, self.getNewStratificationLevelDictionaries(), outputName))


    def addRelativePositionStratifier(self, encompassingFeature: EncompassingData, centerRelativePos = True, 
                                      extraRangeRadius = 0, outputName = "Relative_Pos", positionAmbiguityHandling = AmbiguityHandling.tolerate):
        """
        Adds a layer onto the output data structure to stratify by the position of the encompassed data with the encompassing data.
        """
        self.addNewStratifier(RelativePosODS(positionAmbiguityHandling, self.getNewStratificationLevelDictionaries(),
                                                         encompassingFeature, centerRelativePos, extraRangeRadius, outputName))


    def addEncompassingFeatureStratifier(self, ambiguityHandling = AmbiguityHandling.tolerate, outputName = "Encompassing_Feature"):
        """
        Adds a layer onto the output data structure to stratify by encompassing features.
        """
        self.addNewStratifier(EncompassingFeatureODS(ambiguityHandling, self.getNewStratificationLevelDictionaries(), outputName))


    def addEncompassedFeatureContextStratifier(self, contextSize, includeAlteredTo, outputName = "Context"):
        """
        Adds a layer onto the output data structure to stratify by the surrounding nucleotide context of the encompassed feature.
        """
        self.addNewStratifier(EncompassedFeatureContextODS(self.getNewStratificationLevelDictionaries(), outputName, contextSize, includeAlteredTo))


    def updateEncompassedFeature(self):
        """
        Updates all relevant values for the encompassed feature relative to the encompassing feature.
        """
        for outputDataStratifier in self.outputDataStratifiers: 
            outputDataStratifier.updateData(self.encompassedFeature, self.encompassingFeature)


    def countFeature(self):
        """
        Increments the proper object in the output data structure.
        """

        # Account for the base case where we are just counting all features.
        if len(self.outputDataStratifiers) == 0: 
            self.outputDataStratifiers += 1
            return

        # Drill down through the ODS's using the relevant keys from this encompassed feature to determine where to count.
        currentODSDict = self.outputDataStructure
        for outputDataStratifier in self.outputDataStratifiers[:-1]:
            currentODSDict = currentODSDict[outputDataStratifier.getRelevantKey(self.encompassedFeature)]
        currentODSDict[self.outputDataStratifiers[-1].getRelevantKey(self.encompassedFeature)] += 1


    def checkFeatureStatus(self, exitingEncompassment):
        """
        Determines whether or not the current encompassed feature should be counted based on ambiguity handling and whether or not it is exiting encompassment.
        Also determines whether or not the feature has a chance of being counted in the feature (whether or not it should still be tracked.)
        The function returns these two values as a tuple.  (countNow first, followed by continueTracking)
        """

        # Account for the base case of just counting everything.
        if len(self.outputDataStratifiers) == 0: return (not exitingEncompassment, not exitingEncompassment)

        # Traverse the list of output data stratifiers checking for states that invalidate counting of this feature.
        nontolerantAmbiguityHandling = False
        waitingOnAmbiguityChecks = False
        for oDS in self.outputDataStratifiers:
            if oDS.ambiguityHandling == AmbiguityHandling.tolerate: 
                pass
            else:
                nontolerantAmbiguityHandling = True
                if oDS.ambiguityHandling == AmbiguityHandling.record:
                    if oDS.getRelevantKey(self.encompassedFeature) is not None: waitingOnAmbiguityChecks = True
                else:
                    if oDS.getRelevantKey(self.encompassedFeature) is None: 
                        return (False, False) # There is an ODS that ignores ambiguity, and its key is ambiguous.  Don't count EVER.
                    else: waitingOnAmbiguityChecks = True

        # Is there any nontolerant ambiguity handling in this data structure? If so, do we have enough information to count it now?
        if nontolerantAmbiguityHandling:
            if not waitingOnAmbiguityChecks or exitingEncompassment: return (True, False)
            else: return (False, True)

        # If all ambiguity handling is tolerant and we are not exiting encompassment, count and continue tracking.
        elif not exitingEncompassment: return (True, True)

        # Otherwise, if we ARE exiting encompassment, don't count and stop tracking.
        else: return (False, False)


    def onEncompassedFeatureInEncompassingFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData, exitingEncompassment):
        """
        Handles the case where an encompassed feature is within an encompassing feature.
        Returns true or false based on whether or not the feature should be tracked in the future based on ambiguity handling and stuff.
        If exitingEncompassment is true, the object has been seen previously but is now GUARANTEED to not be encompassed in the future.
        Otherwise, the object MAY be seen again before it exits encompassment.
        """

        # Store the given features within this object.
        self.encompassedFeature = encompassedFeature
        self.encompassingFeature = encompassingFeature

        # First, update the encompassed feature based on the given encompassing feature unless it is exiting encompassment.
        if not exitingEncompassment: self.updateEncompassedFeature()

        # Next, figure out whether or not the object should be counted, and whether or not it still needs to be tracked.
        countFeature, continueTracking = self.checkFeatureStatus(exitingEncompassment)
        if countFeature: self.countFeature()
        return continueTracking


    def onNonEncompassedFeature(self, encompassedFeature: EncompassedData):
        """
        If the Output Data Handler is set up to count non-encompassed data, do it here.
        """

        if self.countNonEncompassed:
            
            self.encompassedFeature = encompassedFeature
            self.encompassingFeature = None
            self.updateEncompassedFeature()
            self.countFeature()

    
    def getCountDerivatives(self, previousKeys, getHeaders = False) -> List[str]:
        """
        Gets additional counts that are not explicitly defined within the output data structure.
        For example, the counts for both strands combined or both strands combined and aligned during dyad position counting.
        if getHeaders is true, the headers for the new data columns are returned instead.
        All return types should be lists of strings so they can be directly written to the output file using join.
        Also, MAKE SURE that the both lists returned whether getHeaders is true or false are of the SAME LENGTH.
        Should be overridden in children class, as the base functionality just returns empty lists.
        """
        return list()


    def writeResults(self, outputFilePath, customStratifyingNames = None):
        """
        Writes the results of the output data structure to a given file.
        The customStratifyingNames variable, if supplied, should contain a list of dictionaries to convert keys to the desired string output.
        If not none, the list should have as many entries as layers in the output data structure, but any given entry can be "None" to indicate
        that naming should just use the keys.
        """

        # A convenience function for getting output names from keys based on the customStratifyingNames parameter.
        def getOutputName(stratificationLevel, key):

            if (customStratifyingNames is None 
                or customStratifyingNames[stratificationLevel] is None 
                or key not in customStratifyingNames[stratificationLevel]):
                return str(key)
            else: return customStratifyingNames[stratificationLevel][key]

        with open(outputFilePath, 'w') as outputFile:

            # Did we receive a valid customStratifyingNames parameter?
            assert customStratifyingNames is None or len(customStratifyingNames) == len(self.outputDataStratifiers), (
                "Custom stratifying names given, but there is not exactly one entry for each ODS.")

            # Account for the base case of just counting everything.
            if len(self.outputDataStratifiers) == 0: outputFile.write(str(self.outputDataStructure) + '\n')

            else:

                # First, write the headers based on the keys of the last data structure and the output names of any others,
                # as well as any "count derivatives" defined in children class (See getCountDerivatives method).
                headers = list()
                if len(self.outputDataStratifiers) > 1:
                    for outputDataStratifier in self.outputDataStratifiers[:-1]:
                        headers.append(outputDataStratifier.outputName)
                for key in self.outputDataStratifiers[-1].getKeysForOutput():
                    headers.append(getOutputName(-1, key))

                headers += self.getCountDerivatives(None, getHeaders = True)

                outputFile.write('\t'.join(headers) + '\n')

                # Next, write the rest of the data using a recursive function for writing rows of data from 
                # an output data structure of an unknown number of stratifiacion levels.
                currentDataRow = [None]*(len(self.outputDataStratifiers) - 1 + len(headers))
                previousKeys = [None]*(len(self.outputDataStratifiers) - 1)
                def addDataRow(currentDataObject, stratificationLevel):

                    # If we're not at the final level of the data structure, iterate through it, recursively calling this function on the results.
                    if stratificationLevel + 1 != len(self.outputDataStratifiers):
                        for key in self.outputDataStratifiers[stratificationLevel].getKeysForOutput():
                            currentDataRow[stratificationLevel] = getOutputName(stratificationLevel, key)
                            previousKeys[stratificationLevel] = key
                            addDataRow(currentDataObject[key],stratificationLevel + 1)
                    
                    # Otherwise, add the entries in this dictionary (which should be integers representing counts) to the data row 
                    # along with any count derivatives and write the row.
                    else:
                        for i, key in enumerate(self.outputDataStratifiers[stratificationLevel].getKeysForOutput()):
                            currentDataRow[stratificationLevel + i] = str(currentDataObject[key])
                        currentDataRow[stratificationLevel + i + 1:] = self.getCountDerivatives(previousKeys)
                        outputFile.write('\t'.join(currentDataRow) + '\n')

                addDataRow(self.outputDataStructure, 0)