#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bend PROOF.bend
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT
bend examples/capture.bend -o "$build_dir/capture"
actual=$("$build_dir/capture")
expected='64x64 16711680 65280 255 16777215'
if [[ "$actual" != "$expected" ]]; then
  printf 'Expected: %s\nObserved: %s\n' "$expected" "$actual" >&2
  exit 1
fi
printf 'PASS: dimensions, RGB quadrants, row order, and pixels after close\n'
