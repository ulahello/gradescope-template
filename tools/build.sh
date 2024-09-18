#!/usr/bin/env sh
set -e

if [ "${1}" = "-h" -o "${1}" = "--help" ]; then
	echo "Usage: ${0} <SCRIPT_DIR> <DST>"
	echo
	echo "This script zips up relevant files from the script directory"
	echo "SCRIPT_DIR into a Gradescope compliant zip file, which will"
	echo "then be deposited to DST."
	exit 0
fi

if [ "${#}" -ne 2 ]; then
	echo "Error: expected exactly 2 arguments (try --help for help)."
	exit 1
fi

SCRIPT_DIR="${1}"
DST="${2}"
SOURCES="`cat "${SCRIPT_DIR}/SOURCES" || true`"

cd "${SCRIPT_DIR}"
SCRIPT="`find . -name 'script_*.py' -type f | head -n 1`"
if [ "${SCRIPT}" = "" ]; then
	echo "${0}: Can't find an entry point! Does 'script_*.py' exist?"
	exit 1
fi

# ./script_unit_section_exercise.py -> ./zip_unit_section_exercise.zip
ZIP="`basename "${SCRIPT}" '.py'`"
ZIP="${ZIP#script_}"
ZIP="./zip_${ZIP}.zip"

# TODO: maybe i should just merge this into SOURCES
rm -vf autograder.zip zip_*.zip
zip "${ZIP}" setup.sh run_autograder \
    io_trace.py core.py cases.py util.py \
    ast_analyze.py ast_check.py pipeline.py \
    "${SCRIPT}" \
    golden.py

# zip up sources
printf '%s\n' "${SOURCES}" | while read source; do
	if [ "${source}" != '' ]; then
		cp -vr --update=none "${source}" "${DST}"
		zip "${ZIP}" "`basename "${source}"`"
	fi
done

cd -
mv -v "${SCRIPT_DIR}/${ZIP}" "${DST}" || true
