#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 -m venv .venv
vitals_requirements=requirements.txt
if [[ -f requirements-lock.txt ]]; then vitals_requirements=requirements-lock.txt; fi
.venv/bin/python -m pip install --index-url https://mirrors.aliyun.com/pypi/simple -r "$vitals_requirements"
.venv/bin/python -m pip check
.venv/bin/python -m pip freeze > requirements-lock.txt
python3 scripts/fetch_sources.py
.venv/bin/python scripts/audit_mtts.py
