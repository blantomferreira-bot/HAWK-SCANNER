import sys
from pathlib import Path


def add_api_to_path() -> None:
    api_root = Path(__file__).resolve().parents[2] / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
