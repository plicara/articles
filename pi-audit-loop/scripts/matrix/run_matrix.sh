#!/usr/bin/env bash
# Run one audit-loop session per (fixture, model) and save transcript + session log.
#
# Usage: run_matrix.sh "<fixture>:<model-id>:<label>" ["<fixture>:<model-id>:<label>" ...]
#
# Example:
#   run_matrix.sh "A-bug:opencode-go/deepseek-v4.1-flash:deepseek-r1"
set -u

ROOT=${AUDIT_ROOT:?set AUDIT_ROOT to the directory that holds pkg/, matrix/ and dogfood/}
PKG="$ROOT/pkg"
RUNS="$ROOT/matrix/runs"
PY="$ROOT/ts/.venv/bin/python"
mkdir -p "$RUNS"

_read_prompt() {
  cat <<EOF
The audit loop tools are available (audit_loop_start, audit_review, audit_simplify, audit_loop_stop, audit_loop_status) and the code-review and code-simplification skills are loaded.

Start exactly one loop with audit_loop_start(scope="src, tests", test_command="PYTHONPATH=. $PY -m unittest discover -s tests -q").

Then follow the phase guidance exactly as the extension returns it — call the tool it says is expected next, wrong-phase calls are rejected.

Review phases: actually read the in-scope code and the tests in tests/, run the verification command with bash before recording a clean verdict, report findings honestly.

Simplify phases: only behavior-preserving changes, run the verification command after each change.

Do not stop early — continue until the extension reports the loop complete, then call audit_loop_status and summarize what was found and changed.

Do not read any file outside the current working directory.
EOF
}

for spec in "$@"; do
  fixture="${spec%%:*}"
  rest="${spec#*:}"
  model="${rest%%:*}"
  label="${rest#*:}"

  dir="$RUNS/../fixtures/$fixture"
  out="$RUNS/${fixture}-${label}.out"
  # Every run must start from the committed pristine fixture: a prior run may
  # have simplified the code, which would silently invalidate the next one.
  git -C "$dir" checkout -- . 2>/dev/null
  echo "=== $fixture | $model | $label"
  ( cd "$dir" && pi -p -e "$PKG" -nc --model "$model" \
      --session-dir "$RUNS" --name "${fixture}-${label}" "$(_read_prompt)" ) >"$out" 2>&1
  echo "    exit=$? -> $out"
done
