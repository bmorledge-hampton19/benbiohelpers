# The class for parsing, formatting, and writing data from the ThisInThatCounter
from benbiohelpers.CountThisInThat.InputDataStructures import EncompassedData, EncompassingData, ENCOMPASSING_DATA, ENCOMPASSED_DATA
from benbiohelpers.CountThisInThat.OutputDataStratifiers import *
from typing import List, Type, Union
import subprocess, warnings


class CounterOutputDataHandler:
    """
    This class receives information on which encompassed features are within which encompassing features and determines how to
    record their data for the final output form.
    This class also handles data writing.
    *Places sticky note on back: "Inherit from me"*
    """

    def __init__(self, incrementalWriting, trackAllEncompassing = False, trackAllEncompassed = False, countAllEncompassed = False):
        """
        Initialize the object by setting default values
        The incrementalWriting parameter flags either encompassed or encompassing features (or None) to be written incrementally.
        The two tracking parameters specify whether or not the respective features should be tracked even if they are not counted.
        (Usually, this is used for tracking 0 counts)
        The countAllEncompassed parameter actually counts even those features which aren't actually encompassed or wouldn't be counted otherwise.
        """

        # Set tracking options to False by default.
        self.trackAllEncompassing = trackAllEncompassing
        self.trackAllEncompassed = trackAllEncompassed
        self.countAllEncompassed = countAllEncompassed
        assert not self.countAllEncompassed or self.trackAllEncompassed, "All encompassed features cannot be counted if they aren't tracked."

        self.outputDataStratifiers: List[OutputDataStratifier] = list() # The ODS's used to stratify the data.
        self.nontolerantAmbiguityHandling = False # To start, there is no non-tolerant ambiguity handling.
        self.ignoreAmbiguityODSs: List[OutputDataStratifier] = list()

        # Sets to keep track of features that will be written when it is guaranteed that they will not be seen again.
        # NOTE: See writeWaitingFeatures for possible exceptions.
        # Set to none if the relevant feature will not actually be written incrementally.
        self.encompassedFeaturesToWrite = None
        self.encompassingFeaturesToWrite = None
        if incrementalWriting is not None:
            if incrementalWriting == ENCOMPASSED_DATA:
                self.encompassedFeaturesToWrite = set()
            elif incrementalWriting == ENCOMPASSING_DATA:
                self.encompassingFeaturesToWrite = set()

        # Set up the most basic output data structre: If the feature is encompassed, include it!
        self.outputDataStructure = 0

        # Placeholder for OutputDataWriter
        self.writer: OutputDataWriter = None


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


    def addFeatureFractionStratifier(self, ambiguityHandling = AmbiguityHandling.tolerate, outputName = "Feature_Fraction", 
                                     fractionNum = 6, flankingBinSize = 0):
        """
        Adds a stratification layer for fractional binning.
        """
        self.addNewStratifier(FeatureFractionODS(ambiguityHandling, self.getNewStratificationLevelDictionaries(), outputName, 
                                                 fractionNum, flankingBinSize))


    def addEncompassingFeatureStratifier(self, ambiguityHandling = AmbiguityHandling.tolerate, outputName = "Encompassing_Feature"):
        """
        Adds a layer onto the output data structure to stratify by encompassing features.
        """
        self.addNewStratifier(EncompassingFeatureODS(ambiguityHandling, self.getNewStratificationLevelDictionaries(), outputName))


    def addEncompassedFeatureStratifier(self, outputName = "Encompassed_Feature"):
        """
        Adds a layer onto the output data structure to stratify by encompassed features.
        """
        self.addNewStratifier(EncompassedFeatureODS(self.getNewStratificationLevelDictionaries(), outputName))


    def addEncompassedFeatureContextStratifier(self, contextSize, includeAlteredTo, outputName = "Context"):
        """
        Adds a layer onto the output data structure to stratify by the surrounding nucleotide context of the encompassed feature.
        """
        self.addNewStratifier(EncompassedFeatureContextODS(self.getNewStratificationLevelDictionaries(), outputName, contextSize, includeAlteredTo))


    def addPlaceholderStratifier(self, ambiguityHandling = AmbiguityHandling.tolerate, outputName = None):
        """
        Adds a layer onto the output data structure to make sure that the last data column just contains raw counts.
        Only change ambiguity handling if you want to ensure that all encompassed features are only counted once.  (Change to "record")
        """
        self.addNewStratifier(PlaceholderODS(self.getNewStratificationLevelDictionaries(), ambiguityHandling, outputName))


    def addSupplementalInformationHandler(self, supplementalInfoClass: Type[SupplementalInformationHandler], 
                                          stratificationLevel, defaultArgs = True, outputName = None,
                                          updateUntilExit = None, updateOnCount = None):
        """
        Adds the specified supplemental information handler to the given stratification level.
        Keep in mind that SIH's cannot be added to the bottom level stratifier, as they store information in the specified
        level's child stratifier.
        If outputName is set to None, the default output name is used.
        """
        if defaultArgs:
            self.outputDataStratifiers[stratificationLevel].addSuplementalInfo(supplementalInfoClass())
        else:
            self.outputDataStratifiers[stratificationLevel].addSuplementalInfo(supplementalInfoClass(outputName, updateUntilExit, updateOnCount))


    def createOutputDataWriter(self, outputFilePath: str, oDSSubs: List = None, 
                               customStratifyingNames = None, getCountDerivatives = None):
        """
        Pretty self explanatory.  See the __init__ method for OutputDataWriter for more info.

        Also performs some quick checks on the ambiguity handling of the stratifiers.
        """
        for outputDataStratifier in self.outputDataStratifiers:
            ambiguityHandling = outputDataStratifier.ambiguityHandling
            if ambiguityHandling is not AmbiguityHandling.tolerate: self.nontolerantAmbiguityHandling = True
            if ambiguityHandling is AmbiguityHandling.ignore:
                self.ignoreAmbiguityODSs.append(outputDataStratifier)
                if self.countAllEncompassed: warnings.warn("Ignoring ambiguity is pointless when counting all encompassed features.")

        self.writer = OutputDataWriter(self.outputDataStructure, self.outputDataStratifiers, outputFilePath,
                                       oDSSubs = oDSSubs, customStratifyingNames = customStratifyingNames,
                                       getCountDerivatives = getCountDerivatives)

        if self.encompassedFeaturesToWrite is not None or self.encompassingFeaturesToWrite is not None:
            assert isinstance(self.outputDataStratifiers[0], (EncompassedFeatureODS, EncompassingFeatureODS)), (
                "Cannot write individual features unless leading ODS is an encompassed/encompassing feature ODS."
            )


    def writeWaitingFeatures(self):
        """
        Writes any waiting features, with the guarantee that they will not be seen again due to the sorting imposed on the input files.
        """
        if self.encompassedFeaturesToWrite is not None:
            for encompassedFeature in sorted(self.encompassedFeaturesToWrite):
                self.writer.writeFeature(encompassedFeature)
                self.outputDataStructure.pop(encompassedFeature)
            self.encompassedFeaturesToWrite.clear()

        if self.encompassingFeaturesToWrite is not None:
            for encompassingFeature in sorted(self.encompassingFeaturesToWrite):
                self.writer.writeFeature(encompassingFeature)
                self.outputDataStructure.pop(encompassingFeature)
            self.encompassingFeaturesToWrite.clear()


    def updateODSs(self, encompassedFeature, encompassingFeature):
        """
        Updates all relevant values in each ODS using the current encompassed and encompassing features.
        """

        for outputDataStratifier in self.outputDataStratifiers: 
            outputDataStratifier.updateConfirmedEncompassedFeature(encompassedFeature, encompassingFeature)
            if outputDataStratifier is not self.outputDataStratifiers[-1]:
                if outputDataStratifier is self.outputDataStratifiers[0]: currentODSDict = self.outputDataStructure
                currentODSDict = currentODSDict[outputDataStratifier.getRelevantKey(encompassedFeature)]
                for i, supplementalInfoHandler in enumerate(outputDataStratifier.supplementalInfoHandlers):
                    if supplementalInfoHandler.updateUntilExit:
                        currentODSDict[SUP_INFO_KEY][i] = supplementalInfoHandler.updateSupplementalInfo(currentODSDict[SUP_INFO_KEY][i], 
                                                                                                         encompassedFeature, encompassingFeature)


    def onNonCountedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData = None):
        """
        If the Output Data Handler is set up to track non-counted encompassed data, do it here.
        """

        if self.trackAllEncompassed:
            for outputDataStratifier in self.outputDataStratifiers: 
                outputDataStratifier.onNonCountedEncompassedFeature(encompassedFeature)
            if self.encompassedFeaturesToWrite is not None: self.encompassedFeaturesToWrite.add(encompassedFeature)
            if self.countAllEncompassed: self.countFeature(encompassedFeature, encompassingFeature)


    def onNewEncompassingFeature(self, encompassingFeature: EncompassingData):
        """
        If the Output Data Handler is set up to track all encompassing data, do it here.
        """

        if self.trackAllEncompassing:
            for outputDataStratifier in self.outputDataStratifiers: 
                outputDataStratifier.onNewEncompassingFeature(encompassingFeature)
            if self.encompassingFeaturesToWrite is not None: self.encompassingFeaturesToWrite.add(encompassingFeature)


    def countFeature(self, encompassedFeature, encompassingFeature):
        """
        If count is true, increments the proper object in the output data structure.
        Otherwise, just updates supplemental information.
        """

        # Account for the base case where we are just counting all features.
        if len(self.outputDataStratifiers) == 0: 
            self.outputDataStructure += 1
            return

        # Drill down through the ODS's using the relevant keys from this encompassed feature to determine where to count.
        currentODSDict = self.outputDataStructure
        for outputDataStratifier in self.outputDataStratifiers[:-1]:
            currentODSDict = currentODSDict[outputDataStratifier.getRelevantKey(encompassedFeature)]
            for i, supplementalInfoHandler in enumerate(outputDataStratifier.supplementalInfoHandlers):
                if supplementalInfoHandler.updateOnCount:
                    currentODSDict[SUP_INFO_KEY][i] = supplementalInfoHandler.updateSupplementalInfo(currentODSDict[SUP_INFO_KEY][i], 
                                                                                                     encompassedFeature, encompassingFeature)
        currentODSDict[self.outputDataStratifiers[-1].getRelevantKey(encompassedFeature)] += 1


    def checkFeatureStatus(self, encompassedFeature, exitingEncompassment):
        """
        DEPRECATED: This function was overly complex for the purpose it was meant to serve and was just creating issues... That being said,
        it does offer some insight into how features could be tracked more precisely, so I'm keeping it around just in case, even though it's never called.

        Determines whether or not the current encompassed feature should be counted based on ambiguity handling and whether or not it is exiting encompassment.
        Also determines whether or not the feature has a chance of being counted in the future (whether or not it should still be tracked.)
        The function returns these two values as a tuple.  (countNow first, followed by continueTracking)
        """

        # Account for the base case of just counting everything.
        if len(self.outputDataStratifiers) == 0: return (not exitingEncompassment, not exitingEncompassment)

        # Traverse the list of output data stratifiers checking for states that invalidate counting of this feature.
        if self.nontolerantAmbiguityHandling:
            waitingOnAmbiguityChecks = False
            for oDS in self.outputDataStratifiers:
                if oDS.ambiguityHandling is AmbiguityHandling.record:
                    if oDS.getRelevantKey(encompassedFeature) is not None: waitingOnAmbiguityChecks = True
                elif oDS.ambiguityHandling is AmbiguityHandling.ignore:
                    if oDS.getRelevantKey(encompassedFeature) is None: 
                        # There is an ODS that ignores ambiguity, and its key is ambiguous.  Don't count,
                        # and stop tracking unless we are still tracking supplemental information
                        return (False, (self.updateSupInfoUntilExit and not exitingEncompassment)) 
                    else: waitingOnAmbiguityChecks = True

        # Given that there is nontolerant ambiguity handling in the ODS's, do we have enough information to count now?
            if (not waitingOnAmbiguityChecks and not self.updateSupInfoUntilExit) or exitingEncompassment: return (True, False)
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

        # Record the encompassing feature if they are being written incrementally.
        if self.encompassingFeaturesToWrite is not None: self.encompassingFeaturesToWrite.add(encompassingFeature)

        # First, update the encompassed feature and supplemental information based on the given encompassing feature unless it is exiting encompassment.
        if not exitingEncompassment: self.updateODSs(encompassedFeature, encompassingFeature)

        # If we don't have nontolerant ambiguity handling, and are not exiting encompassment, count the feature!
        # Otherwise, if we are exiting encompassment, check to see if we need to add this to the list of features to write.
        if not self.nontolerantAmbiguityHandling: 
            if not exitingEncompassment: self.countFeature(encompassedFeature, encompassingFeature)
            elif self.encompassedFeaturesToWrite is not None: self.encompassedFeaturesToWrite.add(encompassedFeature)

        # If we have nontolerant ambiguity handling and are exiting encompassment, handle the features accordingly.
        elif exitingEncompassment:

            ignoreFeature = False
            for oDS in self.ignoreAmbiguityODSs:
                if oDS.getRelevantKey(encompassedFeature) is None: ignoreFeature = True
            
            # If this feature should be ignored, pass it along as "non-counted".  Otherwise, count it!
            if ignoreFeature: self.onNonCountedEncompassedFeature(encompassedFeature, encompassingFeature)
            else: 
                self.countFeature(encompassedFeature, encompassingFeature)
                if self.encompassedFeaturesToWrite is not None: self.encompassedFeaturesToWrite.add(encompassedFeature)


