# This script is testing the CountThisInThat classes by replicating my previous code that tracks TFBS's at mutation positions.
import timeit

from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
from benbiohelpers.CountThisInThat.Counter import ThisInThatCounter
from benbiohelpers.CountThisInThat.InputDataStructures import TfbsData
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import AmbiguityHandling, CounterOutputDataHandler
from benbiohelpers.CountThisInThat.SupplementalInformation import TfbsSupInfoHandler

class MutationsInTfbsCounter(ThisInThatCounter):

    def setUpOutputDataHandler(self):
        self.outputDataHandler = CounterOutputDataHandler(self.writeIncrementally)
        self.outputDataHandler.addEncompassedFeatureStratifier("Mutation Position")
        self.outputDataHandler.addPlaceholderStratifier(AmbiguityHandling.record)
        self.outputDataHandler.addSupplementalInformationHandler(TfbsSupInfoHandler, 0)
        self.outputDataHandler.createOutputDataWriter(self.outputFilePath, customStratifyingNames = (None,{None:"Counts"}))

    def constructEncompassingFeature(self, line) -> TfbsData:
        return TfbsData(line, self.acceptableChromosomes)


def testingCountThisInThat3(mutationPosFilePath, tFBSPosFilePath, outputFilePath):

    counter = MutationsInTfbsCounter(mutationPosFilePath, tFBSPosFilePath, outputFilePath)
    counter.count()


def main():

    # Create the Tkinter UI
    dialog = TkinterDialog(workingDirectory=getDataDirectory())
    dialog.createFileSelector("Bed Mutation Data:",0,("Bed Files",".bed"))    
    dialog.createFileSelector("TFBS Positions:",1,("Bed Files",".bed"))
    dialog.createFileSelector("Output File:",2,("TSV Files",".tsv"), newFile = True)

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    def go():
        testingCountThisInThat3(dialog.selections.getIndividualFilePaths()[0], dialog.selections.getIndividualFilePaths()[1],
                                dialog.selections.getIndividualFilePaths()[2])

    print(timeit.timeit(go, number=1))


if __name__ == "__main__": main()