# news handler
# read last news from a file.

import os

def news():
    if not os.path.exists("news.txt"):
        return None  # dont show.
    with open("news.txt", "r") as f:
        new=f.read()
    os.remove("news.txt")  # to prevent showing the same news over and over and over again xD
    return new
