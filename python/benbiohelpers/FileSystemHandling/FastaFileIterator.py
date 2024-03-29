from typing import IO, List

#Returns a list of sequence identifiers from a fasta name resulting from the bedtools "getfasta" command.  
#The returned list contains chromosome, start pos, end pos, and strand, if present, in that order)
def parseFastaDescription(fastaSequenceName: str):
    """
    Returns a list of sequence identifiers from a fasta name resulting from the bedtools "getfasta" command.  
    The returned list contains chromosome, start pos, end pos, and strand, if present, in that order)
    E.g. Chr1:51-52(-) will become a list like this: ["Chr1", "51", "52", "-"]
    """

    # Remove the leading '>' if necessary.
    if fastaSequenceName.startswith('>'): fastaSequenceName = fastaSequenceName[1:]

    # Get the chromosome. 
    # (The split result is taken from the rear in case there is a leading bedtools formatted name, which is separated by '::')
    splitSequence = fastaSequenceName.split(':')
    chromosome = splitSequence[-2]
    theRest = splitSequence[-1]

    # Get the strand. 'theRest' should look something like: 123-456(+) or 123-456() or 123-456
    if not '(' in theRest or theRest[-2] == '(': strand = None
    else: 
        strand = theRest[-2]
        if not strand in ('+','-','.'):
            raise ValueError("Error.  Unexpected symbol \'" + strand + "\' found where strand designation was expected.")
    theRest = theRest.split('(')[0]

    # Get the nucleotide positions. ('theRest' should look something like: 123-456)
    splitSequence = theRest.split('-')
    startPos = splitSequence[0]
    endPos = splitSequence[1]

    return (chromosome, startPos, endPos, strand)


# Parses fasta files one entry at a time.
# Designed to work with output from the bedtools getfasta function.
class FastaFileIterator:
    """
    Parses fasta files one entry at a time.
    Designed to work with output from the bedtools getfasta function.

    Usage:
        `for fastaEntry in FastaFileIterator(openFastaFile):`
    """


    # The object to hold information on each entry.
    class FastaEntry:
        def __init__(self, sequenceLocation: List[str], sequence: str, sequenceName: str):
            self.sequenceLocation = sequenceLocation # The list containing all the relevant information to locate 
                                                     # The fasta sequence in a given genome.
            self.sequenceName = sequenceName # The full fasta sequence header, without the angle bracket.

            # The information relevant to finding the sequence in the genome.
            self.chromosome = sequenceLocation[0]
            self.startPos = sequenceLocation[1]
            self.endPos = sequenceLocation[2]
            self.strand = sequenceLocation[3]

            self.sequence = sequence # The DNA sequence itself

        def formatForWriting(self):
            """
            Reverses the fasta entry creation process to produce a string that can be rewritten to a file.
            """
            fastaStringForWriting = f">{self.sequenceName}\n"
            i = 0
            while i < len(self.sequence):
                fastaStringForWriting += self.sequence[i:i+50] + '\n'
                i += 50
            return fastaStringForWriting


    # Initialize the FastaFileIterator with an open fasta file object.
    def __init__(self, fastaFile: IO, containsLocationInformation = True):
        self.fastaFile = fastaFile # The file that will be parsed and read through.
        self.containsLocationInformation = containsLocationInformation # Whether or not the fasta file contains full
                                                                       # sequence location information
        self.eof = False # A flag for when the end of the file has been reached.

        # Initialize the iterator with the first entry.
        self.nextSequenceName = self.fastaFile.readline().strip()[1:]
        # If the file is empty (and thus, the first line is blank) set the eof flag to true.
        if not self.nextSequenceName: self.eof = True


    # Reads in the next fasta entry and returns it.
    def readEntry(self):

        # Return None if we've reached the end of the file.
        if self.eof: return None

        # Get the name for the upcoming sequence.
        sequenceName = self.nextSequenceName

        # Get the sequence location for the current entry (if available).
        if self.containsLocationInformation: 
            sequenceLocation = parseFastaDescription(sequenceName)
        else: sequenceLocation = (None,None,None,None)

        # Read through lines until we get to the next entry, adding to the sequence as we go.
        line = self.fastaFile.readline().strip()
        sequence = ''

        while not line.startswith('>'):

            sequence += line.upper()

            line = self.fastaFile.readline().strip()

            if not line:
                self.eof = True
                break

        # Prep for the next entry if we aren't at eof.
        if not self.eof:
            self.nextSequenceName = line[1:]

        # Return the current fasta entry.
        return self.FastaEntry(sequenceLocation, sequence, sequenceName)


    # Make the class iteratable, returning each fasta entry one at a time.
    def __iter__(self):
        return self
    def __next__(self):

        # Make sure we haven't reached the end of the file.
        if self.eof: raise StopIteration

        return self.readEntry()