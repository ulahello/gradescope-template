from pathlib import PurePath, Path
from zipfile import ZipFile
import argparse
import os
import shutil
import subprocess
import sys

# TODO: what if dir exists in script dir but not respective files, so populate skips the whole thing

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

def read_checkout(script_dir: str) -> str:
    co_path = PurePath(script_dir, "CHECKOUT")
    with open(co_path, "r") as f:
        data = f.read()
        lines = data.splitlines(keepends=False)
        if len(lines) != 1:
            fatal(f"'{str(co_path)}' must contain exactly one line")
        [co] = lines
        return co

def find_scripts(script_dir: str) -> List[PurePath]:
    ls = []
    for entry in os.scandir(script_dir):
        if entry.name.startswith("script_") and entry.name.endswith(".py"):
            ls.append(PurePath(entry.path))
    return ls

def run(cwd: str, args: List[str]) -> None:
    info(f"running {' '.join(map(lambda arg: repr(arg), args))}")
    subprocess.check_call(args, cwd=cwd)

def copy_no_clobber(src: str, dst: str) -> None:
    dst_file = PurePath(dst, PurePath(src).name)
    # NOTE: not using atomic fs operations
    if not os.path.exists(dst_file):
        info(f"copying '{src}' to '{dst}'")
        if Path(src).is_dir():
            shutil.copytree(src, dst_file)
        else:
            shutil.copy2(src, dst_file)
    else:
        info(f"skipping '{src}' (already exists)")

def populate(template_path: str, dst: str) -> None:
    # read CHECKOUT
    checkout: str = read_checkout(dst)

    # perform checkout
    run(template_path, ["git", "checkout", checkout])

    # clean template state
    run(template_path, ["git", "reset", "--hard"])
    run(template_path, ["git", "clean", "-fdx"])

    # copy template contents to destination
    for entry in os.scandir(template_path):
        # skip dotfiles (this includes .git)
        if entry.name.startswith("."):
            continue
        assert entry.name != ".git", "unreachable"

        copy_no_clobber(entry.path, dst)

    # the script was probably renamed according to the naming convention,
    # so we want to delete the version from the template.
    scripts: List[PurePath] = find_scripts(dst)
    to_remove = ["script_unit_section_exercise.py", "script_test.py"]
    if len(to_remove) < len(scripts):
        for consider_remove in scripts:
            if consider_remove.name in to_remove:
                info(f"removing '{str(consider_remove)}'")
                os.remove(consider_remove)

    # parse SOURCES
    sources: List[str] = read_sources(dst)

    # copy SOURCES to destination
    old_cwd = os.getcwd()
    os.chdir(dst)
    for source_path in sources:
        copy_no_clobber(source_path, dst)
    os.chdir(old_cwd)

    info(f"successfully populated script directory '{dst}'")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="""
        Copy missing template files into a script directory.
        """,

        epilog="""
        The template repository is first checked out to the contents of the mandatory file "$DST/CHECKOUT"; see git-checkout(1) for valid contents.
        The paths of additional sources (relative to $DST) can be specified in each line of the optional file "$DST/SOURCES".
        """,
    )
    parser.add_argument("TEMPLATE_PATH", help="path to template git repository")
    parser.add_argument("DST", help="path to script directory")
    args = parser.parse_args()

    populate(args.TEMPLATE_PATH, args.DST)

if __name__ == "__main__":
    main()
