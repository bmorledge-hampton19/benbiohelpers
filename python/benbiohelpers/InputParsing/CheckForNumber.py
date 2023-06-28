def checkForNumber(inputToCheck, enforceInt = False, validityCondition = None, validityText = ""):
    """
    First, checks if the inputToCheck parameter can be cast to a float. If enforceInt is true, make sure
    the value can also be cast as an int. If validityCondition is not None, it should be a function
    which takes a single numeric value and returns true or false.
    ValidityText is the text to display if the validity condition does not pass.
    If the input passes all checks, return it.
    """

    from benbiohelpers.CustomErrors import NonIntInput, NonNumericInput, InvalidNumericInput

    raiseNonIntInput = False
    raiseNonNumericInput = False

    if enforceInt:
        try: numericInput = int(inputToCheck)
        except ValueError: raiseNonIntInput = True
    else:
        try: numericInput = float(inputToCheck)
        except ValueError: raiseNonNumericInput = True

    if raiseNonIntInput: raise NonIntInput(inputToCheck)
    if raiseNonNumericInput: raise NonNumericInput(inputToCheck)

    if validityCondition is not None and not validityCondition(numericInput):
        raise InvalidNumericInput(numericInput, validityText)

    return numericInput