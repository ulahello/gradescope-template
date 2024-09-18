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

SCRIPT="`find "${SCRIPT_DIR}" -name 'script_*.py' -type f | head -n 1`"
if [ "${SCRIPT}" = "" ]; then
	echo "${0}: Can't find an entry point! Does 'script_*.py' exist?"
	exit 1
fi

# ./script_unit_section_exercise.py -> ./zip_unit_section_exercise.zip
ZIP_NAME="`basename "${SCRIPT}" '.py'`"
ZIP_NAME="${ZIP_NAME#script_}"
ZIP_NAME="zip_${ZIP_NAME}.zip"
ZIP="${SCRIPT_DIR}/${ZIP_NAME}"

# remove old zip file
find "${DST}" -maxdepth 1 -name 'zip_*.zip' -delete

# add new zip file
# TODO: maybe i should just merge this into SOURCES
cd "${SCRIPT_DIR}"
zip "${ZIP_NAME}" setup.sh run_autograder \
    io_trace.py core.py cases.py util.py \
    ast_analyze.py ast_check.py pipeline.py \
    "`basename ${SCRIPT}`" \
    golden.py
cd -

# zip up sources
printf '%s\n' "${SOURCES}" | while read source; do
	if [ "${source}" != '' ]; then
		cd "${SCRIPT_DIR}"
		cp -vrn "${source}" .
		zip "${ZIP_NAME}" "`basename "${source}"`"
		cd -
	fi
done

mv -v "${ZIP}" "${DST}" || true
