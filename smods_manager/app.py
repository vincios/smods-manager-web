import os
import platform
from pathlib import Path

from smodslib.model import ModBase

from utils.utils import win_search_cs_folders

DEBUG = 1
WEBSOCKET_PORT = 5001

app_folder = os.path.join(os.path.expanduser("~"), ".smods_manager")
db_path = os.path.join(app_folder, 'app.db')
download_folder = os.path.join(app_folder, "downloads")

def init_database():
    from db import metadata, engine
    from db.app import set_configuration_object, CONFIGURATION_KEYS as conf

    metadata.create_all(engine)

    cs_install_location = None
    cs_data_location = None

    if not DEBUG and platform.system() == "Windows":
        cs_install_location, cs_data_location = win_search_cs_folders()
    elif DEBUG:
        cs_install_location = os.path.join(app_folder, "install_dir")
        cs_data_location = os.path.join(app_folder, "data_dir")

    default_config = {
        conf.CS_INSTALL_DIR: cs_install_location,
        conf.CS_DATA_DIR: cs_data_location
    }
    set_configuration_object(default_config)


def generate_app_folders():
    if not os.path.exists(app_folder):
        print(f"Generating app folder in {app_folder}")
        Path(app_folder).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(download_folder):
        print(f"Generating download folder in {download_folder}")
        Path(download_folder).mkdir(parents=True, exist_ok=True)


def get_asset_target_folder(mod: ModBase):
    from db.app import get_configuration
    install_dir = get_configuration("cs.install.dir").value
    data_dir = get_configuration("cs.data.dir").value

    category = mod.category.lower()

    if category == "mod":
        return os.path.join(install_dir, "Files", "Mods")
    elif category == "map":
        return os.path.join(data_dir, "Maps")
    elif "color correction" in category:
        return os.path.join(data_dir, "Addons", "ColorCorrections")
    elif category == "map theme":
        return os.path.join(data_dir, "Addons", "MapThemes")
    elif "style" in category:
        return os.path.join(data_dir, "Addons", "Styles")
    else:
        return os.path.join(data_dir, "Addons", "Assets")
