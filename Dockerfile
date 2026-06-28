# Imagem de container para AWS Lambda via Lambda Web Adapter (LWA).
# Serve o MCP do jangada (build_mcp_app) por Streamable HTTP, stateless.
# O LWA traduz o evento da Lambda para uma requisição HTTP ao uvicorn na $PORT.
FROM public.ecr.aws/docker/library/python:3.12-slim

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

ENV PORT=8080 \
    PYTHONUNBUFFERED=1

WORKDIR /var/task

COPY requirements-lambda.txt ./
RUN python -m pip install --no-cache-dir -r requirements-lambda.txt

# o pacote (server + asgi + docs embutidas). chmod garante leitura pelo
# usuário não-root da Lambda (o COPY pode herdar permissões restritivas do host).
COPY jangada_docs_mcp ./jangada_docs_mcp
RUN chmod -R a+rX ./jangada_docs_mcp

# sobe o app ASGI do jangada (build_mcp_app, rota /mcp, stateless)
CMD exec uvicorn jangada_docs_mcp.asgi:app --host 0.0.0.0 --port ${PORT}
