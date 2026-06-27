# Jangada Docs MCP

Servidor **MCP** que dá ao seu assistente de IA (Claude Code, Claude Desktop,
Cursor…) acesso a **toda a documentação da biblioteca [jangada](https://github.com/nerigleston/jangada)**
(`jangada-ai`). Assim o assistente escreve código com a **API atual e correta** —
sem inventar nomes de função, assinaturas ou parâmetros.

> Feito **para desenvolvedores** que constroem com o `jangada`. É o próprio
> jangada **sendo um servidor MCP** (`serve_mcp`, protocolo stdio). A doc vem
> embutida no pacote — self-contained, sem depender de rede em runtime.

---

## Jeito mais fácil: `uvx` (sem clonar nada)

Como o `npx` do Node, o **`uvx`** roda o servidor direto do GitHub — **sem clonar,
sem instalar manualmente**. Só precisa do [`uv`](https://docs.astral.sh/uv/)
(`curl -LsSf https://astral.sh/uv/install.sh | sh`).

Comando que as configurações abaixo usam:

```bash
uvx --from git+https://github.com/nerigleston/jangada-docs-mcp jangada-docs-mcp
```

(O `uvx` baixa, monta e roda o pacote numa sandbox temporária a cada uso.)

---

## Claude Code

### Em um projeto específico (escopo do projeto)

Vale **só naquele projeto** (ideal para times — pode commitar). Crie um
`.mcp.json` na **raiz do projeto**:

```json
{
  "mcpServers": {
    "jangada-docs": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/nerigleston/jangada-docs-mcp", "jangada-docs-mcp"]
    }
  }
}
```

Ou pela CLI:

```bash
claude mcp add jangada-docs --scope project -- \
  uvx --from git+https://github.com/nerigleston/jangada-docs-mcp jangada-docs-mcp
```

### Globalmente (todos os seus projetos)

Disponível em **qualquer projeto seu** (escopo do usuário, fica no seu PC):

```bash
claude mcp add jangada-docs --scope user -- \
  uvx --from git+https://github.com/nerigleston/jangada-docs-mcp jangada-docs-mcp
```

> Escopos do Claude Code: `project` (no `.mcp.json` do projeto, compartilhável) ·
> `local` (só você, naquele projeto) · `user` (global, todos os seus projetos).

---

## Claude Desktop (global)

Settings → Developer → **Edit Config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "jangada-docs": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/nerigleston/jangada-docs-mcp", "jangada-docs-mcp"]
    }
  }
}
```

Reinicie o Claude Desktop.

## Cursor

- **Global:** `~/.cursor/mcp.json`  ·  **Projeto:** `.cursor/mcp.json`

Use o mesmo bloco `mcpServers` acima.

---

## Alternativa sem `uv` (clonar o repo)

```bash
git clone https://github.com/nerigleston/jangada-docs-mcp
cd jangada-docs-mcp
pip install -r requirements.txt        # = jangada-ai[mcp]
```

Aponte a config para o `python` do seu ambiente + o `server`:

```json
{
  "mcpServers": {
    "jangada-docs": {
      "command": "/caminho/para/python",
      "args": ["-m", "jangada_docs_mcp.server"]
    }
  }
}
```

---

## Ferramentas expostas

| Ferramenta | Para que serve |
|-----------|----------------|
| `jangada_indice()` | Índice/ordem das páginas. Comece aqui. |
| `jangada_listar_docs()` | Lista todas as páginas (nome — título). |
| `jangada_ler_doc(nome, lang)` | Conteúdo completo de uma página (`pt` padrão ou `en`). |
| `jangada_buscar(termo)` | Procura um termo em toda a doc (trechos + página). |

O assistente decide sozinho quando chamar — ex.: você pede "faça um RAG com
reranking" e ele consulta `jangada_ler_doc("rag")` antes de escrever.

## Como funciona

`jangada_docs_mcp/server.py` registra as funções acima como ferramentas MCP via
`jangada_ai.serve_mcp(...)` — sobre o `Server` **low-level** do protocolo MCP
(não FastMCP). Transporte **stdio**. A doc fica em `jangada_docs_mcp/docs/`
(snapshot do site da lib), empacotada no wheel.

## Licença

MIT — veja [LICENSE](LICENSE).
