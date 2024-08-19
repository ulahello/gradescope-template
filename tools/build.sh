#!/usr/bin/env sh
set -e

if [ "${1}" = "-h" -o "${1}" = "--help" ]; then
	echo "Usage: ${0} <TEMPLATE_DIR> <DST>"
	echo
	echo "This script zips up relevant files from the script/template"
	echo "directory TEMPLATE_DIR into a Gradescope compliant zip file,"
	echo "which will then be deposited to DST."
	exit 0
fi

if [ "${#}" -ne 2 ]; then
	echo "Error: expected exactly 2 arguments (try --help for help)."
	exit 1
fi

TEMPLATE_DIR="${1}"
DST="${2}"

SOURCES="`cat "${TEMPLATE_DIR}/SOURCES" || true`"

cd "${TEMPLATE_DIR}"

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
    io_trace.py core.py cases.py recursion.py pipeline.py util.py "${SCRIPT}" \
    golden.py

# zip up sources
printf '%s\n' "${SOURCES}" | while read source; do
	if [ "${source}" != '' ]; then
		cp -vr --update=none "${source}" "${DST}"
		zip "${ZIP}" "`basename "${source}"`"
	fi
done

cd -
mv -v "${TEMPLATE_DIR}/${ZIP}" "${DST}"
