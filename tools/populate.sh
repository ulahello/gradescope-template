#!/usr/bin/env sh

if [ "${1}" = "-h" -o "${1}" = "--help" ]; then
	echo "Usage: ${0} <TEMPLATE_PATH> <DST>"
	echo
	echo "This script fills in missing files in DST with the autograding"
	echo "template at TEMPLATE_PATH. This template is expected to be a Git"
	echo "repository, which before copying, will be checked out to a commit"
	echo "hash or tag specified by the contents of the file 'CHECKOUT' in"
	echo "DST, then reset, then cleaned."
	exit 0
fi

if [ "${#}" -ne 2 ]; then
	echo "Error: expected exactly 3 arguments (try --help for help)."
	exit 1
fi


TEMPLATE="${1}"
DST="${2}"

TEMPLATE_VER="`cat "${DST}/CHECKOUT"`"

# get clean template state
pushd "${TEMPLATE}"
git checkout "${TEMPLATE_VER}"
git reset --hard
git clean -fdx
popd

# copy template to destination
cp -r --update=none "${TEMPLATE}/"* "${DST}"
# the script was probably renamed according to the naming convention,
# so we want to delete the version from the template.
if [ "`find "${DST}" -name "script_*.py" -type f | wc -l`" -gt 1 ]; then
	rm -v "${DST}/script_unit_section_exercise.py"
fi
