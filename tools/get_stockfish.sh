#!/usr/bin/env bash
# Downloads the official Stockfish 19 Linux build into ./stockfish/stockfish (used by the GitHub workflow).
# Stockfish 19 ships "universal" binaries that pick the best instruction set (AVX2, AVX-512, ...) at runtime.
# On macOS or Windows, install Stockfish yourself and set STOCKFISH=/path/to/it instead.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p stockfish && cd stockfish
curl -sSL -o sf.tar.gz https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-linux-x86-64-universal.tar.gz
tar xzf sf.tar.gz --strip-components=1
mv stockfish-linux-x86-64-universal stockfish
rm sf.tar.gz
./stockfish --help >/dev/null 2>&1 || true
echo "Stockfish ready at $(pwd)/stockfish"
