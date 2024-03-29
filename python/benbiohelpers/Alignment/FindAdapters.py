# This script takes a set of potential adapter sequences and a fastq file and
# determines which adapters are enriched in the reads.
import os, gzip
from typing import List, Dict, TextIO
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs, getIsolatedParentDir
from benbiohelpers.FileSystemHandling.FastaFileIterator import FastaFileIterator
from benbiohelpers.FileSystemHandling.GetFileSubset import getFastqSubset
from benbiohelpers.InputParsing.CheckForNumber import checkForNumber


class NoEnrichedAdapterError(Exception):
    """
    An error class for when no adapters are enriched beyond 0%
    """


def getFastqEntrySequence(fastqFile: TextIO):
    """
    Reads the next four lines in the fastq file and returns the raw sequence (second line).
    """
    fastqFile.readline()
    sequence = fastqFile.readline().strip()
    fastqFile.readline(); fastqFile.readline()
    return sequence

def findAdapters(fastqFilePaths: List[str], adapterFilePath, threshold = 0.01, defaultToMax = True, aggregateOutput = False,
                 searchLengthLimit = None):
    """
    Given one or more fastq files (in a list) and a fasta file of adapter sequences,
    determines which adapters are enriched in each file (using a subset of that file)
    and prints them to a new adapters file in the same directory as the fastq file.
    - Default threshold for adapter enrichment is 5%. If no adapter meets this threshold, and the
    defaultToMax parameter is true, the adapter with the highest enrichment is chosen.
    - If the aggregateOutput parameter is true, all enriched adapters are output to the same file, whose path is
    determined by the the first fastq file path given. (Useful when preparing to trim paired-end data.)
    - searchLengthLimit determines the maximum number of bases in each adapter sequence that are used for exact matching,
    starting from the 5' end.
    """

    # Get the fasta entries from the adapter file.
    adapterFastaEntries: List[FastaFileIterator.FastaEntry] = list()
    with open(adapterFilePath, 'r') as adapterFile:
        for fastaEntry in FastaFileIterator(adapterFile, False):
            adapterFastaEntries.append(fastaEntry)

    adapterSearchSequences: Dict[FastaFileIterator.FastaEntry:str] = dict()
    for adapterFastaEntry in adapterFastaEntries:
        if searchLengthLimit is None: adapterSearchSequences[adapterFastaEntry] = adapterFastaEntry.sequence
        else: adapterSearchSequences[adapterFastaEntry] = adapterFastaEntry.sequence[:searchLengthLimit]


    # Loop through the given fastq files, looking for adapter enrichment in each.
    enrichedAdapters = list()
    enrichedAdapterFilePath = None
    enrichedAdapterWriteMode = None
    enrichedAdapterFilePaths = list()
    for fastqFilePath in fastqFilePaths:

        print(f"\nSearching for enriched adapters in {os.path.basename(fastqFilePath)}...")

        if not aggregateOutput: enrichedAdapters = list()

        # Determine what function will be used to handle file IO
        if fastqFilePath.endswith(".gz"): openFunction = gzip.open
        else: openFunction = open

        # Generate a temporary directory.
        tempDir = os.path.join(os.path.dirname(fastqFilePath),".tmp")
        checkDirs(tempDir)

        # Do some initialization
        totalSequences = 0
        adapterCounts = {fastaEntry:0 for fastaEntry in adapterFastaEntries}

        # Subset the fastq file and open the resulting file path.
        with openFunction(getFastqSubset(fastqFilePath, outputDir=tempDir), "rt") as fastqSubsetFile:

            # Loop through the fastq sequences, looking for the relevant adapter sequences.
            sequence = getFastqEntrySequence(fastqSubsetFile)
            while sequence:
                for fastaEntry in adapterCounts:
                    if adapterSearchSequences[fastaEntry] in sequence: adapterCounts[fastaEntry] += 1
                totalSequences += 1
                sequence = getFastqEntrySequence(fastqSubsetFile)

        # Determine the threshold for adapter enrichment.
        enrichmentThreshold = totalSequences * threshold

        # Write the enriched adapters to a new file.
        foundEnrichedAdapter = False
        if enrichedAdapterFilePath is None or not aggregateOutput:
            enrichedAdapterFilePath: str = os.path.join(os.path.dirname(fastqFilePath), "adapters.fa")
            enrichedAdapterFilePaths.append(enrichedAdapterFilePath)

        if enrichedAdapterWriteMode is None: enrichedAdapterWriteMode = 'w'
        elif aggregateOutput: enrichedAdapterWriteMode = 'a'

        with open(enrichedAdapterFilePath, enrichedAdapterWriteMode) as enrichedAdapterFile:
            for fastaEntry in adapterCounts:
                if adapterCounts[fastaEntry] >= enrichmentThreshold:
                    percentage = adapterCounts[fastaEntry] / totalSequences * 100
                    print(f"Adapter {fastaEntry.sequenceName} is enriched at {percentage}%")
                    foundEnrichedAdapter = True
                    if fastaEntry.sequence not in enrichedAdapters:
                        enrichedAdapterFile.write(fastaEntry.formatForWriting())
                        enrichedAdapters.append(fastaEntry.sequence)
        
            if not foundEnrichedAdapter:
                maxAdapter: FastaFileIterator.FastaEntry = max(adapterCounts, key = adapterCounts.get)
                if adapterCounts[maxAdapter] == 0: raise NoEnrichedAdapterError(f"No adapters are enriched for {os.path.basename(fastqFilePath)}.")
                percentage = adapterCounts[maxAdapter]/totalSequences * 100
                if defaultToMax:
                    print("WARNING: No adapters meet enrichment threshold. "
                        "Adapter with maximum enrichment will be written.")
                    if fastaEntry.sequence not in enrichedAdapters:
                        enrichedAdapterFile.write(maxAdapter.formatForWriting())
                        enrichedAdapters.append(maxAdapter.sequence)
                else:
                    print("WARNING: No adapters meet enrichment threshold. Adapter file will be empty.")
                print(f"Maximum enrichment was {percentage}% for {maxAdapter.sequenceName}")

    return enrichedAdapterFilePaths


def main():

    with TkinterDialog(workingDirectory = os.getenv("HOME"), title = "Find Adapters") as dialog:
        dialog.createMultipleFileSelector("Raw fastq reads:", 0, ".fastq.gz",
                                        ("Gzipped fastq Files", ".fastq.gz"), ("fastq Files", ".fastq"),
                                        additionalFileEndings=[".fastq"])
        dialog.createFileSelector("Adapter file:", 1, ("Fasta File", ".fa"))
        with dialog.createDynamicSelector(2, 0) as searchLengthLimitDS:
            searchLengthLimitDS.initCheckboxController("Limit search length")
            searchLengthLimitDS.initDisplay(True, "searchLengthLimit").createTextField("Search length limit:", 0, 0, defaultText = "42")

    # Sanitize inputs
    fastqFilePaths = [filePath for filePath in dialog.selections.getFilePathGroups()[0] if 
                      getIsolatedParentDir(filePath) != ".tmp"]
    if searchLengthLimitDS.getControllerVar():
        searchLengthLimit = checkForNumber(dialog.selections.getTextEntries("searchLengthLimit")[0], True,
                                           lambda x:x>0, "Expected a positive-integer search length limit")
    else:
        searchLengthLimit = None

    findAdapters(fastqFilePaths, dialog.selections.getIndividualFilePaths()[0], searchLengthLimit = searchLengthLimit)


if __name__ == "__main__": main()
