#!/usr/bin/env sh
rm -vf autograder.zip zip_*.zip

SCRIPT="`find . -name 'script_*.py' -type f | head -n 1`"
if [ "${SCRIPT}" = "" ]; then
	echo "${0}: Can't find an entry point! Does 'script_*.py' exist?"
	exit 1
fi

# ./script_unit_section_exercise.py -> ./zip_unit_section_exercise.zip
ZIP="`basename "${SCRIPT}" '.py'`"
ZIP="${ZIP#script_}"
ZIP="./zip_${ZIP}.zip"

zip "${ZIP}" setup.sh run_autograder \
    io_trace.py core.py cases.py recursion.py pipeline.py util.py "${SCRIPT}"
