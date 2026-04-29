"""
src/utils/config_loader.py
Carga la configuración central desde config/config.yaml
"""

import yaml
from pathlib import Path
from functools import lru_cache


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_config(config_path: str | None = None) -> dict:
    """Carga y cachea el archivo config.yaml."""
    path = Path(config_path) if config_path else PROJECT_ROOT / "config" / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    # Resolver rutas relativas desde la raíz del proyecto
    for section in ("paths",):
        if section in config:
            _resolve_paths(config[section], PROJECT_ROOT)
    return config


def _resolve_paths(node: dict | str, root: Path) -> None:
    """Convierte strings de rutas en Path absolutos recursivamente."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                node[k] = root / v
            elif isinstance(v, dict):
                _resolve_paths(v, root)


def get_path(section: str, key: str) -> Path:
    """Shortcut para acceder a rutas del config."""
    config = load_config()
    path: Path = config["paths"][section][key]
    path.mkdir(parents=True, exist_ok=True)
    return path
