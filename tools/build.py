from pathlib import PurePath
from zipfile import ZipFile
import argparse
import os
import shutil
import sys

from typing import List, Optional, NoReturn, Tuple

def fatal(msg: str) -> NoReturn:
    print(f"Error: {msg}", file=sys.stderr)
    exit(1)

def info(msg: str) -> None:
    print(f"Info: {msg}", file=sys.stderr)

def read_sources(parent_dir: str) -> List[str]:
    path = PurePath(parent_dir, "SOURCES")
    sources: List[str] = []
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
    with ZipFile(zip_path, mode="w") as zipfile:
        # add hardcoded sources
        for file_name in [
                "io_trace.py",
                "core.py",
                "cases.py",
                "util.py",
                "ast_analyze.py",
                "ast_check.py",
                "pipeline.py",
                "golden.py",
                script_name,
        ]:
            file_path = PurePath(script_dir, file_name)
            with open(file_path, "r") as f:
                file_data = f.read()
            zipfile.writestr(file_name, file_data)
            info(f"added source '{file_name}'")

        # add SOURCES. we change the cwd because sources are relative to the script directory.
        old_cwd = os.getcwd()
        os.chdir(script_dir)
        for source_path in sources:
            source_name: str = PurePath(source_path).name
            with open(source_path, "r") as f:
                source_data = f.read()
            zipfile.writestr(source_name, source_data)
            info(f"added source '{source_path}'")
        os.chdir(old_cwd)

    info(f"successfully built ZIP at '{zip_path}'")

def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble a Gradescope compliant zip file.")
    parser.add_argument("SCRIPT_DIR", help="path to script directory where source files reside")
    parser.add_argument("DST", help="path to deposit zip file")
    args = parser.parse_args()

    build(args.SCRIPT_DIR, args.DST)

if __name__ == "__main__":
    main()
