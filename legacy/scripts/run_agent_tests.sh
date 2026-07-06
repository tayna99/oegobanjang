#!/usr/bin/env bash
set -euo pipefail

uv run pytest backend/tests -k "agent or guardrail"