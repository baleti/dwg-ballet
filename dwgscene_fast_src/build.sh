#!/bin/sh
# Build the optional native scene kernels and copy them next to the Python modules (dwgscene_fast.abi3.so, git-ignored). Without it everything runs in pure Python.
# Usage: dwgscene_fast_src/build.sh   (cargo, offline crates cache; about 15 s; run niced)
set -e
cd "$(dirname "$0")"
nice -n 19 cargo build --release --offline
cp target/release/libdwgscene_fast.so ../dwgscene_fast.abi3.so.tmp && mv -f ../dwgscene_fast.abi3.so.tmp ../dwgscene_fast.abi3.so
echo "built ../dwgscene_fast.abi3.so"
