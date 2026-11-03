#!/usr/bin/env bash
# Atualiza o snapshot da doc embutida a partir do site da lib (rode no monorepo).
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${1:-../doc/src/content/docs}"
[ -d "$SRC" ] || { echo "fonte não encontrada: $SRC"; exit 1; }
rm -rf jangada_docs_mcp/docs/*.mdx jangada_docs_mcp/docs/*.json jangada_docs_mcp/docs/js
cp "$SRC"/*.mdx "$SRC"/*.json jangada_docs_mcp/docs/
# pacote JavaScript/TypeScript (npm): subpasta js/, páginas 'js/<nome>'
if [ -d "$SRC/js" ]; then
  mkdir -p jangada_docs_mcp/docs/js
  cp "$SRC"/js/*.mdx "$SRC"/js/*.json jangada_docs_mcp/docs/js/
fi
find . -name '._*' -delete 2>/dev/null || true
echo "snapshot atualizado: $(ls jangada_docs_mcp/docs/*.mdx | grep -vc '\.en\.mdx') páginas PT (Python) + $(ls jangada_docs_mcp/docs/js/*.mdx 2>/dev/null | grep -vc '\.en\.mdx') (JS)"
