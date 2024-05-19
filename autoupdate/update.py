import httpx
import os
import sys
from packaging import version
from subprocess import Popen
import tqdm
from .version import VERSION

ver=version.parse  # from autoupdate.update import ver  # for convenience


def get_latest_release():
    """
    Retrieves the latest release information for a given GitHub repository.

    Returns:
        dict: A dictionary containing the JSON response of the latest release.

    Raises:
        httpx.HTTPError: If the HTTP request to the GitHub API fails or returns an error.

    """
    url = "https://deniz.r1oaz.ru/schedule/version.json"
    with httpx.Client() as client:
        response = client.get(url)
    response.raise_for_status()
    j=response.json()
    return j

def download_release():
    """
    Downloads a release from the given URL and saves it to the specified path.


    Raises:
        httpx.HTTPError: If there is an error while downloading the release.

    """
    with httpx.Client(follow_redirects=True) as client:
        response = client.get("https://deniz.r1oaz.ru/schedule/setup.exe", timeout=None)
    response.raise_for_status()
    with open("setup.exe", 'wb') as f:
        # get the total file size from the response headers
        total = int(response.headers.get('Content-Length', 0))
        # if no callback, use tqdm
        for chunk in tqdm.tqdm(response.iter_bytes(), total=total, unit='B', unit_scale=True):
            f.write(chunk)

def check_and_update():
    # if not pyinstalled, we will not update
    if not hasattr(sys, 'frozen'):
        return
    release = get_latest_release()
    latest_version = ver(release['version'])
    if VERSION<latest_version or release['force_update']:
        yield (..., latest_version)
        download_release()
        yield (True, latest_version)
        return
    yield (False, latest_version)

def restart():
    """
    Restarts the current program.
    Note: This function does not return. Any cleanup action (like saving data) must be done before calling this function.
    """
    if not (sys.frozen and hasattr(sys, '_MEIPASS')):
        return  # we are not pyinstalled
    Popen(["setup.exe", "/SILENT", "/FORCECLOSEAPPLICATIONS"])
    sys.exit()

# console interaction
def console_update():
    print("Checking for updates...")
    for status, lversion in check_and_update():
        if status is ...:
            print(f"Новое обновление! Версия {lversion}. Хотите обновиться? (y/n)")
            # if "y".lower() is not in input, then break
            if "y" not in input().lower():
                break
        elif status:
            print(f"Обновлено до версии {lversion}!")
            print("Перезапуск...")
            restart()
        #else: we just skip because it will else print "no update available" in every start of the program

        # from autoupdate.update import console
        # console()
        # that's all!
