# This script is kind of like a simplified version of the third test script.  I made this to check which mutations are being counted in nucleosomes
# in order to find out which ones are being omitted from previous iterations of the package.
import timeit

from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
from benbiohelpers.CountThisInThat.Counter import ThisInThatCounter
from benbiohelpers.CountThisInThat.InputDataStructures import EncompassingDataDefaultStrand, ENCOMPASSED_DATA
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import CounterOutputDataHandler

class MutationsInTfbsCounter(ThisInThatCounter):

    def setUpOutputDataHandler(self):
        self.outputDataHandler = CounterOutputDataHandler(self.writeIncrementally)
        self.outputDataHandler.addEncompassedFeatureStratifier("Mutation_Pos")
        self.outputDataHandler.addPlaceholderStratifier()
        self.outputDataHandler.createOutputDataWriter(self.outputFilePath, customStratifyingNames = (None,{None:"Counts"}))

    def constructEncompassingFeature(self, line) -> EncompassingDataDefaultStrand:
        return EncompassingDataDefaultStrand(line, self.acceptableChromosomes)


def testingCountThisInThat3(mutationPosFilePath, nucPosFilePath, outputFilePath):

    #counter = MutationsInTfbsCounter(mutationPosFilePath, tFBSPosFilePath, outputFilePath)
    counter = MutationsInTfbsCounter(mutationPosFilePath, nucPosFilePath, outputFilePath, 
                                     encompassingFeatureExtraRadius = 73, writeIncrementally = ENCOMPASSED_DATA)
    counter.count()


def main():

    # Create the Tkinter UI
    dialog = TkinterDialog(workingDirectory=getDataDirectory())
    dialog.createFileSelector("Bed Mutation Data:",0,("Bed Files",".bed"))
    dialog.createFileSelector("Nucleosome Positions:",1,("Bed Files",".bed"))
    dialog.createFileSelector("Output File:",2,("TSV Files",".tsv"), ("Bed Files",".bed"), newFile = True)

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    def go():
        testingCountThisInThat3(dialog.selections.getIndividualFilePaths()[0], dialog.selections.getIndividualFilePaths()[1],
                                dialog.selections.getIndividualFilePaths()[2])

    print(timeit.timeit(go, number=1))


if __name__ == "__main__": main()