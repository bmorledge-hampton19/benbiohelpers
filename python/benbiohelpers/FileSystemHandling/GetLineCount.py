# A simple function for getting the number of lines in a file
def getLineCount(filePath):
    with open(filePath, 'r') as file:
        return sum(1 for _ in file)