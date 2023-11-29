from random import choice, randrange

class randomGenerator:
    def __init__(self):
        self.LOWER_CASE_ASCIIS = list(range(97, 122 + 1))
        self.UPPER_CASE_ASCIIS = list(range(65, 90 + 1))
        self.NUMBER_ASCIIS = list(range(48, 57 + 1))
        self.ALPHANUMERIC_ASCIIS = self.LOWER_CASE_ASCIIS + self.UPPER_CASE_ASCIIS + self.NUMBER_ASCIIS


    def AlphaNumeric(self, _min=10, _max=20)->str:
        string = ''
        for _ in range(randrange(_min, _max)):
            string += chr(choice(self.ALPHANUMERIC_ASCIIS))
        return string


    def OnlyNumeric(self, _min=10, _max=20)->str:
        string = ''
        for _ in range(randrange(_min, _max)):
            string += chr(choice(self.LOWER_CASE_ASCIIS+self.UPPER_CASE_ASCIIS))
        return string


    def OnlyAlpha(self, _min=10, _max=20)->str:
        string = ''
        for _ in range(randrange(_min, _max)):
            string += chr(choice(self.LOWER_CASE_ASCIIS+self.UPPER_CASE_ASCIIS))
        return string
