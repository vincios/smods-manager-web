import functools
import os
import time
import winreg
from pathlib import Path
from shutil import copy2, copytree
from typing import Callable, Union
from zipfile import ZipFile


def folder_size(path):
    # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    root_directory = Path(path)

    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())


def copydir(src: str, dest: str, callback: Callable[[int, int], None] = None):
    root, dirs, files = next(os.walk(src))
    copying_folder = dirs[0] if dirs else None

    total = folder_size(src)

    def copy2_callback(total_size, s, d):
        from utils.logger import get_logger
        logger = get_logger(__name__)
        copy2(s, d)

        if copying_folder:
            logger.debug(f"Generating folder size for path {os.path.join(dest, copying_folder)}")
            copied_size = folder_size(os.path.join(dest, copying_folder))
            logger.debug(f"{copied_size}")
            if callback:
                try:
                    callback(copied_size, total_size)
                except Exception:
                    # continue copy in case of exception into the callback function
                    pass

    copy_fn: Callable[[str, str], None] = functools.partial(copy2_callback, total)
    return copytree(src, dest, copy_function=copy_fn, dirs_exist_ok=True)


def unzip(zip_path: str, dest_path: str) -> str:
    """
    Unzip the zip at zip_path insto dest_path. Returns the path to the unzipped folder.
    """
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_root_folder = zip_ref.filelist[0].filename
        zip_ref.extractall(dest_path)

    return os.path.join(dest_path, zip_root_folder)


def wait_for_file(path: str, timeout: int = 120) -> str:
    """
    Wait until a file exists in a folder, or until timeout time exceed
    :param path: file to watch
    :param timeout: timeout seconds
    :return: watched file path if no timeout happen
    """
    wait_time = timeout
    while not os.path.exists(path):
        if wait_time < 0:
            raise TimeoutError("Timeout time exceeded")

        time.sleep(1)
        wait_time = wait_time - 1

    return path


def win_search_cs_folders():
    """
    On Windows, this function tries to return the installation folder and data folder of Cities Skylines. Otherwise,
    None will be returned
    """
    def _search_cs_install_folder() -> Union[str, None]:
        install_location = None
        key_tests = ["cs", "cities", "skylines"]
        install_locations_tests = ["cs", "cities", "skylines", "colossal", "order"]

        def get_reg_value(key, subpath, name):
            try:
                registry_key = winreg.OpenKey(key, subpath, 0, winreg.KEY_READ)
                value, regtype = winreg.QueryValueEx(registry_key, name)
                winreg.CloseKey(registry_key)
                return value
            except WindowsError:
                return None

        base_keys = [
            winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall', 0,
                           winreg.KEY_READ),
            winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 0,
                           winreg.KEY_READ)
        ]

        for base_key in base_keys:
            if install_location:
                break

            for i in range(winreg.QueryInfoKey(base_key)[0]):
                subkey = winreg.EnumKey(base_key, i)
                tests = [test in subkey.lower() for test in key_tests]

                if any(tests):
                    try:
                        value = get_reg_value(base_key, subkey, "InstallLocation")
                        tests = [test in value.lower() for test in install_locations_tests]
                        if any(tests):
                            install_location = value
                            break
                    except FileNotFoundError:
                        continue

        for key in base_keys:
            winreg.CloseKey(key)

        paths = [
            os.path.join(os.environ["ProgramFiles"]),
            os.path.join(os.environ["ProgramFiles(x86)"]),
            os.path.join(os.environ["ProgramFiles"], "Steam", "steamapps", "common"),
            os.path.join(os.environ["ProgramFiles(x86)"], "Steam", "steamapps", "common"),
        ]

        for base_path in paths:
            if install_location:
                break

            root, dirs, files = next(os.walk(base_path))
            for directory in dirs:
                if "colossal order" in directory.lower().replace("_", ""):
                    root2, dirs2, files2 = next(os.walk(os.path.join(base_path, directory)))
                    for directory2 in dirs2:
                        if "cities skylines" in directory2.lower().replace("_", ""):
                            install_location = os.path.join(base_path, directory, directory2)
                elif "cities skylines" in directory.lower().replace("_", ""):
                    install_location = os.path.join(base_path, directory)

        return install_location

    install_location = _search_cs_install_folder()
    data_location = None

    data_test_location = os.path.join(os.environ["LOCALAPPDATA"], "Colossal Order", "Cities_Skylines")
    if os.path.exists(data_test_location):
        data_location = data_test_location

    return install_location, data_location
