import httpx
import os
import sys
from packaging import version
from subprocess import Popen
import tqdm

def get_latest_release(user, repo, prerelease=False):
    """
    Retrieves the latest release information for a given GitHub repository.

    Args:
        user (str): The username or organization name of the repository owner.
        repo (str): The name of the repository.
        prerelease (bool): Whether to include prereleases in the results (default is False).

    Returns:
        dict: A dictionary containing the JSON response of the latest release.

    Raises:
        httpx.HTTPError: If the HTTP request to the GitHub API fails or returns an error.

    """
    url = f"https://api.github.com/repos/{user}/{repo}/releases"  # very strange, but trailing slash breaks the request
    if not prerelease:
        url += "/latest"
    with httpx.Client() as client:
        response = client.get(url)
    response.raise_for_status()
    j=response.json()
    if prerelease:
        return j[0] # return the first release if prerelease is True
    return j

def download_release(url, path):
    """
    Downloads a release from the given URL and saves it to the specified path.

    Args:
        url (str): The URL of the release to download.
        path (str): The path where the downloaded release should be saved.

    Raises:
        httpx.HTTPError: If there is an error while downloading the release.

    """
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url)
    response.raise_for_status()
    with open(path, 'wb') as f:
        # get the total file size from the response headers
        total = int(response.headers.get('Content-Length', 0))
        for chunk in tqdm.tqdm(response.iter_bytes(), desc="Downloading", unit="B", unit_scale=True, total=total):
            f.write(chunk)

def check_and_update(user, repo, current_version, download_path, prerelease=False):
    """
    Checks for updates in the specified GitHub repository and downloads the latest release if available.

    Args:
        user (str): The username or organization name of the GitHub repository.
        repo (str): The name of the GitHub repository.
        current_version (str): The current version of the software.
        download_path (str): The path where the downloaded release file will be saved.
        prerelease (bool): Whether to include prereleases in the results (default is False).

    Yields:
        tuple: A tuple containing a boolean value indicating whether an update is available, the latest version number, and what's new or empty string.

    """
    # if not pyinstalled, we will not update
    if not hasattr(sys, 'frozen'):
        return
    try: os.remove("restart.bat")  # remove the restart.bat file if it exists
    except FileNotFoundError: pass
    new_exe=os.path.splitext(download_path)[0]+".new"+os.path.splitext(download_path)[1]
    release = get_latest_release(user, repo, prerelease)
    latest_version = release['tag_name']
    # if no release is found, return False
    if not latest_version:
        yield (False, "0.0.0", "no release found")
    if version.parse(latest_version) > version.parse(current_version):
        yield (..., latest_version, release['body'])
        download_filename=os.path.basename(download_path)
        for asset in release['assets']:
            if asset['name']==download_filename:
                download_url = asset['browser_download_url']
                # .exe to .new.exe
                download_release(download_url, new_exe)
                yield (True, latest_version, release['body'])
                return
    yield (False, latest_version, "no update available")

def restart():
    """
    Restarts the current program.
    Note: This function does not return. Any cleanup action (like saving data) must be done before calling this function.
    """
    # make up a bat file that will delete the x.exe and rename x.new.exe to x.exe than run x
    new_exe=os.path.splitext(sys.argv[0])[0]+".new"+os.path.splitext(sys.argv[0])[1]
    bat=f"""@echo off
timeout /t 1 /nobreak >nul
del "{sys.argv[0]}"
ren "{new_exe}" "{os.path.basename(sys.argv[0])}"
start "" "{sys.argv[0]}"
"""
    with open("restart.bat", "w", encoding="utf-8") as f:
        f.write(bat)
    # popen in background to exit before the bat file is executed
    Popen("restart.bat", shell=True)
    print("exitting")  # debug
    sys.exit()