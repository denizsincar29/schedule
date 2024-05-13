# make an sfx from the dist folder
import py7zr
from subprocess import call
import os

def make_sfx(filelist):
    if not os.path.exists("sfx_config.txt"):
        with open("autoupdate/sfx_config.txt", "w") as f:
            f.write(";!@Install@!UTF-8!\n")
            f.write("Title=\"Schedule\"\n")
            f.write("BeginPrompt=\"Do you want to install Schedule?\"\n")
            f.write("RunProgram=\"schedule.exe\"\n")
            f.write(";!@InstallEnd@!\n")
    # create a 7z archive
    sfx_name="setup"
    with py7zr.SevenZipFile(sfx_name+".7z", 'w') as archive:
        for file in filelist:
            # add to the root of the archive
            archive.write(file, os.path.basename(file))
        # make the archive an sfx
        archive.write("autoupdate/sfx_config.txt", "sfx_config.txt")
    # create the sfx
    #call(["7z", "s", "-sfx7z.sfx", sfx_name+".7z", "-o"+sfx_name+".exe"])
    # call winrar, since 7z doesn't support sfx
    call(["C:\\Program Files\\WinRAR\\Rar.exe", "a", "-sfx", sfx_name+".exe", sfx_name+".7z"])


make_sfx(["dist/schedule.exe", "dist/schedule_console.exe", "dist/news.txt"])
