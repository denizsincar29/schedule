import sys
import os

win= sys.platform == 'win32'
if win:
    from cytolk import tolk



# all functions are working only on Windows, so dummy functions are used on other platforms
class ScreenReader:
    def __init__(self):
        self.tolk=tolk.tolk() if win else None
    def __enter__(self):
        if win:
            self.tolk.__enter__()
        return self
    def __exit__(self, type, value, traceback):
        if win:
            self.tolk.__exit__(type, value, traceback)

    def output(self, text):
        if win:
            tolk.output(text)

