#!/usr/bin/env bash

set -euo pipefail

pytest -q \
  tests/test_api_fastapi.py \
  tests/test_api_smoke_critical.py \
  tests/test_db_backend_feature_flag.py \
  tests/test_frontend_structure.py \
  "$@"
