#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${OPENINDEX_DEV_VENV:-$ROOT_DIR/.venv}"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install -r "$ROOT_DIR/requirements/dev.txt" >/dev/null

export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/src:$ROOT_DIR/src/api:${PYTHONPATH:-}"

cd "$ROOT_DIR"
pytest -q tests
