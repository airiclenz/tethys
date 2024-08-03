import subprocess
from datetime import datetime


# =============================================================================
# =============================================================================
# =============================================================================
class Logger:
    __separator = " > "

    # =============================================================================
    def __init__(self, clearScreen=True):
        if clearScreen == True:
            # clear the screen
            subprocess.call("clear", shell=True)

    # =============================================================================
    def log(self, message1="", message2="", message3=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if message1 != "" and message2 != "" and message3 != "":
            print(timestamp, self.__separator, message1, message2, message3)

        elif message1 != "" and message2 != "":
            print(timestamp, self.__separator, message1, message2)

        elif message1 != "" and message2 == "":
            print(timestamp, self.__separator, message1)

        else:
            print(timestamp)
