"""Uygulamanın kullandığı dosya ve klasör yolları."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent

_xdg_config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
_xdg_cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")

CONFIG_DIR = _xdg_config / "ecofuav-hangar"
CACHE_DIR = _xdg_cache / "ecofuav-hangar"

# Kullanıcının kendi modül listesi; ilk açılışta varsayılandan kopyalanır.
USER_MODULES_FILE = CONFIG_DIR / "modules.yaml"
DEFAULT_MODULES_FILE = APP_DIR / "config" / "default_modules.yaml"

# Takımın ortak sürüm listesi; repoyla birlikte gelir.
VERSIONS_FILE = APP_DIR / "install" / "versions.yaml"
SCRIPTS_DIR = APP_DIR / "install" / "scripts"

ICON_FILE = APP_DIR / "assets" / "icon.svg"


def expand(path: str) -> str:
    """'~' ve $DEGISKEN ifadelerini açar."""
    return os.path.expandvars(os.path.expanduser(path))
