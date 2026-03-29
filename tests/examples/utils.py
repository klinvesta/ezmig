import shutil
from pathlib import Path


def copy_example(name: str, destination: Path):
    root = Path(__file__).resolve().parents[2]
    src = root / "examples" / name

    shutil.copytree(src, destination, dirs_exist_ok=True)