class OutputDataWriter():

    def __init__(self, outputDataStructure, outputDataStratifiers, outputFilePath: str,
                    oDSSubs: List = None, customStratifyingNames = None, getCountDerivatives = None):
        """
        Set up the OutputDataWriter by providing access to the output data stratifiers and the underlying dictionaries as well as by
        giving an output file path and the two optional arguments described below.

        The oDSSubs variable, if supplied, should contain a list of integers or NoneTypes equal in length to the number of headers in the output
        data.  Each integer is used to susbstitute information from the output data structures into the original data line at that column number.
        If the integer "-1" is supplied, the data is skipped and never written.
        If ODSSubs is None, all data is simply appended to the line, and each NoneType entry has the same behavior as well.

        The customStratifyingNames variable, if supplied, should contain a list of dictionaries to convert keys to the desired string output.
        If not none, the list should have as many entries as layers in the output data structure, but any given entry can be "None" to indicate
        that naming should just use the keys using the basic formatting.

        The getCountDerivatives object is a function that gets additional counts not explicitly defined within the output data structure.
        For example, the counts for both strands combined or both strands combined and aligned during dyad position counting.
        Within the function definition, two parameters: outputDataWriter and getHeaders, should be present.
        If getHeaders is true, the headers for the new data columns are returned instead of the counts.
        All return types should be lists of strings so they can be directly written to the output file using join.
        Also, MAKE SURE that the returned list, whether getHeaders is true or false, is always the SAME LENGTH.
        If not assigned, the default function simply returns an empty list.
        """

        self.outputDataStructure = outputDataStructure
        self.outputDataStratifiers: List[OutputDataStratifier] = outputDataStratifiers
        self.outputFilePath = outputFilePath
        self.outputFile = open(outputFilePath, 'w')

        self.oDSSubs = oDSSubs
        self.customStratifyingNames = customStratifyingNames
        self.currentDataRow = None
        self.previousKeys = [None]*(len(self.outputDataStratifiers) - 1)

        # Do some input checking...
        assert self.customStratifyingNames is None or len(self.customStratifyingNames) == len(self.outputDataStratifiers), (
            "Output data has "+str(len(self.outputDataStratifiers))+" stratifiers, but customStratifyingNames is a dictionary of length "
            ""+str(len(self.customStratifyingNames))+".  These values should be equal."
        )

        assert self.oDSSubs is None or self.outputFilePath.endswith(".bed"), (
            "oDSSubs were given, but the given output file path is not bed formatted."
        )

        # Set up getCountDerivatives
        if getCountDerivatives is None:
            self.getCountDerivativesFunc = lambda outputDataWriter, getHeaders: list()
        else: self.getCountDerivativesFunc = getCountDerivatives

        # Obtain headers (checks oDSSubs for valid input as well)
        self.headers = self.getHeaders()


    def __del__(self):
        """
        Make sure the output file is closed 
        """
        self.outputFile.close()


    def getCountDerivatives(self, getHeaders):
        """
        A simple wrapper for the passed getCountDerivatives function
        """
        return self.getCountDerivativesFunc(self, getHeaders)


    def getHeaders(self):
        """
        Returns a list of the headers for the output data.
        """

        headers = list()
        if len(self.outputDataStratifiers) > 1:
            for outputDataStratifier in self.outputDataStratifiers[:-1]:
                headers.append(outputDataStratifier.outputName)
                for supplementalInfoHandler in outputDataStratifier.supplementalInfoHandlers:
                    headers.append(supplementalInfoHandler.outputName)
        if len(self.outputDataStratifiers) > 0:
            for key in self.outputDataStratifiers[-1].getKeysForOutput():
                headers.append(self.getOutputName(-1, key))

        headers += self.getCountDerivatives(True)

        assert self.oDSSubs is None or len(self.oDSSubs) == len(headers), (
            "Output data has "+str(len(headers))+" levels, but ODSSubs is a list of length "+str(len(self.oDSSubs))+".  "
            "These values should be equal."
        )

        return headers


    def setDataCol(self, dataLevel, value):
        """
        Updates self.currentDataRow using the given data level and value, taking into account oDSSubs.
        """

        if self.oDSSubs is None:
            self.currentDataRow[dataLevel] = value
        elif self.oDSSubs[dataLevel] == -1:
            pass
        elif self.oDSSubs[dataLevel] is None:
            self.currentDataRow[self.oDSSubs[:dataLevel].count(None)] = value
        else: self.currentDataRow[0][self.oDSSubs[dataLevel]] = value


    def getOutputName(self, stratificationLevel, key):
        """
        A convenience function for getting output names from keys based on the customStratifyingNames parameter.
        """

        if (self.customStratifyingNames is None 
            or self.customStratifyingNames[stratificationLevel] is None 
            or key not in self.customStratifyingNames[stratificationLevel]):
            return self.outputDataStratifiers[stratificationLevel].formatKeyForOutput(key)
        else: return self.customStratifyingNames[stratificationLevel][key]

    def writeDataRows(self, currentDataObject, stratificationLevel, supplementalInfoCount):
        """
        Uses the self.currentDataRow object to recursively write all possible data rows that can be constructed using information at or below
        the given stratification level for a given data object (dictionary) at that same stratification level.
        """

        # If we're not at the final level of the data structure, iterate through it, recursively calling this function on the results.
        if stratificationLevel + 1 != len(self.outputDataStratifiers):
            for key in self.outputDataStratifiers[stratificationLevel].getKeysForOutput():

                self.setDataCol(stratificationLevel + supplementalInfoCount, self.getOutputName(stratificationLevel, key))
                self.previousKeys[stratificationLevel] = key

                supplementalInfoHandlers = self.outputDataStratifiers[stratificationLevel].supplementalInfoHandlers
                for i, supplementalInfoHandler in enumerate(supplementalInfoHandlers):
                    supplementalInfo = supplementalInfoHandler.getFormattedOutput(currentDataObject[key][SUP_INFO_KEY][i])
                    self.setDataCol(stratificationLevel + supplementalInfoCount + i + 1, supplementalInfo)

                self.writeDataRows(currentDataObject[key], stratificationLevel + 1, supplementalInfoCount + len(supplementalInfoHandlers))

        # Otherwise, add the entries in this dictionary (which should be integers representing counts) to the data row 
        # along with any count derivatives and write the row.
        else:
            for i, key in enumerate(self.outputDataStratifiers[stratificationLevel].getKeysForOutput()):
                self.setDataCol(stratificationLevel + supplementalInfoCount + i, str(currentDataObject[key]))
            self.currentDataRow[stratificationLevel + supplementalInfoCount + i + 1:] = self.getCountDerivatives(False)
            if isinstance(self.currentDataRow[0],list):
                self.outputFile.write('\t'.join(['\t'.join(self.currentDataRow[0])] + self.currentDataRow[1:]) + '\n')
            else: self.outputFile.write('\t'.join(self.currentDataRow) + '\n')


    def writeFeature(self, featureToWrite: Union[EncompassingData, EncompassedData]):
        """
        Writes individual features as they cease to be tracked instead of all at once at the end.  (Should be more memory efficient)
        Also, this method preserves bed formatting for those features if the output file has the .bed extension.
        """

        # If we are preserving bed format, prepare the data row based on the number of headers, taking
        # into account any ODSSubs.
        if self.outputFilePath.endswith(".bed"):
            self.currentDataRow = [featureToWrite.choppedUpLine.copy()]
            if self.oDSSubs is None: self.currentDataRow += [None] * (len(self.headers) - 1)
            else: self.currentDataRow += [None] * (self.oDSSubs.count(None) - 1)
        # Otherwise, set up the data row with the "featureToWrite" in the first column.
        else:
            self.currentDataRow = [None] * len(self.headers)
            self.currentDataRow[0] = self.outputDataStratifiers[0].formatKeyForOutput(featureToWrite)

        # Check for any supplemental information at the first stratification level.
        supplementalInfoHandlers = self.outputDataStratifiers[0].supplementalInfoHandlers
        for i, supplementalInfoHandler in enumerate(supplementalInfoHandlers):
            supplementalInfo = supplementalInfoHandler.getFormattedOutput(self.outputDataStructure[featureToWrite][SUP_INFO_KEY][i])
            self.setDataCol(i + 1, supplementalInfo)

        self.writeDataRows(self.outputDataStructure[featureToWrite], 1, len(supplementalInfoHandlers))


    def finishIndividualFeatureWriting(self):
        """
        Sorts the results of individual feature writing, as features are not guaranteed to be written in the same order
        as the input files.
        """
        self.outputFile.close()


    def writeResults(self):
        """
        Writes the results of the output data structure to a given file.  (All at once)
        """

        # Account for the base case of just counting everything.
        if len(self.outputDataStratifiers) == 0: self.outputFile.write(str(self.outputDataStructure) + '\n')

        else:

            # Write headers.
            self.outputFile.write('\t'.join(self.headers) + '\n')

            # Next, write the rest of the data using the recursive writeDataRows function
            self.currentDataRow = [None]*(len(self.headers))

            self.writeDataRows(self.outputDataStructure, 0, 0)

        self.outputFile.close()