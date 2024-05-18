import httpx
import os
import sys
from packaging import version
from subprocess import Popen
import tqdm

ver=version.parse  # from autoupdate.update import ver  # for convenience

def get_latest_release():
    """
    Retrieves the latest release information for a given GitHub repository.

    Returns:
        dict: A dictionary containing the JSON response of the latest release.

    Raises:
        httpx.HTTPError: If the HTTP request to the GitHub API fails or returns an error.

    """
    url = f"https://deniz.r1oaz.ru/schedule/version.json"
    with httpx.Client() as client:
        response = client.get(url)
    response.raise_for_status()
    j=response.json()
    return j

def download_release(progress_callback=None, yield_total=False):
    """
    Downloads a release from the given URL and saves it to the specified path.

    Args:
    progress_callback: A callback function that takes a single argument, the number of bytes downloaded so far.
    yield_total: If True, yields the total file size before downloading.

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
        iterable=response.iter_bytes() if progress_callback is not None else tqdm.tqdm(response.iter_bytes(), total=total, unit='B', unit_scale=True)  # clever, right?
        for chunk in iterable:
            f.write(chunk)
            if progress_callback is not None:
                progress_callback(len(chunk))

def check_and_update(current_version, progress_callback=None):
    # if not pyinstalled, we will not update
    if not hasattr(sys, 'frozen'):
        return
    release = get_latest_release()
    latest_version = version.parse(release['version'])
    if current_version < latest_version or release['force_update']:
        yield (..., latest_version)
        download_release(progress_callback)
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
    # popen inno setup setup.exe --silent
    Popen("setup.exe --silent", shell=True)
    sys.exit()

# console interaction
def console_update(current_version):
    print("Checking for updates...")
    for status, version in check_and_update(current_version):
        if status is ...:
            print(f"Новое обновление! Версия {version}. Хотите обновиться? (y/n)")
            # if "y".lower() is not in input, then break
            if "y" not in input().lower():
                break
        elif status:
            print(f"Обновлено до версии {version}!")
            print("Перезапуск...")
            restart()
        #else: we just skip because it will else print "no update available" in every start of the program

        # from autoupdate.update import console
        # console(version.parse("0.0.1"))
        # that's all!
