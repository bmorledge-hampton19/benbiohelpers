# This script features a class which iterates through Sam file objects.
from typing import IO, List, Dict
from benbiohelpers.DNA_SequenceHandling import reverseCompliment

reverseComplimentTranslator = str.maketrans("ACTGactg","TGACtgac")

class SamFileIterator:
    """
    Parses sam files one read at a time.
    Designed to work with output from bowtie2.
    """


    class SamHeader:
        """
        Holds information on headers (basically a glorified string)
        """

        def __init__(self, header: str):
            self.header = header


    class SamRead:
        """
        Holds information on each parsed sam read.
        """

        THREE_PRIME = 3
        FIVE_PRIME = 5

        def __init__(self, readName: str, readSequence: str, qualityString: str,
                     referenceSequence: str = None, referenceSequenceLocation: List[str] = None,
                     readAlignmentSeq: str = None, referenceAlignmentSeq: str = None):
            self.referenceSequenceLocation = referenceSequenceLocation # The list containing all the relevant information to locate 
                                                                       # The read sequence in a given genome.

            # The information relevant to finding the sequence in the genome.
            if self.referenceSequenceLocation is not None:
                self.chromosome = referenceSequenceLocation[0]
                self.startPos = int(referenceSequenceLocation[1]) # 1-based
                self.endPos = int(referenceSequenceLocation[2]) # 1-based
                self.strand = referenceSequenceLocation[3]
            else:
                self.chromosome = None
                self.startPos = None
                self.endPos = None
                self.strand = None

            self.readName = readName # The read name/ID
            self.readSequence = readSequence # The sequence of the read
            self.referenceSequence = referenceSequence # The reference sequence the read aligned to. (None if no alignment)
            self.qualityString = qualityString # Phred-scaled quality scores encoded as ASCII characters.

            self.readAlignmentSeq = readAlignmentSeq
            self.referenceAlignmentSeq = referenceAlignmentSeq


        def getAlignmentString(self):
            """
            Get the two alignment sequences formatted in parallel as a 2-line string.
            Returns None if no alignment was found.
            """
            if self.readAlignmentSeq is None: return None

            return (f"Read:      {self.readAlignmentSeq}\n"
                    f"Reference: {self.referenceAlignmentSeq}")


        def getMismatches(self, orientation = FIVE_PRIME):
            """
            Returns a dictionary of mismatch positions (keys) and sequences (values).
            Positions can be given relative to the 5' (positive) or 3' (negative) end.
            Positions are given relative to the ungapped read sequence.
            Returns None if no alignment was found.
            """
            if self.readAlignmentSeq is None: return None

            mismatches = dict()
            readAlignmentGaps = 0
            if orientation == self.FIVE_PRIME: loopRange = range(len(self.readAlignmentSeq))
            else: loopRange = range(-1, -len(self.readAlignmentSeq)-1, -1)
            for i in loopRange:
                readChar = self.readAlignmentSeq[i]
                referenceChar = self.referenceAlignmentSeq[i]
                if (readChar != '-' and referenceChar != '-' and readChar != referenceChar):
                    if orientation == self.FIVE_PRIME: mismatches[i+1-readAlignmentGaps] = referenceChar.upper() + '>' + readChar
                    else: mismatches[i+readAlignmentGaps] = referenceChar.upper() + '>' + readChar
                elif readChar == '-': readAlignmentGaps += 1
            return mismatches


        def formatForFastaOutput(self, readSequence = True):
            """
            Formats and returns the sam read as an entry in a fasta file.
            By default, uses the read sequence, but if the related parameter is set to False, uses the reference sequence
            the read aligned to.
            """
            fastaStringForWriting = f">{self.chromosome}:{self.startPos}-{self.endPos}({self.strand})\n"
            i = 0
            if readSequence: sequence = self.readSequence
            else: sequence = self.referenceSequence
            while i < len(sequence):
                fastaStringForWriting += sequence[i:i+50] + '\n'
                i += 50
            return fastaStringForWriting


        def formatForBedOutput(self):
            """
            Formats and returns the sam read as a line in a bed file.
            """
            return '\t'.join((self.chromosome, str(self.startPos-1), str(self.endPos), '.', '.', str(self.strand))) + '\n'


    # Initialize the SamFileIterator with an open sam file object.
    def __init__(self, samFile: IO, skipHeaders = True, skipUnaligned = False, skipIndels = False):
        """
        Takes an open file IO object. Headers can be skipped if desired (True by default).
        """

        self.samFile = samFile # The file that will be parsed and read through.
        self.skipHeaders = skipHeaders # Whether or not to skip the initial header lines (lines preceded by '@')
        self.skipUnaligned = skipUnaligned # Whether or not to skip reads that didn't align to the reference genome.
        self.skipIndels = skipIndels # Whether or not to skip reads that aligned with insertions or deletions.


    # Reads in the next same read (or header) and returns it.
    def parseRead(self):

        # Determine if this is a header line. If it is, return/skip as necessary.
        if self.thisRead.startswith('@'):
            if self.skipHeaders: return self.__next__()
            else: return self.SamHeader(self.thisRead.strip())

        splitLine = self.thisRead.split()

        # Retrieve the read name, sequence, and quality string.
        readName = splitLine[0]
        readSequence = splitLine[9]
        qualityString = splitLine[10]

        # If the read didn't align, we already have all the relevant information.
        # Create the SamRead object and return it (unless skipping unaligned reads)!
        if splitLine[5] == '*': 
            if self.skipUnaligned: return self.__next__()
            else: return self.SamRead(readName, readSequence, qualityString)

        # Find the XM and MD fields and derive information about mismatches from them.
        if splitLine[13].startswith("XM"):
            mismatchCount = int(splitLine[13].rsplit(':',1)[1])
            assert splitLine[17].startswith("MD"), f"MD field not found at expected location:\n{self.thisRead}"
            mismatchDesignations = splitLine[17].rsplit(':',1)[1]

        elif splitLine[14].startswith("XM"): 
            mismatchCount = int(splitLine[14].rsplit(':',1)[1])
            assert splitLine[18].startswith("MD"), f"MD field not found at expected location:\n{self.thisRead}"
            mismatchDesignations = splitLine[18].rsplit(':',1)[1]

        else: raise ValueError(f"XM field not at expected position:\n{self.thisRead}")

        # Get the cigar string.
        cigarString = splitLine[5]

        # Determine if the read sequence should actually be the reverse complement.
        readSequence = splitLine[9]
        isReverseCompliment = bool(int(splitLine[1]) & 0b10000)
        if isReverseCompliment: strand = '-'
        else: strand = '+'

        # Get information on the reference sequence location.
        chromosome = splitLine[2]
        startPos = int(splitLine[3]) - 1

        # If there are indels, check whether those are even allowed, skipping if not.
        if self.skipIndels and ('I' in cigarString or 'D' in cigarString): return self.__next__()

        # If there are no mismatches and no indels, we skip the next steps (which are icky anyway) and just
        # write the read/reference as is!
        if mismatchCount == 0 and not ('I' in cigarString or 'D' in cigarString):
            if isReverseCompliment: readSequence = reverseCompliment(readSequence)
            return self.SamRead(readName, readSequence, qualityString, readSequence,
                                [chromosome, startPos, startPos + len(readSequence), strand],
                                readSequence, readSequence)


        # Next, use the CIGAR and mismatch designations (MD) strings to reproduce the alignment.
        readAlignmentPieces = list()
        referenceAlignmentPieces = list()
        readPos = 0
        mdi = 0 # mismatch designation index
        leftoverMatches = 0

        # Break the cigar string up into its individual components (number-alpha pairs) than loop through them.
        cigarAlphaPositions = [i for i,char in enumerate(cigarString) if char.isalpha()]
        lastCigarAlphaPosition = -1
        for cigarAlphaPosition in cigarAlphaPositions:
            cigarNumber = int(cigarString[lastCigarAlphaPosition+1:cigarAlphaPosition])
            cigarAlpha = cigarString[cigarAlphaPosition]

            # If the cigar position is an 'M', use the mismatch designations string to find the 
            # relevant matches/mismatches.
            if cigarAlpha == 'M':

                # It's possible that 1 group of matches in the mismatch designations string spans multiple CIGAR 'M'
                # values split up by I values (Ugh), so make sure to keep track of how many M values need to be read
                # in case we need to stop to parse those I values.
                remainingMs = cigarNumber
                while remainingMs > 0:

                    # If there are no matches leftover from a previous M value, see if the next entry in the mismatch
                    # designations string is an alpha (mismatched nucleotide) character. If so, parse it accordingly.
                    if leftoverMatches == 0 and mismatchDesignations[mdi].isalpha():
                        readAlignmentPieces.append(readSequence[readPos])
                        referenceAlignmentPieces.append(mismatchDesignations[mdi].lower())
                        readPos += 1
                        mdi += 1
                        remainingMs -= 1

                    # If there are no matches leftover from a previous M value, and the next entry in the mismatch
                    # designations string wasn't an alpha, it must be a number of matches. Parse accordingly, and 
                    # set this value as the number of leftover matches.
                    elif leftoverMatches == 0:
                        matchNumberString = ''
                        while mismatchDesignations[mdi:mdi+1].isnumeric():
                            matchNumberString += mismatchDesignations[mdi]
                            mdi += 1
                        leftoverMatches = int(matchNumberString)

                    # If we do have matches leftover and they meet or exceed the remaining M value, we
                    # can use the read sequence to get the remaining nucleotides for both alignments.
                    elif leftoverMatches >= remainingMs:
                        readAlignmentPieces.append(readSequence[readPos:readPos+remainingMs])
                        referenceAlignmentPieces.append(readSequence[readPos:readPos+remainingMs])
                        readPos += remainingMs
                        leftoverMatches -= remainingMs
                        remainingMs = 0

                    # Lastly, if we have matches leftover but not enough to satisfy the M value, take
                    # what we can and continue parsing.
                    else:
                        readAlignmentPieces.append(readSequence[readPos:readPos+leftoverMatches])
                        referenceAlignmentPieces.append(readSequence[readPos:readPos+leftoverMatches])
                        readPos += leftoverMatches
                        remainingMs -= leftoverMatches
                        leftoverMatches = 0

            # If the cigar position is an "I", add gaps to the reference alignment and add the relevant read
            # bases to the read alignment.
            elif cigarAlpha == 'I':
                referenceAlignmentPieces.append('-'*cigarNumber)
                readAlignmentPieces.append(readSequence[readPos:readPos+cigarNumber])
                readPos += cigarNumber

            # If the cigar position is an "M", add gaps to the read alignment and use the mismatch designations
            # string to find the bases to add to the reference alignment.
            elif cigarAlpha == 'D':
                if mismatchDesignations[mdi] == '0': mdi += 1 # WHY, sam files, WHY?!
                assert mismatchDesignations[mdi] == '^'
                referenceAlignmentPieces.append(mismatchDesignations[mdi+1:mdi+cigarNumber+1])
                readAlignmentPieces.append('-'*cigarNumber)
                mdi += cigarNumber + 1
            else: raise ValueError(f"Unexpected cigar string character {cigarAlpha} in {cigarString}")
            lastCigarAlphaPosition = cigarAlphaPosition

        # Piece together the alignment sequences and derive the reference sequence from its alignment sequence.
        readAlignmentSequence = ''.join(readAlignmentPieces)
        referenceAlignmentSequence = ''.join(referenceAlignmentPieces)
        referenceSequence = referenceAlignmentSequence.replace('-', '').upper()

        # Transform sequences if the actual read sequence is the reverse complement.
        if isReverseCompliment:
            readSequence = reverseCompliment(readSequence)
            referenceSequence = reverseCompliment(referenceSequence)
            # The alignment sequences need to use a translator that is robust to non-nucleotide characters (gaps).
            readAlignmentSequence = readAlignmentSequence.translate(reverseComplimentTranslator)[::-1]
            referenceAlignmentSequence = referenceAlignmentSequence.translate(reverseComplimentTranslator)[::-1]

        # Create and return the SamRead object.
        return self.SamRead(readName, readSequence, qualityString, referenceSequence,
                            [chromosome, startPos, startPos + len(referenceSequence), strand],
                            readAlignmentSequence, referenceAlignmentSequence)


    # Make the class iteratable, returning each parsed sam read one at a time.
    def __iter__(self):
        return self
    def __next__(self):

        # Read in the next line (and make sure a line was actually read in at all)
        self.thisRead: str = self.samFile.readline()
        if not self.thisRead: raise StopIteration
        else: return self.parseRead()
