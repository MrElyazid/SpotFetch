"""Persistent settings for SpotFetch, stored as JSON in the user config dir
the location of the conf is :

macOS 	~/Library/Application Support/spotfetch
Linux / Unix 	$XDG_CONFIG_HOME/spotfetch (default ~/.config/spotfetch)
Windows 	%APPDATA%\\spotfetch\\{version} (i.e. C:\\Users\\<user>\\AppData\\Roaming\\spotfetch\\{version})

"""

import json
from pathlib import Path

import platformdirs
from rich import print

CONFIG_PATH = Path(platformdirs.user_config_dir("spotfetch")) / "settings.json"


def load_settings() -> dict:
    """Persisted settings; empty dict when the file is missing or unreadable."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING : could not read {CONFIG_PATH} ({e}), using defaults")
        return {}


def save_settings(settings: dict) -> None:
    """Write settings to the config file, creating the directory if needed."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
