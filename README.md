# Jangada Docs MCP

Servidor **MCP** que dá ao seu assistente de IA (Claude Code, Claude Desktop,
Cursor…) acesso a **toda a documentação da biblioteca [jangada](https://github.com/nerigleston/jangada)**
(`jangada-ai`). Assim o assistente escreve código com a **API atual e correta** —
sem inventar nomes de função, assinaturas ou parâmetros.

> Feito **para desenvolvedores** que constroem com o `jangada`. É o próprio
> jangada **sendo um servidor MCP** (`serve_mcp`, protocolo stdio). A doc vem
> embutida (`./docs`) — self-contained, sem depender de rede.

---

## O que ele expõe (ferramentas)

| Ferramenta | Para que serve |
|-----------|----------------|
| `jangada_indice()` | Índice/ordem das páginas (Começando, Providers, Capacidades…). Comece aqui. |
| `jangada_listar_docs()` | Lista todas as páginas (nome — título). |
| `jangada_ler_doc(nome, lang)` | Conteúdo completo de uma página (`pt` padrão ou `en`). |
| `jangada_buscar(termo)` | Procura um termo em toda a doc (trechos + página). |

O assistente decide sozinho quando chamar — ex.: você pede "faça um RAG com
reranking" e ele consulta `jangada_ler_doc("rag")` antes de escrever.

---

## Instalação

```bash
git clone https://github.com/nerigleston/jangada-docs-mcp
cd jangada-docs-mcp
pip install -r requirements.txt        # = jangada-ai[mcp]
```

> Dica: use um venv (`python -m venv .venv && . .venv/bin/activate`). Anote o
> caminho do `python` desse venv para usar na configuração abaixo.

Teste rápido (deve aguardar em stdio, sem erro):

```bash
python server.py
```

---

## Conectar ao Claude Code

**Escopo de projeto** (recomendado — vale só naquele projeto, não no PC todo):
crie um arquivo `.mcp.json` na **raiz do seu projeto**:

```json
{
  "mcpServers": {
    "jangada-docs": {
      "command": "/caminho/para/python",
      "args": ["/caminho/para/jangada-docs-mcp/server.py"]
    }
  }
}
```

Ou pela CLI (escopo de projeto):

```bash
claude mcp add jangada-docs --scope project -- /caminho/para/python /caminho/para/jangada-docs-mcp/server.py
```

Use o `python` do venv onde você instalou os requirements e o caminho absoluto do
`server.py`. Reabra o Claude Code no projeto e pergunte algo sobre o jangada.

## Conectar ao Claude Desktop

Edite o `claude_desktop_config.json` (Settings → Developer → Edit Config) e
adicione:

```json
{
  "mcpServers": {
    "jangada-docs": {
      "command": "/caminho/para/python",
      "args": ["/caminho/para/jangada-docs-mcp/server.py"]
    }
  }
}
```

Reinicie o Claude Desktop.

## Conectar ao Cursor

Em `~/.cursor/mcp.json` (global) ou `.cursor/mcp.json` (projeto), use o mesmo
bloco `mcpServers` acima.

---

## Atualizar a documentação

A doc em `./docs` é um snapshot do site da lib. Para atualizar, troque os
arquivos por uma versão mais nova de
[`jangada/doc`](https://github.com/nerigleston/jangada) (ou rode o `sync` do
monorepo) e faça commit.

## Como funciona

`server.py` registra as funções acima como ferramentas MCP via
`jangada_ai.serve_mcp(...)` — construído sobre o `Server` **low-level** do
protocolo MCP (não FastMCP). Transporte **stdio** (o usado por Claude
Code/Desktop/Cursor). Para HTTP: `serve_mcp(..., transport="streamable-http")`.

## Licença

MIT — veja [LICENSE](LICENSE).
