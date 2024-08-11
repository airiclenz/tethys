import os
import subprocess
from datetime import datetime
from colorama import Fore, Style


# =============================================================================
# =============================================================================
# =============================================================================
class Logger:
    _separator = '|   '
    _indentDepth = 0
    _indentString = ''
    _color = Fore.WHITE

    # =============================================================================
    def __init__(self, color=Fore.WHITE, clearScreen=True):
        if clearScreen == True:
            # clear the screen
            subprocess.call("clear", shell=True)
            os.system('color')
            self._color = color

    # =============================================================================
    def increaseIndent(self):
        self._indentDepth = self._indentDepth + 1
        self.generateIndentString()

    # =============================================================================
    def decreaseIndent(self):
        if (self._indentDepth > 0):
            self._indentDepth = self._indentDepth - 1
            self.generateIndentString()

    # =============================================================================
    def generateIndentString(self):

        self._indentString = ''

        for i in range(0, self._indentDepth):
            self._indentString = self._indentString + self._separator


    # =============================================================================
    def log(self, message=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        style = None

        if self._indentDepth == 0:
            style = Style.NORMAL
        else:
            style = Style.BRIGHT

        if message != None:
            print(f'{Fore.WHITE}{Style.RESET_ALL}{timestamp}  {self._color}{Style.DIM}{self._indentString}{style}{message}')

        else:
            print(f'{Fore.WHITE}{timestamp}')

