#!/usr/bin/env bash
# Run the Lean verifier's controls natively: Comparator on each solution, then HoleCheck.lean when
# Comparator accepts. Usage: run.sh PROJECT, a Lake project with the pinned package built
# (lakefile.toml with the libraries MCAChallenge, Challenge and Submission, `lake build MCAChallenge`
# done) and comparator, lean4export and landrun on PATH (on macOS, Comparator's
# scripts/fake-landrun.sh as `landrun`, which sandboxes nothing: development only).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
PROJECT=$(cd "$1" && pwd)
HOLECHECK=$HERE/../templates/lean/tests/HoleCheck.lean
export LEAN_NUM_THREADS=${LEAN_NUM_THREADS:-4}
cd "$PROJECT"
cp "$HERE/config.json" config.json
cp "$HERE/Control.lean" Challenge.lean
run_case() {
  name=$1; solution=$2; expect=$3
  cp "$solution" Submission.lean
  find .lake/build -name 'Challenge*' -delete 2>/dev/null; find .lake/build -name 'Submission*' -delete 2>/dev/null
  start=$(date +%s)
  lake env comparator config.json > "control-$name.log" 2>&1; code=$?
  secs=$(( $(date +%s) - start ))
  if [ $code -eq 0 ] && grep -q "Your solution is okay" "control-$name.log"; then
    lake env lean "$HOLECHECK" > "control-$name-holes.log" 2>&1 && verdict="accepted, holes ok" || verdict="accepted, holes denied"
  else
    verdict="refused: $(grep -oE "Illegal axiom detected: '[^']*'|statement do not match|build failed" "control-$name.log" | head -1)"
  fi
  [ "$verdict" = "$expect" ] && mark=ok || mark=UNEXPECTED
  echo "$mark  $name (${secs}s): $verdict | expected: $expect"
}
run_case ok     "$HERE/solutions/ok.lean"     "accepted, holes ok"
run_case sorry  "$HERE/Control.lean"          "refused: Illegal axiom detected: 'sorryAx'"
run_case weak   "$HERE/solutions/weak.lean"   "refused: statement do not match"
run_case choice "$HERE/solutions/choice.lean" "accepted, holes denied"
