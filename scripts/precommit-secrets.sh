#!/usr/bin/env bash
# Blocks commits that contain likely secrets. Installed as the shared pre-commit hook
# by scripts/setup_worktrees.sh (hooks live in the common git dir, so all worktrees use it).

# 1) never commit a real .env file (.env.example is fine)
if git diff --cached --name-only | grep -E '(^|/)\.env(\.[A-Za-z0-9_-]+)?$' | grep -qv '\.env\.example$'; then
  echo "pre-commit: refusing to commit a .env file. Keep keys in .env (gitignored)." >&2
  exit 1
fi

# 2) scan added lines for key-shaped strings
KEYS='(tvly-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{20,}|(API_KEY|SECRET|TOKEN)[A-Z_]*[[:space:]]*[=:][[:space:]]*["'"'"']?[A-Za-z0-9._-]{24,})'
HITS="$(git diff --cached -U0 -- . ':(exclude)*.env.example' \
  | grep -E '^\+' | grep -Ev '^\+\+\+' \
  | grep -E "$KEYS" | grep -Eiv 'your|xxx|changeme|example|placeholder|<.*>' || true)"

if [ -n "$HITS" ]; then
  echo "pre-commit: possible secret in staged changes — move it to .env:" >&2
  echo "$HITS" | cut -c1-80 | sed 's/^/   /' >&2
  exit 1
fi
exit 0
