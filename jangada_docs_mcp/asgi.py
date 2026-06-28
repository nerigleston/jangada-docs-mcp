"""App ASGI para deploy HTTP (uvicorn / AWS Lambda Web Adapter).

Serve as ferramentas de documentação via **streamable-HTTP**, em modo
**stateless** (sem sessão `Mcp-Session-Id`, respostas JSON) — o que um ambiente
por-invocação como a AWS Lambda precisa. É o próprio jangada sendo servidor MCP
(`build_mcp_app`), não um framework externo.

O entrypoint stdio (uvx/Claude Code) continua em `server.py:main` — este módulo
só é usado no deploy HTTP.
"""
from __future__ import annotations

from jangada_ai import build_mcp_app

from .server import (
    jangada_buscar,
    jangada_indice,
    jangada_ler_doc,
    jangada_listar_docs,
)

app = build_mcp_app(
    "jangada-mcp",
    tools=[jangada_indice, jangada_listar_docs, jangada_ler_doc, jangada_buscar],
    path="/mcp",
    json_response=True,
    stateless=True,
)
