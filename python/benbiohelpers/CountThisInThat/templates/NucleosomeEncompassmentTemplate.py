# Lots of messy imports, I know, but they should contain most of what you need. Delete/add as needed.
from benbiohelpers.CountThisInThat.Counter import ThisInThatCounter, CounterOutputDataHandler
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import OutputDataWriter, AmbiguityHandling
from benbiohelpers.CountThisInThat.InputDataStructures import (EncompassedData, EncompassingData, EncompassingDataDefaultStrand,
                                                               ENCOMPASSED_DATA, ENCOMPASSING_DATA)
from benbiohelpers.CountThisInThat.SupplementalInformation import SimpleColumnSupInfoHandler


"""
Each counter should extend the ThisInThatCounter and define at least one of the following three methods: initOutputDataHandler,
setupOutputDataStratifiers, and setupOutputDataWriter. Each are described in detail below. Additionally, this is a good
place to define a getCountDerivatives function, if desired.
"""
class MutationsInNucleosomesCounter(ThisInThatCounter):

    def getCountDerivatives(outputDataWriter: OutputDataWriter, getHeaders):
        """
        Used to derive separate counts or other values from the normally outputted counts.
        For example: Getting the counts across both strands by combining counts on the plus or minus strand
        or even categorizing data rows by counts and including that categorization in its own column. (This
        is also good for categorizing data based on whether or not they were encompassed or not in the first place.)
        """
        if getHeaders: return ["Both_Strands_Counts", "Aligned_Strands_Counts"]
        else:
            thisPlusCounts = outputDataWriter.outputDataStructure[outputDataWriter.previousKeys[0]][True]
            thisMinusCounts = outputDataWriter.outputDataStructure[outputDataWriter.previousKeys[0]][False]
            oppositeMinusCounts = outputDataWriter.outputDataStructure[-outputDataWriter.previousKeys[0]][False]
            return [str(thisPlusCounts+thisMinusCounts),str(thisPlusCounts+oppositeMinusCounts)]

    def initOutputDataHandler(self):
        """
        Use this function to create the instance of the CounterOutputDataHandler object.
        Default behavior creates the output data handler and passes in the counter's "writeIncrementally" value.
        (In this case, the function doesn't do anything beyond the default and could be omitted entirely.)
        """
        super().initOutputDataHandler()


    def setupOutputDataStratifiers(self):
        """
        Use this function to set up any output data stratifiers for the output data handler.
        Default behavior sets up no stratifiers.
        """
        self.outputDataHandler.addRelativePositionStratifier(self.currentEncompassingFeature, extraRangeRadius = self.encompassingFeatureExtraRadius,
                                                             outputName = "Dyad_Position")
        self.outputDataHandler.addStrandComparisonStratifier(strandAmbiguityHandling = AmbiguityHandling.tolerate)


    def setupOutputDataWriter(self):
        """
        Use this funciton to set up the output data writer.
        Default behavior creates the output data writer with the counter's "outputFilePath" value
        """
        self.outputDataHandler.createOutputDataWriter(self.outputFilePath, customStratifyingNames=(None, {True:"Plus_Strand_Counts", False:"Minus_Strand_Counts"}),
                                                      getCountDerivatives = self.getCountDerivatives)


"""
Here is an example of creating and running the new counter:
Note that if the output file path has the ".bed" extension, the output will preserve bed formatting
based on the first output data stratifier (encompassing vs. encompassed data file).
"""
def runMyCounter():
    counter = MutationsInNucleosomesCounter("mutations/file/path", "nucleosomes/file/path", "output/file/path", 
                                            encompassingFeatureExtraRadius=73, acceptableChromosomes=["chr1","chr2"])
    counter.count()