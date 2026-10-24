#!/usr/bin/env bash
# Create one git worktree + branch per parallel Claude Code terminal.
# Run from the main repo, on a clean `main`:
#   scripts/setup_worktrees.sh                 # all default terminals
#   scripts/setup_worktrees.sh frontend api-infra   # just these
# Worktrees land in ../<repo>-wt/<name> on branch feat/<name>.
set -euo pipefail

MAIN="$(git worktree list --porcelain | sed -n '1s/^worktree //p')"
cd "$MAIN"

[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "Check out main first (git branch -M main if needed)." >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "Commit or stash changes on main first." >&2; exit 1; }

WT_DIR="${WT_DIR:-$(dirname "$MAIN")/$(basename "$MAIN")-wt}"
NAMES="${*:-llm-ledger recon-twin attack-engine remediate-league api-infra frontend agent-shell docs-demo}"

# secret-scan hook (shared by every worktree)
HOOKS="$(cd "$(git rev-parse --git-common-dir)" && pwd)/hooks"
mkdir -p "$HOOKS"
cp "$MAIN/scripts/precommit-secrets.sh" "$HOOKS/pre-commit"
chmod +x "$HOOKS/pre-commit"

mkdir -p "$WT_DIR"
for n in $NAMES; do
  if [ -d "$WT_DIR/$n" ]; then echo "skip   $n (already exists)"; continue; fi
  git worktree add -q -b "feat/$n" "$WT_DIR/$n" main
  echo "ready  $WT_DIR/$n   (branch feat/$n)"
done

echo
echo "Next:  scripts/autocommit.sh --all     (leave running in its own tab)"
echo "Then:  cd $WT_DIR/<name> && claude     (one terminal per worktree)"
