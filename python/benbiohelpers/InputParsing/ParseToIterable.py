import warnings
from benbiohelpers.CustomErrors import UserInputError


def parseToIterable(input: str, sepChar = ',', rangeChar = '-', stepChar = '$', castType = None):
    """
    A function for parsing strings to an iterable based on special characters
    - sepChar: Separates individual items (or ranges of items) in the iterable (e.g. "1, 2, 3")
    - rangeChar: Specifies a range of values ("1-3" is essentially equivalent to "1, 2, 3").
                 If rangeChar is none, ranges are ignored entirely. (Can be useful if strings contain range char.)
    - stepChar: Specifies the value to increment by in ranges. Default is 0. Can be a float!
    - castType: The type to cast single-item output to. No casting is performed if castType is NoneType or str.

    NOTE: Leading and trailing whitespace and whitespace adjacent to the above characters is removed from final output
    """

    outputList = list()

    # Split the input into pieces using the separator character
    for inputPiece in input.split(sepChar):

        # Remove trailing and leading whitespace
        inputPiece = inputPiece.strip()

        # If there is a range character in the current inputPiece (and no separator characters),
        # parse it to a range object (if possible), or a list of numbers if not.
        if rangeChar is not None and rangeChar in inputPiece:
            start, stop = (item.strip() for item in inputPiece.split(rangeChar, 1))
            if stepChar in stop:
                stop, step = (item.strip() for item in stop.split(stepChar, 1))
            else: step = 1

            try: float(start)
            except: raise UserInputError(f"Range start \"{start}\" cannot be cast to a numeric value. "
                                        "Did you mean to set rangeChar to None?")
            try: float(stop)
            except: raise UserInputError(f"Range stop \"{stop}\" cannot be cast to a numeric value. "
                                        "Did you mean to set rangeChar to None?")
            try: float(step)
            except: raise UserInputError(f"Range step \"{step}\" cannot be cast to a numeric value. "
                                        "Did you mean to set rangeChar to None?")

            if float(step) == 0: raise UserInputError("Step of 0 given.")
            if float(stop) < float(start) and float(step) > 0: 
                warnings.warn(f"Stop is less than start in range {input} and step value is positive. "
                            "Range will contain no values.")
            if float(stop) > float(start) and float(step) < 0: 
                warnings.warn(f"Start is less than stop in range {input} and step value is negative. "
                            "Range will contain no values.")

            try:
                if int(step) > 0: outputList.append(range(int(start),int(stop)+1,int(step)))
                else: outputList.append(range(int(start),int(stop)-1,int(step)))
            except: outputList += [float(start)+i*float(step) for i in range(int((float(stop)-float(start)) / float(step) + 1))]


        # Otherwise, the inputPiece is a single item (unless of course it's empty)
        elif inputPiece:
            if castType is None or castType is str: outputList.append(inputPiece)
            else: 
                try: outputList.append(castType(inputPiece))
                except: raise UserInputError(f"Input: {inputPiece} cannot be cast to desired type: {castType}.")

    # If the output list contains exactly 1 item and it is a range, return just that range. (It's more efficient!)
    if len(outputList) == 1 and type(outputList[0]) is range:
        return outputList[0]

    # Otherwise, we need to unpack all range items or the output list can't be iterated through properly.
    else:
        unpackedOutputList = list()
        for item in outputList:
            if type(item) is range: unpackedOutputList += [num for num in item]
            else: unpackedOutputList.append(item)
        return unpackedOutputList