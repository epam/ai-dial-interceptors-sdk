from pathlib import Path


def package_root_dir():
    return Path(__file__).parent.parent.parent
