#!/usr/bin/env bash
# Dogfood: run the audit loop on a real project the way a user would.
#
# A fresh copy of the project is made per run, so runs cannot contaminate each
# other and the original is never touched.
#
# usage: run.sh <pristine-dir> <label> <model> <scope> <test_command>
set -u

SRC=$1; LABEL=$2; MODEL=$3; SCOPE=$4; TESTCMD=$5
ROOT=${AUDIT_ROOT:?set AUDIT_ROOT to the directory that holds pkg/, matrix/ and dogfood/}
RUNS="$ROOT/dogfood/runs"
mkdir -p "$RUNS"

DIR="$ROOT/dogfood/$LABEL"
rm -rf "$DIR"
cp -R "$SRC" "$DIR"

read -r -d '' PROMPT <<EOF
Audit this project with the audit loop.

Start with: audit_loop_start(scope="$SCOPE", test_command="$TESTCMD")

Then follow the phase guidance exactly as the extension returns it — call the tool it says is expected next; wrong-phase calls are rejected.

Review phases: actually read the in-scope code and its tests, and run the verification command with bash before recording a clean verdict. Report findings honestly.

Simplify phases: only behavior-preserving changes, and run the verification command after each change.

Continue until the extension reports the loop complete, then call audit_loop_status and summarize what you found and changed.
EOF

cd "$DIR" || exit 1
pi -p -e "$ROOT/pkg" --model "$MODEL" \
   --session-dir "$RUNS" --name "$LABEL" "$PROMPT" >"$RUNS/$LABEL.out" 2>&1
echo "$LABEL: exit=$? -> $RUNS/$LABEL.out"
