import warnings
from benbiohelpers.CustomErrors import UserInputError


def parseToIterable(input: str, sepChar = ',', rangeChar = '-', stepChar = '$', castType = None):
    """
    A function for parsing strings to an iterable based on special characters
    - sepChar: Separates individual items (or ranges of items) in the iterable (e.g. "1, 2, 3")
    - rangeChar: Specifies a range of values ("1-3" is essentially equivalent to "1, 2, 3").
                 If rangeChar is none, ranges are ignored entirely. (Can be useful if strings contain range char.)
    - stepChar: Specifies a the value to increment by in ranges. Default is 0. Can be a float!
    - castType: The type to cast single-item output to. No casting is performed if castType is NoneType or str.

    NOTE: Leading and trailing whitespace and whitespace adjacent to the above characters is removed from final output
    """

    # Remove trailing and leading whitespace
    input = input.strip()

    # If there are separator characters in the input, split it into multiple inputs,
    # and recursively perform this function on each, concatenating the results into a single list.
    if sepChar in input:
        return([
            item for inputIterable in input.split(sepChar)
                 for item in parseToIterable(inputIterable, sepChar, rangeChar, stepChar, castType)
        ])

    # If there is a range separator in the input (and no separator characters),
    # parse the input to a range object (if possible), or a list of numbers if not.
    elif rangeChar is not None and rangeChar in input:
        start, stop = (item.strip() for item in input.split(rangeChar, 1))
        if stepChar in stop:
            stop, step = (item.strip() for item in stop.split(stepChar, 1))
        else: step = 1

        try: float(start)
        except: raise UserInputError("Range start cannot be cast to a numeric value. Did you mean to set rangeChar to None?")
        try: float(stop)
        except: raise UserInputError("Range stop cannot be cast to a numeric value. Did you mean to set rangeChar to None?")
        try: float(step)
        except: raise UserInputError("Range step cannot be cast to a numeric value. Did you mean to set rangeChar to None?")

        if float(step) == 0: raise UserInputError("Step of 0 given.")
        if float(stop) < float(start) and float(step) > 0: 
            warnings.warn(f"Stop is less than start in range {input} and step value is positive.  Range will contain no values.")
        if float(stop) > float(start) and float(step) < 0: 
            warnings.warn(f"Start is less than stop in range {input} and step value is negative.  Range will contain no values.")

        try:
            if int(step) > 0: thisRange = range(int(start),int(stop)+1,int(step))
            else: thisRange = range(int(start),int(stop)-1,int(step))
        except: thisRange = [float(start)+i*float(step) for i in range(int((float(stop)-float(start)) / float(step) + 1))]

        return thisRange


    # Otherwise, the input is a single item that just needs to be turned into an iterable and returned.
    # (Unless of course it's empty, in which case an empty list should be returned.)
    else:
        if not input: return([])
        elif castType is None or castType is str: return([input])
        else: 
            try: return([castType(input)])
            except: raise UserInputError(f"Input: {input} cannot be cast to desired type: {castType}.")