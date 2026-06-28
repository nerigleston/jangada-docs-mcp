# Deploy do jangada-mcp na AWS (Lambda + API Gateway)

Como o servidor MCP (o próprio **jangada** sendo servidor, via `build_mcp_app`)
foi para produção em **`https://mcp.jangada.dev.br/mcp/`** — passo a passo,
arquivos que importam e as armadilhas que custaram tempo.

> ⚠️ **O endpoint tem barra final**: `/mcp/`. `/mcp` responde **307** (redirect do
> Mount do Starlette) — use sempre `/mcp/`.

## Arquitetura final

```
cliente MCP (Claude Code / Cursor)
   │ HTTPS POST  https://mcp.jangada.dev.br/mcp/
   ▼
Route 53 (A alias) → API Gateway HTTP API (domínio custom + cert ACM curinga)
   │ integração AWS_PROXY (payload v2.0)
   ▼
Lambda (imagem container, arm64) + Lambda Web Adapter
   │ traduz o evento → HTTP em :8080
   ▼
uvicorn → build_mcp_app (jangada) → lê os .mdx da imagem → JSON
```

- **Lambda container arm64**, 1024 MB, timeout 30s.
- **Lambda Web Adapter (LWA)**: extensão que faz a ponte evento↔HTTP — o app é um
  uvicorn comum.
- **API Gateway HTTP API**: invoca a Lambda direto (não assina o corpo). Público,
  sem auth na rota.
- **Domínio**: API Gateway custom domain (regional) + cert ACM `*.jangada.dev.br`
  + alias no Route 53.

## Por que NÃO Function URL (a parte que custou tempo)

Tentei dois caminhos com **Lambda Function URL** e os dois morreram para MCP:

1. **Function URL `AuthType: NONE` (público)** → **403 Forbidden** mesmo com a
   resource policy pública correta. Essa conta **bloqueia** Function URL pública
   (não é org/SCP; é comportamento da conta).
2. **Function URL `AWS_IAM` + CloudFront com OAC** → **`signature does not
   match`**. O **OAC não assina o corpo do POST** ao falar com a Lambda; como MCP
   é todo POST com body, a validação SigV4 sempre falha.

➡️ Solução: **API Gateway HTTP API**, que invoca a Lambda por integração direta
(sem SigV4 sobre o corpo). Funciona com qualquer cliente MCP.

## Arquivos que fazem diferença

### `jangada_docs_mcp/asgi.py` — o app ASGI (stateless é obrigatório)
```python
from jangada_ai import build_mcp_app
from .server import (jangada_indice, jangada_listar_docs,
                     jangada_ler_doc, jangada_buscar)

app = build_mcp_app(
    "jangada-mcp",
    tools=[jangada_indice, jangada_listar_docs, jangada_ler_doc, jangada_buscar],
    path="/mcp",
    json_response=True,   # resposta JSON única (sem stream SSE longo)
    stateless=True,       # sem sessão Mcp-Session-Id — Lambda é por-invocação
)
```
`stateless=True` + `json_response=True` são o pulo do gato: a Lambda não mantém
estado/conexão entre chamadas, então cada request MCP precisa se bastar sozinho.

### `Dockerfile` — LWA + as 3 linhas críticas
```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim
# (1) o Lambda Web Adapter como extensão
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV PORT=8080 PYTHONUNBUFFERED=1
WORKDIR /var/task
COPY requirements-lambda.txt ./
RUN python -m pip install --no-cache-dir -r requirements-lambda.txt
COPY jangada_docs_mcp ./jangada_docs_mcp
# (2) sem isto -> PermissionError no /var/task: o COPY herda permissões
#     restritivas do host; o usuário não-root da Lambda não consegue ler.
RUN chmod -R a+rX ./jangada_docs_mcp
# (3) shell-form p/ expandir $PORT
CMD exec uvicorn jangada_docs_mcp.asgi:app --host 0.0.0.0 --port ${PORT}
```

### `requirements-lambda.txt`
```
jangada-ai[mcp]>=0.36.0
starlette>=0.37
uvicorn[standard]>=0.30
```

### Build da imagem — `--provenance=false` é obrigatório
```bash
docker build --platform linux/arm64 --provenance=false --sbom=false -t <ecr>:latest .
```
Sem `--provenance=false`, o BuildKit gera um **manifest list com attestation** que
a **Lambda rejeita** (precisa de imagem single-arch `manifest.v2`). Em runner CI,
o `docker/build-push-action` recebe `provenance: false`.

> macOS no volume exFAT cria arquivos `._*` (AppleDouble) que quebram o build
> (`failed to xattr ._Dockerfile`). Tenha um `.dockerignore` com `._*` e rode
> `find . -name '._*' -delete` antes do build.

## Passo a passo (CLI, profile `exiby`, us-east-1)

