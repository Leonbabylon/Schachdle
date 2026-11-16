#!/usr/bin/env bash
# Downloads the official Stockfish 17.1 Linux build into ./stockfish/stockfish (used by the GitHub workflow).
# On macOS or Windows, install Stockfish yourself and set STOCKFISH=/path/to/it instead.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p stockfish && cd stockfish
curl -sSL -o sf.tar https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1/stockfish-ubuntu-x86-64-avx2.tar
tar xf sf.tar --strip-components=1
mv stockfish-ubuntu-x86-64-avx2 stockfish
rm sf.tar
./stockfish --help >/dev/null 2>&1 || true
echo "Stockfish ready at $(pwd)/stockfish"
