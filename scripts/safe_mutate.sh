#!/bin/bash
# Mutation testing without destroying uncommitted work.
#
# WHY THIS EXISTS. Three times in one session, a mutation test was reverted
# with `git checkout <file>` — which restores the file to HEAD and therefore
# throws away every uncommitted change in it, not just the mutation. It cost
# the `_fitting_slots` implementation once and eleven Library cards once.
#
# `git checkout` is the wrong tool because it reverts to the LAST COMMIT, and
# during development the thing you are mutating is usually itself uncommitted.
# The right move is to snapshot first and restore from the snapshot.
#
#   bash scripts/safe_mutate.sh save missiongen/bfm.py
#   ...apply the mutation, run the tests, watch them fail...
#   bash scripts/safe_mutate.sh restore missiongen/bfm.py
#
# `save` refuses to overwrite an existing snapshot, so a second `save` before a
# `restore` cannot destroy the good copy either.
set -euo pipefail

SNAP_DIR="${TMPDIR:-/tmp}/ss-mutation-snapshots"
mkdir -p "$SNAP_DIR"

usage() { echo "usage: $0 {save|restore|list|clean} [file...]" >&2; exit 2; }
[ $# -ge 1 ] || usage
op="$1"; shift

snap_for() { echo "$SNAP_DIR/$(echo "$1" | tr '/' '_')"; }

case "$op" in
  save)
    [ $# -ge 1 ] || usage
    for f in "$@"; do
      s="$(snap_for "$f")"
      if [ -e "$s" ]; then
        echo "REFUSING: a snapshot of $f already exists ($s)." >&2
        echo "          Restore it first, or 'clean' if you are sure." >&2
        exit 1
      fi
      cp "$f" "$s"
      echo "saved  $f"
    done
    ;;
  restore)
    [ $# -ge 1 ] || usage
    for f in "$@"; do
      s="$(snap_for "$f")"
      [ -e "$s" ] || { echo "no snapshot for $f" >&2; exit 1; }
      cp "$s" "$f"
      rm -f "$s"
      echo "restored  $f"
    done
    ;;
  list)   ls -la "$SNAP_DIR" 2>/dev/null || echo "(no snapshots)" ;;
  clean)  rm -rf "$SNAP_DIR"; echo "cleared" ;;
  *)      usage ;;
esac