```bash
export AWS_PROFILE=exiby AWS_DEFAULT_REGION=us-east-1
ACC=917727438331
ECR=$ACC.dkr.ecr.us-east-1.amazonaws.com

# 1) ECR
aws ecr create-repository --repository-name jangada-docs-mcp
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR

# 2) imagem arm64 (single-arch) + push
docker build --platform linux/arm64 --provenance=false --sbom=false -t $ECR/jangada-docs-mcp:latest .
docker push $ECR/jangada-docs-mcp:latest

# 3) role de execução da Lambda
aws iam create-role --role-name jangada-docs-mcp-lambda-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name jangada-docs-mcp-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 4) função (container arm64)
aws lambda create-function --function-name jangada-docs-mcp \
  --package-type Image --code ImageUri=$ECR/jangada-docs-mcp:latest \
  --role arn:aws:iam::$ACC:role/jangada-docs-mcp-lambda-role \
  --architectures arm64 --timeout 30 --memory-size 1024

# 5) API Gateway HTTP API (quick-create: integração AWS_PROXY + rota $default)
API=$(aws apigatewayv2 create-api --name jangada-mcp --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:$ACC:function:jangada-docs-mcp \
  --query ApiId --output text)

# 6) PERMISSÃO p/ a API invocar a Lambda (o quick-create NÃO adiciona!)
aws lambda add-permission --function-name jangada-docs-mcp --statement-id ApiGatewayInvoke \
  --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:$ACC:$API/*/*"

# 7) domínio custom (regional, cert na MESMA região) + mapping
CERT=arn:aws:acm:us-east-1:$ACC:certificate/abc158c5-b759-41b8-b6d7-28a835cc679f
aws apigatewayv2 create-domain-name --domain-name mcp.jangada.dev.br \
  --domain-name-configurations CertificateArn=$CERT,EndpointType=REGIONAL,SecurityPolicy=TLS_1_2
aws apigatewayv2 create-api-mapping --domain-name mcp.jangada.dev.br --api-id $API --stage '$default'

# 8) Route 53: A alias mcp.jangada.dev.br -> alvo regional do domínio
#    (target = DomainNameConfigurations[0].ApiGatewayDomainName, HostedZoneId Z1UJRXOUMOOFQ8)
aws route53 change-resource-record-sets --hosted-zone-id Z08720531K910N9F668BG --change-batch '{...A alias...}'

# 9) testar (barra final!)
curl -s -X POST https://mcp.jangada.dev.br/mcp/ \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"c","version":"1"}}}'
# -> {"result":{...,"serverInfo":{"name":"jangada-mcp",...}}}
```

## Atualizar a imagem (deploy de nova versão)
```bash
docker build --platform linux/arm64 --provenance=false --sbom=false -t $ECR/jangada-docs-mcp:latest .
docker push $ECR/jangada-docs-mcp:latest
aws lambda update-function-code --function-name jangada-docs-mcp --image-uri $ECR/jangada-docs-mcp:latest
```

## CI/CD (GitHub Actions, OIDC — sem chaves longas)

`.github/workflows/deploy.yml` builda arm64, manda pro ECR e dá
`update-function-code` a cada push na `master`. Autentica via **OIDC** assumindo
o role `jangada-docs-mcp-ci`.

Setup do role (uma vez):
```bash
# provider OIDC do GitHub (se ainda não existir na conta)
aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# role confiando no repo + policy (ECR push + lambda:UpdateFunctionCode) — ver
# os JSONs de trust/policy abaixo.
aws iam create-role --role-name jangada-docs-mcp-ci --assume-role-policy-document file://trust.json
aws iam put-role-policy --role-name jangada-docs-mcp-ci --policy-name deploy --policy-document file://policy.json
```
Trust (condiciona ao repo):
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
 "Principal":{"Federated":"arn:aws:iam::917727438331:oidc-provider/token.actions.githubusercontent.com"},
 "Action":"sts:AssumeRoleWithWebIdentity",
 "Condition":{"StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},
              "StringLike":{"token.actions.githubusercontent.com:sub":"repo:nerigleston/jangada-docs-mcp:*"}}}]}
```
Policy (mínima): `ecr:GetAuthorizationToken` (Resource `*`), as ações de push no
repo `jangada-docs-mcp` e `lambda:UpdateFunctionCode` na função.

## Infrastructure as Code

`template.yaml` (AWS SAM) reproduz **toda** a arquitetura do zero — Lambda
container arm64 + API Gateway HTTP API + domínio custom + registro Route 53:
```bash
sam build
sam deploy --guided
```
> A infra atual foi criada **na mão** (passos acima). O `template.yaml` serve para
> recriar em outra conta/ambiente — ou para migrar o que existe para um stack
> CloudFormation. O CI/CD do dia a dia **não** roda `sam deploy`; só atualiza a
> imagem da função (mais rápido e com permissão mínima).

## Armadilhas (resumo)
| Sintoma | Causa | Correção |
|---|---|---|
| `403 Forbidden` na Function URL NONE | conta bloqueia URL pública | usar API Gateway |
| `signature does not match` (CloudFront+OAC) | OAC não assina corpo POST | usar API Gateway |
| Lambda rejeita a imagem | manifest list/attestation | `docker build --provenance=false` |
| `PermissionError /var/task/...` | COPY herdou perms restritivas | `RUN chmod -R a+rX` no Dockerfile |
| `failed to xattr ._Dockerfile` | AppleDouble do macOS/exFAT | `.dockerignore` com `._*` + limpar |
| `500` sem logs na 1ª chamada | API Gateway sem permissão de invoke | `add-permission` p/ `apigateway.amazonaws.com` |
| `307` no endpoint | faltou barra final | usar `/mcp/` |
