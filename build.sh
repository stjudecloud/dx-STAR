#!/usr/bin/env bash
# Builds resources and then invokes dx build to build the DNAnexus app.
#
# This invokes docker and dx, so be sure they are in your path.
#
# Usage: ./build.sh [--no-docker-build] VERS [DX_BUILD_ARGS...]
#
# Parameters:
# VERS:              the version you are trying to build
# DX_BUILD_ARGS      these arguments are passed to dx build
#
# The build performs the following operations:
# 1. Checks the dxapp.json to confirm the version matches VERS (fails if not)
# 2. Retrieves dependencies
# 3. Performs dx build

# Print usage instructions if no arguments were given
if [ "$#" == 0 ]; then sed -q '2,/^$/p' $0; exit 0; fi

# Get arguments
if [ "$1" == "--app" ]
then app_arg="--app"; shift
fi
VERS=$1
shift
# Remaining arguments are passed to dx build

# Validate version
dxapp_version=`cat dxapp.json | tr -d '\t "' | sed 's/,$//' | awk -F : '$1 == "version" { print $2; exit }'`
if [ "$VERS" != "$dxapp_version" ]
then
  echo "Version from dxapp.json is $dxapp_version, not $VERS" >&2
  exit 1
fi

set -ex

if [ ! -d resources ] 
then 
  mkdir -p resources
fi

if [ ! -d build ]
then
  mkdir build 
fi

cd build
curl -L -o star.tar.gz https://github.com/alexdobin/STAR/archive/2.7.1a.tar.gz
echo "4026d6d19a9aea62404b84dfab204c99  star.tar.gz" > star.md5
md5sum -c star.md5

tar -zxf star.tar.gz
cp STAR-2.7.1a/bin/Linux_x86_64_static/STAR ../resources/

curl -L -o sambamba.gz https://github.com/biod/sambamba/releases/download/v0.7.1/sambamba-0.7.1-linux-static.gz
echo "a47932d27f92a2639d4b228eb7847e04  sambamba.gz" > sambamba.md5
md5sum -c sambamba.md5

gunzip sambamba.gz
cp sambamba ../resources/

cd ..

echo dx build $app_arg "$@"
#dx build $app_arg "$@"
