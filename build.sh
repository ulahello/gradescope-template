#!/usr/bin/env sh
rm -vf autograder.zip
zip autograder.zip setup.sh run_autograder \
    io_trace.py core.py cases.py recursion.py util.py autograder_script.py
