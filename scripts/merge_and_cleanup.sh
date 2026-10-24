#!/usr/bin/env bash
# Merge a worktree branch into main.
#   scripts/merge_and_cleanup.sh <name>           milestone merge: worktree stays, synced to main
#   scripts/merge_and_cleanup.sh <name> --final   merge, then delete the worktree + branch
# Uses a GitHub PR (gh) when origin + gh exist; otherwise a local --no-ff merge. USE_PR=0 forces local.
# Run it from the MAIN repo dir for --final (your shell must not be inside the worktree being deleted):
#   cd "$(git worktree list --porcelain | sed -n '1s/^worktree //p')"
set -euo pipefail

NAME="${1:?usage: $0 <name> [--final]}"
FINAL="${2:-}"
BR="feat/$NAME"

MAIN="$(git worktree list --porcelain | sed -n '1s/^worktree //p')"
WT="$(git worktree list --porcelain | awk -v b="refs/heads/$BR" '/^worktree /{p=substr($0,10)} $1=="branch" && $2==b {print p}')"
[ -n "$WT" ] || { echo "No worktree found for $BR" >&2; exit 1; }

# one merge at a time (mkdir lock works on macOS + Linux)
LOCK="$(git -C "$MAIN" rev-parse --path-format=absolute --git-common-dir)/praetor-merge.lock"
i=0
until mkdir "$LOCK" 2>/dev/null; do
  i=$((i+1)); [ "$i" -gt 60 ] && { echo "Another merge holds the lock: $LOCK" >&2; exit 3; }
  sleep 2
done
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

echo "› saving work in $NAME"
"$MAIN/scripts/autocommit.sh" "$WT" --once
[ -z "$(git -C "$WT" status --porcelain)" ] || { echo "Uncommitted changes remain in $WT (blocked commit?). Fix, re-run." >&2; exit 1; }
[ -z "$(git -C "$MAIN" status --porcelain)" ] || { echo "main has uncommitted changes. Nobody edits main directly — commit/stash them." >&2; exit 1; }
[ "$(git -C "$MAIN" rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "The main worktree must have main checked out." >&2; exit 1; }

HAVE_REMOTE=0
git -C "$MAIN" remote get-url origin >/dev/null 2>&1 && HAVE_REMOTE=1
if [ "$HAVE_REMOTE" = 1 ]; then git -C "$MAIN" pull -q --ff-only origin main || true; fi

echo "› rebasing $BR onto main"
if ! git -C "$WT" rebase -q main; then
  echo "Rebase conflict in $WT. Resolve, 'git rebase --continue', then re-run this script." >&2
  exit 2
fi

if [ -f "$WT/Makefile" ] && grep -q '^test-fast:' "$WT/Makefile" && [ "${SKIP_TESTS:-0}" != 1 ]; then
  echo "› make test-fast"
  make -C "$WT" test-fast
fi

if [ "$(git -C "$WT" rev-list --count "main..$BR")" = 0 ]; then
  echo "› nothing new to merge"
elif [ "$HAVE_REMOTE" = 1 ] && command -v gh >/dev/null 2>&1 && [ "${USE_PR:-1}" = 1 ]; then
  echo "› opening + merging PR"
  git -C "$WT" push -q -u origin "$BR" --force-with-lease
  ( cd "$WT" && { gh pr view "$BR" >/dev/null 2>&1 || gh pr create --base main --head "$BR" --fill; } && gh pr merge "$BR" --merge )
  git -C "$MAIN" pull -q --ff-only origin main
else
  echo "› merging locally"
  git -C "$MAIN" merge -q --no-ff "$BR" -m "merge: $NAME"
  if [ "$HAVE_REMOTE" = 1 ]; then git -C "$MAIN" push -q origin main || true; fi
fi

if [ "$FINAL" = "--final" ]; then
  git -C "$MAIN" merge-base --is-ancestor "$BR" main || { echo "$BR is not fully merged; refusing to delete." >&2; exit 1; }
  git -C "$MAIN" worktree remove --force "$WT"
  git -C "$MAIN" branch -d "$BR"
  if [ "$HAVE_REMOTE" = 1 ]; then git -C "$MAIN" push -q origin --delete "$BR" 2>/dev/null || true; fi
  git -C "$MAIN" worktree prune
  echo "✓ $NAME merged into main; worktree and branch removed."
else
  git -C "$WT" merge -q --ff-only main
  echo "✓ $NAME merged into main; worktree kept and synced."
fi
