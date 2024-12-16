from pathlib import PurePath
from typing import Dict, List

def read_sources(paths: List[str]) -> Dict[PurePath, str]:
    sources = {}
    for path in paths:
        with open(path, "r") as f:
            sources[PurePath(path)] = f.read()
    return sources
