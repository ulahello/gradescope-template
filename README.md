# Untitled Gradescope Autograding Template!

This README is under construction!

## What is the shape of this system?

TODO: add some example scripts to make this clearer

This template closely follows the shape of the [Gradescope API specification](https://gradescope-autograders.readthedocs.io/en/latest/specs/).
I strongly recommend reading this, and maybe even playing around with it to get a feel for how it works.
At the highest level, we're reading some student submitted file(s) and writing JSON to [`results/results.json`](./results/results.json).
Gradescope promises to read this and show a prettier and possibly truncated version of this to the student, as feedback for their submission.

Zooming in a little, this feedback consists of a sequence of test cases.
Cases are the basic building blocks of the template (in code this is the `Case` class).
This is a shared concept between the Gradescope API and this template, so many `Case` fields are directly passed to it.

It is the responsibility of the script author to produce a sequence of test cases (see `get_test_cases`; it may be helpful to read the function [`autograder_main`](./core.py)).
The `Case` class isn't useful on its own, since it doesn't *do* anything, it's just an interface.
Instead, you can use the subclasses defined in [`cases.py`](./cases.py) to evaluate the submission.
If the functionality you're looking for isn't present or is inadequate, you can totally write your own subclasses and use them in your scripts!

## How do I test my autograding script?

This repository is laid out so that you can run [`script_*.py`](./script_unit_section_exercise.py) and it should work as expected.
It will look for submission files in [`submission/`](./submission/).
Once you've run it, take a look at [`results/results.json`](./results/results.json) for your output, as Gradescope will see it.

## How do I generate the ZIP file?

The zip file must contain the following:

1. `setup.sh`
2. `run_autograder`
3. Source code for the autograding script (probably `*.py`)

The [`build.sh`](./tools/build.sh) script creates a conformant ZIP file, but only works on unix-like systems.

## License

This template is licensed under the [MIT No Attribution license](./LICENSE) (SPDX: `MIT-0`).

