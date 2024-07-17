#!/usr/bin/env sh
rm -vf autograder.zip
7z a autograder.zip setup.sh run_autograder io_trace.py core.py cases.py util.py autograder_script.py
