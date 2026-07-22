#!/usr/bin/env bash
set -euo pipefail

README="README.md"
MAX=50

cd "$(git rev-parse --show-toplevel)"

generer_tableau() {
  echo "## Historique des commits"
  echo ""
  echo "| Hash | Date | Gitea | GitHub | Description |"
  echo "|------|------|-------|--------|-------------|"

  git log main -"$MAX" --format="%H %ai %s" | while read -r hash date time tz desc; do
    short="${hash:0:8}"
    date_only="${date}"
    gitea="non"
    github="non"
    if git merge-base --is-ancestor "$hash" gitea/main 2>/dev/null; then
      gitea="oui"
    fi
    if git merge-base --is-ancestor "$hash" github/main 2>/dev/null; then
      github="oui"
    fi
    echo "| \`$short\` | $date_only | $gitea | $github | $desc |"
  done
}

# Remplacer la section existante ou l'ajouter à la fin
if grep -q "^## Historique des commits" "$README"; then
  TMP=$(mktemp)
  sed '/^## Historique des commits/,$d' "$README" > "$TMP"
  generer_tableau >> "$TMP"
  mv "$TMP" "$README"
else
  echo "" >> "$README"
  generer_tableau >> "$README"
fi
