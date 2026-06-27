"""Servidor MCP da documentação do jangada — para DESENVOLVEDORES.

Pluga no seu projeto (Claude Code, Cursor, Claude Desktop) e dá ao assistente
acesso a TODA a documentação da lib `jangada` — para ele escrever código correto
com a API atual (sem chutar nomes de função/assinaturas).

É o próprio jangada **sendo um servidor MCP** (`serve_mcp`, protocolo stdio).
Self-contained: a doc vive em `./docs` (cópia do site, `.mdx` PT/EN).

Ferramentas expostas:
  - jangada_indice()            -> índice/ordem das páginas (meta.json)
  - jangada_listar_docs()       -> todas as páginas (nome — título)
  - jangada_ler_doc(nome, lang) -> conteúdo completo de uma página (pt|en)
  - jangada_buscar(termo)       -> procura o termo em toda a doc (trechos + página)

Rodar à mão:   python server.py
No Claude Code: ver .mcp.json (escopo de projeto) e o README.md.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jangada_ai import serve_mcp

DOCS = Path(__file__).resolve().parent / "docs"

_FM_TITLE = re.compile(r'^title:\s*"?(.+?)"?\s*$', re.MULTILINE)


def _frontmatter_title(md: str, fallback: str) -> str:
    if md.startswith("---"):
        fim = md.find("---", 3)
        if fim != -1:
            m = _FM_TITLE.search(md[3:fim])
            if m:
                return m.group(1).strip()
    return fallback


def _pt_pages() -> list[Path]:
    # páginas PT = *.mdx exceto *.en.mdx
    return sorted(p for p in DOCS.glob("*.mdx") if not p.name.endswith(".en.mdx"))


def jangada_indice() -> str:
    """Índice da documentação do jangada: as páginas na ordem das seções
    (Começando, Providers, Capacidades, Confiabilidade, etc.). Comece por aqui."""
    meta = DOCS / "meta.json"
    if not meta.exists():
        return jangada_listar_docs()
    pages = json.loads(meta.read_text(encoding="utf-8", errors="ignore")).get("pages", [])
    linhas = []
    for p in pages:
        if p.startswith("---") and p.endswith("---"):
            linhas.append(f"\n### {p.strip('- ')}")
        else:
            linhas.append(f"- {p}")
    return "\n".join(linhas)


def jangada_listar_docs() -> str:
    """Lista todas as páginas de documentação (nome do arquivo — título)."""
    linhas = []
    for f in _pt_pages():
        try:
            titulo = _frontmatter_title(f.read_text(encoding="utf-8", errors="ignore"), f.stem)
        except OSError:
            titulo = f.stem
        linhas.append(f"- {f.stem} — {titulo}")
    return "\n".join(linhas) or "nenhuma página encontrada"


def jangada_ler_doc(nome: str, lang: str = "pt") -> str:
    """Conteúdo completo de uma página. `nome` = arquivo (com ou sem .mdx),
    ex.: 'rag', 'mcp', 'eval', 'agents', 'structured-output'. `lang`: 'pt' (padrão)
    ou 'en'."""
    nome = nome.strip().removesuffix(".mdx").removesuffix(".en")
    arquivo = DOCS / (f"{nome}.en.mdx" if lang == "en" else f"{nome}.mdx")
    if not arquivo.exists():
        disponiveis = ", ".join(p.stem for p in _pt_pages())
        return f"página '{nome}' ({lang}) não existe. Disponíveis: {disponiveis}"
    return arquivo.read_text(encoding="utf-8", errors="ignore")


def jangada_buscar(termo: str, max_resultados: int = 30) -> str:
    """Procura um termo (case-insensitive) em toda a documentação PT e devolve as
    linhas que casam, agrupadas por página. Útil para achar 'como faço X'."""
    termo_l = termo.lower()
    saida: list[str] = []
    achados = 0
    for f in _pt_pages():
        try:
            linhas = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        hits = [ln.strip() for ln in linhas if termo_l in ln.lower()]
        if hits:
            saida.append(f"## {f.stem}")
            for h in hits[:8]:
                saida.append(f"  {h}")
                achados += 1
                if achados >= max_resultados:
                    saida.append("… (truncado; refine o termo ou abra a página)")
                    return "\n".join(saida)
    return "\n".join(saida) or f"nenhum resultado para '{termo}'"


def main() -> None:
    """Entry point (console script `jangada-docs-mcp`): sobe o servidor por stdio."""
    serve_mcp(
        "jangada-docs",
        tools=[jangada_indice, jangada_listar_docs, jangada_ler_doc, jangada_buscar],
    )


if __name__ == "__main__":
    main()
