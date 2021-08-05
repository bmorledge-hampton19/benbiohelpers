# This script contains two data objects that represent the inputs from two files in the related "ThisInThatCounter".
# These objects are meant to be inherited from and overridden as necessary.

ENCOMPASSED_DATA = 1
ENCOMPASSING_DATA = 2

class EncompassedData:
    """
    Stores data on each of the features that are expected to be encompassed by the second feature 
    e.g. this could be for mutations that are expected to be encompassed by nucleosomes
    """
    def __init__(self, line: str, acceptableChromosomes):

        # Read in the next line.
        self.choppedUpLine = line.strip().split()

        self.setLocationData(acceptableChromosomes)
        self.setOtherData()

    def __key(self):
        return (self.chromosome, self.position, self.strand)

    def __hash__(self) -> int:
        return hash(self.__key())

    def __eq__(self, other) -> bool:
        return (self.__key()) == (other.__key())

    # NOTE: Does not take into account strand.
    def __lt__(self, other) -> bool:
        return (self.__key()[:2]) < (other.__key()[:2])

    def setLocationData(self, acceptableChromosomes):
        """
        Sets the chromosome, position, and strand of the feature.
        Also checks to make sure the chromosome is acceptable.  
        If acceptableChromosomes is None, all chromosomes are accepted.  Yes, it's counterintuitive.  Sorry.
        """

        self.chromosome = self.choppedUpLine[0] # The chromosome that houses the feature.
        self.position = (float(self.choppedUpLine[1]) + float(self.choppedUpLine[2]) - 1) / 2 # The center of the feature in its chromosome. (0 base)
        self.strand = self.choppedUpLine[5] # Either '+' or '-' depending on which strand houses the mutation.

        # Make sure the mutation is in a valid chromosome.
        if acceptableChromosomes is not None and self.chromosome not in acceptableChromosomes:
            raise ValueError(self.chromosome + " is not a valid chromosome for this genome.")

    def getLocationString(self):
        return self.chromosome + ':' + str(self.position) + '(' + self.strand + ')'

    def setOtherData(self):
        """
        Sets any other data not directly pertaining to location
        """
        self.matchesEncompassingDataStrand = None # Whether or not the strand on the encompassing data matches this data's strand.
        self.positionRelativeToEncompassingData = None # The position of the encompassed feature within the encompassing feature.
        self.encompassingFeature: EncompassingData = None # The feature encompassing this feature.

        self.ambiguousStrandMatching = False # Whether or not there is ambiguity due to different strands on multiple encompassing data features.
        self.ambiguousRelativePos = False # Whether or not there is ambiguity due to different relative positions on multiple encompassing data features.
        self.ambiguousEncompassingFeature = False # Whether or not there is ambiguity due to multiple encompassing features.

        self.finishedTracking = False # Changes to true when there is certainty that this object will not be updated again.


class EncompassedDataWithContext(EncompassedData):
    """
    Much like its parent class, except it expects information on the context of the feature to be 
    present in the 4th column of the file and information on the alteration in the 5th column.
    """

    def setLocationData(self, acceptableChromosomes):
        super().setLocationData(acceptableChromosomes)
        self.context = self.choppedUpLine[3]
        self.alteredTo = self.choppedUpLine[4]


class EncompassedDataDefaultStrand(EncompassedData):
    """
    An extension of EncompassedData which assumes that the strand is the '+' strand, either because
    the data has no 6th column or that column does not contain strand information (like nucleosome maps)
    """

    def setLocationData(self, acceptableChromosomes):
        self.chromosome = self.choppedUpLine[0] # The chromosome that houses the feature.
        self.position = (float(self.choppedUpLine[1]) + float(self.choppedUpLine[2]) - 1) / 2 # The center of the feature in its chromosome. (0 base)
        self.strand = '+'

        # Make sure the mutation is in a valid chromosome.
        if acceptableChromosomes is not None and self.chromosome not in acceptableChromosomes:
            raise ValueError(self.chromosome + " is not a valid chromosome for this genome.")


class EncompassingData:
    """
    Stores data on each of the features that are expected to be encompass the first feature
    e.g. this could be for the nucleosomes that are expected to encompass mutations.
    """
    def __init__(self, line: str, acceptableChromosomes):

        # Read in the next line.
        self.choppedUpLine = line.strip().split()

        self.setLocationData(acceptableChromosomes)
        self.setOtherData()

    def __key(self):
        return (self.chromosome, self.startPos, self.endPos, self.strand)

    def __hash__(self) -> int:
        return hash(self.__key())

    def __eq__(self, other) -> bool:
        return (self.__key()) == (other.__key())

    # NOTE: Does not take into account strand.
    def __lt__(self, other) -> bool:
        return (self.__key()[:3]) < (other.__key()[:3])

    def setLocationData(self, acceptableChromosomes):
        """
        Sets the chromosome, position, and strand of the feature.
        Also checks to make sure the chromosome is acceptable.  
        If acceptableChromosomes is None, all chromosomes are accepted.  Yes, it's counterintuitive.  Sorry.
        """

        self.chromosome = self.choppedUpLine[0] # The chromosome that houses the feature.
        self.startPos = float(self.choppedUpLine[1]) # The start position of the feature in its chromosome. (0 base)
        self.endPos = float(self.choppedUpLine[2]) - 1 # The end position of the feature in its chromosome. (0 base)
        self.center = (self.startPos + self.endPos) / 2 # The average (center) of the start and end positions.  (Still 0 base)
        self.strand = self.choppedUpLine[5] # Either '+' or '-' depending on which strand houses the mutation.

        # Make sure the mutation is in a valid chromosome.
        if acceptableChromosomes is not None and self.chromosome not in acceptableChromosomes:
            raise ValueError(self.chromosome + " is not a valid chromosome for this genome.")

    def setOtherData(self):
        pass

    def getLocationString(self):
        return self.chromosome + ':' + str(self.startPos) + '-' + str(self.endPos) + '(' + self.strand + ')'

class EncompassingDataDefaultStrand(EncompassingData):
    """
    An extension of EncompassingData which assumes that the strand is the '+' strand, either because
    the data has no 6th column or that column does not contain strand information (like nucleosome maps)
    """

    def setLocationData(self, acceptableChromosomes):

        self.chromosome = self.choppedUpLine[0] # The chromosome that houses the feature.
        self.startPos = float(self.choppedUpLine[1]) # The start position of the feature in its chromosome. (0 base)
        self.endPos = float(self.choppedUpLine[2]) - 1 # The end position of the feature in its chromosome. (0 base)
        self.center = (self.startPos + self.endPos) / 2 # The average (center) of the start and end positions.  (Still 0 base)
        self.strand = '+'

        # Make sure the mutation is in a valid chromosome.
        if acceptableChromosomes is not None and self.chromosome not in acceptableChromosomes:
            raise ValueError(self.chromosome + " is not a valid chromosome for this genome.")

class TfbsData(EncompassingData):
    """
    Like encompassing data, but with the name of the transcription factor binding site.
    """

    def setOtherData(self):
        self.tfbsName = self.choppedUpLine[6] # Might need to change the column number here...
