ARG MODOS_API_IMAGE=ghcr.io/sdsc-ordes/modos-api:0.3.5
FROM ${MODOS_API_IMAGE}

USER modos_user
WORKDIR /app
COPY ./src /app/kms

RUN uv venv -p 3.12 --allow-existing
RUN uv pip install \
    "fastapi ~= 0.109.2" \
    "uvicorn ~= 0.27.0.post1" \
    "pyjwt ~= 2.10.1"

ENTRYPOINT ["uv", "run", "--offline"]
CMD ["uvicorn", "--reload", "kms.kms:app"]
