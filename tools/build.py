from pathlib import PurePath
from zipfile import ZipFile, ZipInfo
import argparse
import os
import shutil
import sys
import zipfile

from typing import List, Optional, NoReturn, Tuple, Set

def fatal(msg: str) -> NoReturn:
    print(f"Error: {msg}", file=sys.stderr)
    exit(1)

def info(msg: str) -> None:
    print(f"Info: {msg}", file=sys.stderr)

def read_sources(parent_dir: str) -> List[str]:
    path = PurePath(parent_dir, "SOURCES")
    sources = []
    with open(path, "r") as f:
        for line in f.read().splitlines(keepends=False):
            sources.append(line)
    return sources

def find_script(script_dir: str) -> Optional[Tuple[str, str]]:
    for entry in os.scandir(script_dir):
        if entry.name.startswith("script_") and entry.name.endswith(".py"):
            return (entry.path, entry.name)
    return None

def get_zip_name(script_name: str) -> str:
    new_name: str = "zip_" + script_name.removeprefix("script_")
    return PurePath(script_name).with_name(new_name).with_suffix(".zip").name

def det_zipinfo(filename: str, algo: int, level: int) -> ZipInfo:
    info = ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = algo
    # XXX: can't set compression level? also why do i have to specify algo here if i already do for the whole ZipFile?? maybe i should read the ZIP spec
    return info

def add_to_zip(zf: ZipFile, script_dir: str, sources: List[str], algo: int, level: int) -> None:
    def add_file_contents(zf: ZipFile, path: PurePath, algo: int, level: int) -> None:
        with open(path, "r") as f:
            file_data = f.read()
        zf.writestr(det_zipinfo(path.name, algo, level), file_data)
        info(f"added source '{path.name}'")

    to_add: Set[str | PurePath] = {
        "setup.sh",
        "run_autograder",
    }

    # queue all python source code
    for entry in os.scandir(script_dir):
        if entry.name.endswith(".py") and entry.is_file():
            to_add.add(entry.name)

    # queue all files in SOURCES
    for fname in sources:
        to_add.add(fname)

    # make queue real
    to_add_ordered: List[str | PurePath] = list(to_add)
    to_add_ordered.sort()
    for name in to_add_ordered:
        path = PurePath(script_dir, name)
        add_file_contents(zf, path, algo, level)

assert get_zip_name("script_foo.whatever") == "zip_foo.zip"
assert get_zip_name("script_unit_section_exercise.py") == "zip_unit_section_exercise.zip"

def build(script_dir: str, dst: str) -> None:
    # parse SOURCES
    sources: List[str] = read_sources(script_dir)

    # find script
    script: Optional[Tuple[str, str]] = find_script(script_dir)
    if script is None:
        fatal(f"cannot find script in path '{script_dir}'")
    script_path, script_name = script

    # get the zip path
    # ex. ./script_unit_section_exercise.py -> ./zip_unit_section_exercise.zip
    zip_name: str = get_zip_name(script_name)
    zip_path: PurePath = PurePath(dst, zip_name)

    # remove the old zip file
    try:
        os.remove(zip_path)
        info(f"removed old zip '{zip_path}'")
    except FileNotFoundError:
        pass

    # construct zip file
    for algo, level in [
            (zipfile.ZIP_DEFLATED, 9),
            (zipfile.ZIP_BZIP2, 9),
            (zipfile.ZIP_LZMA, -1),
            (zipfile.ZIP_STORED, -1),
    ]:
        try:
            with ZipFile(zip_path, mode="w",
                         compression=algo, compresslevel=level) as zf:
                add_to_zip(zf, script_dir, sources, algo, level)

            info(f"successfully built ZIP '{str(zip_path)}' ({algo=}, {level=})")
            return

        except RuntimeError:
            continue

    fatal("no suitable compression method found. this is a bug.")

def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble a Gradescope compliant zip file. If not all source files are present, you must run 'populate.py' first.")
    parser.add_argument("SCRIPT_DIR", help="path to script directory where source files reside")
    parser.add_argument("DST", help="path to deposit zip file")
    args = parser.parse_args()

    build(args.SCRIPT_DIR, args.DST)

if __name__ == "__main__":
    main()
