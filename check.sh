#!/usr/bin/env bash
# 阵容码盒 canonical 验证:解析单测 + 浏览器冒烟(本地 file:// 模式)
set -e
cd "$(dirname "$0")"
echo "== extract 单测 =="
node test-extract.js
echo "== 浏览器冒烟(file://) =="
/tmp/pwenv/bin/python smoke.py
echo "== ALL GREEN =="
