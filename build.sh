#!/usr/bin/env sh
rm -vf autograder.zip
7z a autograder.zip setup.sh run_autograder main.py io_trace.py
