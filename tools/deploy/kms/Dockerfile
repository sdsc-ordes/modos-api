ARG MODOS_API_IMAGE=ghcr.io/sdsc-ordes/modos-api:0.3.5
FROM ${MODOS_API_IMAGE}

USER modos_user
WORKDIR /app
COPY ./src /app/kms

RUN uv venv -p 3.14 --allow-existing
RUN uv pip install \
    "fastapi ~= 0.162.0" \
    "uvicorn ~= 0.54.0" \
    "pyjwt ~= 2.15.0"

ENTRYPOINT ["uv", "run", "--offline"]
CMD ["uvicorn", "--reload", "kms.kms:app"]
