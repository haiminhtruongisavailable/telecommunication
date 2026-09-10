#!/bin/sh
# Clone upstream BookSim for the FCFS hop check. EDF stays in golden/hop.py.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/third_party"
if [ ! -d "$ROOT/third_party/booksim2/.git" ]; then
  git clone --depth 1 https://github.com/booksim/booksim2.git "$ROOT/third_party/booksim2"
fi
cd "$ROOT/third_party/booksim2/src"
make
echo "binary: $ROOT/third_party/booksim2/src/booksim"
