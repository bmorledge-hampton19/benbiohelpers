# This script takes a bed file and genome fasta file, converts the positions in each bed line to their DNA sequence,
# And writes the sequence to the bed file at a specified position.
from benbiohelpers.FileSystemHandling.BedToFasta import bedToFasta
from benbiohelpers.FileSystemHandling.FastaFileIterator import FastaFileIterator
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory

import os

def addSequenceToBed(bedFilePath: str, genomeFastaFilePath: str, substitutionPosition = None, verbose = False):
    """
    Add fasta sequences to the bed file for each line.  The sequences are substituted in at the given "substitutionPosition" column
    if a value is supplied, or they are appended to a new column if it is None.
    """

    # Get the names of intermediate files from the bed file name.
    fastaSequencesFilePath = bedFilePath.rsplit('.',1)[0] + "_sequences.fa"
    newBedFilePath = bedFilePath.rsplit('.',1)[0] + "_NEW.bed"

    # Generate the fasta sequences file.
    if verbose: print("Generating fasta sequences file...")
    bedToFasta(bedFilePath, genomeFastaFilePath, fastaSequencesFilePath)

    # Open both the fasta sequence file and original bed file to read from and the new bed file to write to.
    if verbose: print("Writing fasta sequences to new bed file...")
    with open(bedFilePath, 'r') as bedFile:
        with open(fastaSequencesFilePath, 'r') as fastaSequencesFile:
            with open(newBedFilePath, 'w') as newBedFile:

                fastaFileIterator = FastaFileIterator(fastaSequencesFile)

                # For every line in the bed file, grab it and the accompanying fasta sequence and write them to the new file!
                for fastaEntry in fastaFileIterator:

                    bedColumns = bedFile.readline().split()
                    fastaSequence = fastaEntry.sequence
                    assert bedColumns, "No bed line found to accompany fasta sequence: " + fastaSequence

                    if substitutionPosition is None: bedColumns.append(fastaSequence)
                    else: bedColumns[substitutionPosition] = fastaSequence

                    newBedFile.write('\t'.join(bedColumns) + '\n')

                # Make sure the files had the same number of lines.
                checkBedFile = bedFile.readline()
                assert not checkBedFile, "Extra bed line found: " + checkBedFile

    # Clean up files by deleting the intermediate sequences file and replacing the old bed file with the new one.
    print("Success!  Deleting intermediate fasta sequences file and replacing old bed file...")
    os.remove(fastaSequencesFilePath)
    os.replace(newBedFilePath, bedFilePath)


def main():

    # Create the Tkinter UI
    dialog = TkinterDialog(workingDirectory=getDataDirectory())
    dialog.createFileSelector("Bed File:",0,("Bed Files",".bed"))    
    dialog.createFileSelector("Genome Fasta File:",1,("Fasta Files",".fa"))

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    addSequenceToBed(dialog.selections.getFilePaths()[0], dialog.selections.getFilePaths()[1], 4, True)


if __name__ == "__main__": main()