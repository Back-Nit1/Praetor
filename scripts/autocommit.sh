#!/usr/bin/env bash
# Auto-commit every 4 minutes (override with AUTOCOMMIT_SECONDS).
#   scripts/autocommit.sh --all            every feat/* worktree (run from the main repo)
#   scripts/autocommit.sh <worktree-path>  one worktree
#   add --once as 2nd arg for a single pass instead of a loop
set -uo pipefail

INTERVAL="${AUTOCOMMIT_SECONDS:-240}"
TARGET="${1:-}"
ONCE=""
[ -n "$TARGET" ] || { echo "usage: $0 --all|<worktree-path> [--once]" >&2; exit 1; }
[ "${2:-}" = "--once" ] && ONCE=1

tick() {
  local dir="$1" branch p
  branch="$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)" || return 0
  case "$branch" in feat/*) ;; *) return 0 ;; esac

  # never touch a worktree that is mid-rebase / mid-merge
  for p in rebase-merge rebase-apply MERGE_HEAD; do
    if ( cd "$dir" && [ -e "$(git rev-parse --git-path "$p")" ] ); then return 0; fi
  done

  if [ -n "$(git -C "$dir" status --porcelain)" ]; then
    git -C "$dir" add -A
    if git -C "$dir" commit -q -m "wip(${branch#feat/}): autosave $(date +%H:%M)"; then
      echo "[$(date +%H:%M:%S)] committed  ${branch#feat/}"
    else
      echo "[$(date +%H:%M:%S)] BLOCKED    ${branch#feat/} (secret scan?) — fix it; retrying next tick" >&2
      git -C "$dir" reset -q
    fi
  fi
}

list_dirs() {
  if [ "$TARGET" = "--all" ]; then
    git worktree list --porcelain | sed -n 's/^worktree //p'
  else
    echo "$TARGET"
  fi
}

pass() { while IFS= read -r d; do tick "$d"; done < <(list_dirs); }

if [ -n "$ONCE" ]; then pass; exit 0; fi
echo "[autocommit] every ${INTERVAL}s — Ctrl-C to stop"
while true; do sleep "$INTERVAL"; pass; done
