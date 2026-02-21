#!/usr/bin/env bash
set -euo pipefail

: "${OPENAI_MODEL:=gpt-5}"

qldpcwatch update --download-pdfs --rebuild-site "$@"
