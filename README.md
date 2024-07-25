# Untitled Gradescope Autograding Template!

This README is under construction!

## How do I test my autograding script?

This repository is laid out so that you can run [`script_*.py`](./script_unit_section_exercise.py) and it should work as expected.
It will look for submission files in [`submission/`](./submission/).
Once you've run it, take a look at [`results/results.json`](./results/results.json) for your output, as Gradescope will see it.

## How do I generate the ZIP file?

The zip file must contain the following:

1. `setup.sh`
2. `run_autograder`
3. Source code for the autograding script (probably `*.py`)

The [`build.sh`](./build.sh) script creates a conformant ZIP file, but only works on unix-like systems.

## License

This template is licensed under the [MIT No Attribution license](./LICENSE) (SPDX: `MIT-0`).

