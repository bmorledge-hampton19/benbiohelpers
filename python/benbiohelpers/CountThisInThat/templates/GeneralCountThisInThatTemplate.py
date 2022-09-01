# Lots of messy imports, I know, but they should contain most of what you need. Delete/add as needed.
from benbiohelpers.CountThisInThat.Counter import ThisInThatCounter, CounterOutputDataHandler
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import OutputDataWriter, AmbiguityHandling
from benbiohelpers.CountThisInThat.InputDataStructures import (EncompassedData, EncompassingData,
                                                               ENCOMPASSED_DATA, ENCOMPASSING_DATA)
from benbiohelpers.CountThisInThat.SupplementalInformation import SimpleColumnSupInfoHandler

"""
Here is an example of how to modify a basic EncompassingData input structure.
In this case, the start and end positions are changed when setting location data.
"""
class GeneAnnotationData(EncompassingData):

    def setLocationData(self, acceptableChromosomes):
        
        self.chromosome = self.choppedUpLine[0] # The chromosome that houses the feature.
        self.startPos = float(self.choppedUpLine[3]) # The start position of the feature in its chromosome. (0 base)
        self.endPos = float(self.choppedUpLine[4]) - 1 # The end position of the feature in its chromosome. (0 base)
        self.center = (self.startPos + self.endPos) / 2 # The average (center) of the start and end positions.  (Still 0 base)
        self.strand = self.choppedUpLine[5] # Either '+' or '-' depending on which strand houses the mutation.

        # Make sure the mutation is in a valid chromosome.
        if acceptableChromosomes is not None and self.chromosome not in acceptableChromosomes:
            raise ValueError(self.chromosome + " is not a valid chromosome for this genome.")


"""
Each counter should extend the ThisInThatCounter and define at least the following three methods: initOutputDataHandler,
setupOutputDataStratifiers, and setupOutputDataWriter. Each are described in detail below. Additionally, this is a good
place to define a getCountDerivatives function, if desired.
"""
class ExonChecker(ThisInThatCounter):

    def getCountDerivatives(outputDataWriter: OutputDataWriter, getHeaders):
        """
        Used to derive separate counts or other values from the normally outputted counts.
        For example: Getting the counts across both strands by combining counts on the plus or minus strand
        or even categorizing data rows by counts and including that categorization in its own column. (This
        is also good for categorizing data based on whether or not they were encompassed or not in the first place.)
        """
        if getHeaders: return ["Exon_Or_Intron"]
        else:
            if outputDataWriter.outputDataStructure[outputDataWriter.previousKeys[0]][None]: return ["Exon"]
            else: return ["Intron"]

    def initOutputDataHandler(self):
        """
        Use this function to create the instance of the CounterOutputDataHandler object.
        Default behavior creates the output data handler and passes in the counter's "writeIncrementally" value.
        """
        self.outputDataHandler = CounterOutputDataHandler(self.writeIncrementally, trackAllEncompassed = True)


    def setupOutputDataStratifiers(self):
        """
        Use this function to set up any output data stratifiers for the output data handler.
        Default behavior sets up no stratifiers.
        """
        self.outputDataHandler.addEncompassedFeatureStratifier()
        self.outputDataHandler.addPlaceholderStratifier()


    def setupOutputDataWriter(self):
        """
        Use this funciton to set up the output data writer.
        Default behavior creates the output data writer with the counter's "outputFilePath" value
        """
        self.outputDataHandler.createOutputDataWriter(self.outputFilePath, getCountDerivatives=ExonChecker.getCountDerivatives,
                                                      oDSSubs = [None, 10], omitFinalStratificationCounts = True)


"""
Here is an example of creating and running the new counter:
Note that if the output file path has the ".bed" extension, the output will preserve bed formatting
based on the first output data stratifier (encompassing vs. encompassed data file).
"""
def runMyCounter():
    exonChecker = ExonChecker("encompassed/file/path", "encompassing/file/path", "output/file/path")
    exonChecker.count()