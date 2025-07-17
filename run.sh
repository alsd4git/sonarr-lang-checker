#!/bin/sh
# Wrapper per eseguire lo script con uv e passare tutti gli argomenti

uv run "$(dirname "$0")/main.py" "$@"
