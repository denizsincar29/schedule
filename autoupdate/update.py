import httpx
import os
from packaging import version
import tqdm

def get_latest_release(user, repo):
    """
    Retrieves the latest release information for a given GitHub repository.

    Args:
        user (str): The username or organization name of the repository owner.
        repo (str): The name of the repository.

    Returns:
        dict: A dictionary containing the JSON response of the latest release.

    Raises:
        httpx.HTTPError: If the HTTP request to the GitHub API fails or returns an error.

    """
    url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
    with httpx.Client() as client:
        response = client.get(url)
    response.raise_for_status()
    return response.json()

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

def check_and_update(user, repo, current_version, download_path):
    """
    Checks for updates in the specified GitHub repository and downloads the latest release if available.

    Args:
        user (str): The username or organization name of the GitHub repository.
        repo (str): The name of the GitHub repository.
        current_version (str): The current version of the software.
        download_path (str): The path where the downloaded release file will be saved.

    Yields:
        tuple: A tuple containing a boolean value indicating whether an update is available, the latest version number, and what's new or empty string.

    """
    release = get_latest_release(user, repo)
    latest_version = release['tag_name']
    # if no release is found, return False
    if not latest_version:
        yield (False, "0.0.0", "no release found")
    if version.parse(latest_version) > version.parse(current_version):
        yield (..., latest_version, release['body'])
        for asset in release['assets']:
            if asset['name'].endswith('.exe'):  # download .exe file
                download_url = asset['browser_download_url']
                download_release(download_url, os.path.join(download_path, asset['name']))
                yield (True, latest_version, release['body'])
    yield (False, latest_version)

# Usage
if __name__ =="__main__":
    user = "denizsincar29"
    repo = "schedule"
    current_version = "2024.04.08"
    user="yt-dlp"  # overwrite to test
    repo="yt-dlp"
    current_version="2024.04.08"
    download_path="."
    download_path="c:/users/user/files/yt-dlp/"  # overwrite to test
    for status, latest_version, body in check_and_update(user, repo, current_version, download_path):
        if status is ...:
            print(f"Update available: {latest_version} Do you want to download?\n{body}")
            try:
                input("Press Enter to continue or Ctrl+C to cancel")
            except (KeyboardInterrupt, EOFError):
                print("Update cancelled")
                break  # we don't want to proceed running the code after yielding this value
        elif status:
            print(f"Updated to {latest_version}:\n{body}")
        else:
            if latest_version=="0.0.0":  # normally used for debugging
                print(f"No release found for {repo}")
            print(f"Already up-to-date at {latest_version}")