ARG MODOS_API_IMAGE=ghcr.io/sdsc-ordes/modos-api:0.3.5
FROM ${MODOS_API_IMAGE}

USER modos_user
WORKDIR /app
COPY ./server.py /app

RUN uv venv -p 3.14 --allow-existing
RUN uv pip install \
    "fastapi ~= 0.162.0" \
    "uvicorn ~= 0.54.0"

ENTRYPOINT ["uv", "run", "--offline"]
CMD ["uvicorn", "--reload", "server:app"]
