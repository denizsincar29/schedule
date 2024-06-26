# news handler
# read last news from a file.

import os

def news():
    if not os.path.exists("news.txt"):
        return None  # dont show.
    with open("news.txt", "r", encoding="UTF-8") as f:
        new=f.read()
    # if news.old.txt exists, delete it.
    if os.path.exists("news.old.txt"):
        os.remove("news.old.txt")
    os.rename("news.txt", "news.old.txt") # dont delete in case of error
    return new
