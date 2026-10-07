#!/bin/sh
# Build the Stwo reference entry: copy the crate into a proving tree at the frontier commit,
# add it to the workspace, build, and copy the binary here.
#   ./build.sh /path/to/proving   (a checkout of starknet-innovation/proving at 6e80156f)
set -eu
TREE=$1
HERE=$(cd "$(dirname "$0")" && pwd)
test "$(git -C "$TREE" rev-parse HEAD)" = 6e80156fb698bb9775240458304ac119db035aba
mkdir -p "$TREE/crates/chain_bench"
cp -R "$HERE/crate/." "$TREE/crates/chain_bench/"
python3 - "$TREE/Cargo.toml" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
anchor = 'members = [\n'
if '"crates/chain_bench"' not in text:
    assert text.count(anchor) == 1
    open(path, "w").write(text.replace(anchor, anchor + '    "crates/chain_bench",\n', 1))
PY
(cd "$TREE" && RUSTFLAGS="-C target-cpu=native" cargo build --release -p chain-bench)
cp "$TREE/target/release/chain" "$HERE/chain"
