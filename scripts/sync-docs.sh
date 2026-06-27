#!/usr/bin/env bash
# Atualiza o snapshot da doc embutida a partir do site da lib (rode no monorepo).
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${1:-../doc/src/content/docs}"
[ -d "$SRC" ] || { echo "fonte não encontrada: $SRC"; exit 1; }
rm -f jangada_docs_mcp/docs/*.mdx jangada_docs_mcp/docs/*.json
cp "$SRC"/*.mdx "$SRC"/*.json jangada_docs_mcp/docs/
find . -name '._*' -delete 2>/dev/null || true
echo "snapshot atualizado: $(ls jangada_docs_mcp/docs/*.mdx | grep -vc '\.en\.mdx') páginas PT"
