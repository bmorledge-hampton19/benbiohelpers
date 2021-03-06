# This script is testing the CountThisInThat classes by replicating my previous code that counts mutations in genic vs. intergenic regions
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
from benbiohelpers.CountThisInThat.Counter import ThisInThatCounter
from benbiohelpers.CountThisInThat.InputDataStructures import EncompassedDataWithContext
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import AmbiguityHandling, CounterOutputDataHandler

import timeit


class MutationsInGenesCounter(ThisInThatCounter):

    def setUpOutputDataHandler(self):
        self.outputDataHandler = CounterOutputDataHandler(self.writeIncrementally, trackAllEncompassed = True, countAllEncompassed = True)
        self.outputDataHandler.addEncompassedFeatureContextStratifier(3, True, "Trinucleotide")
        self.outputDataHandler.addStrandComparisonStratifier(strandAmbiguityHandling = AmbiguityHandling.record)
        self.outputDataHandler.createOutputDataWriter(self.outputFilePath, 
            customStratifyingNames = (None, {True:"NTS_Counts", False:"TS_Counts", None:"Intergenic_and_Ambiguous_Counts"}))

    def constructEncompassedFeature(self, line) -> EncompassedDataWithContext:
        return EncompassedDataWithContext(line, self.acceptableChromosomes)


def testingCountThisInThat2(mutationFilePath, geneDesignationsFilePath, outputFilePath):

    counter = MutationsInGenesCounter(mutationFilePath, geneDesignationsFilePath, outputFilePath)
    counter.count()


def main():

    # Create the Tkinter UI
    dialog = TkinterDialog(workingDirectory=getDataDirectory())
    dialog.createFileSelector("Bed Mutation Data:",0,("Bed Files",".bed"))    
    dialog.createFileSelector("Gene Designations:",1,("Bed Files",".bed"))
    dialog.createFileSelector("Output File:",2,("TSV Files",".tsv"), newFile = True)

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    def go():
        testingCountThisInThat2(dialog.selections.getIndividualFilePaths()[0], dialog.selections.getIndividualFilePaths()[1],
                                dialog.selections.getIndividualFilePaths()[2])

    print(timeit.timeit(go, number=5))


if __name__ == "__main__": main()