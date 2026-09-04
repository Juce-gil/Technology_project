#!/bin/sh
set -eu

cd "$(dirname "$0")"

if [ -z "${SMARTCAR_PANEL_TOKEN:-}" ]; then
    echo "请先设置控制面板密码："
    echo "  export SMARTCAR_PANEL_TOKEN='请替换为强密码'"
    exit 1
fi

export PYTHONPATH="$(pwd)"
exec python3 tools/control_panel.py --host 0.0.0.0 --port 8080
