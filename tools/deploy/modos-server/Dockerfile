FROM ghcr.io/sdsc-ordes/modos-api:0.3.2

USER root

WORKDIR /app
COPY ./server.py /app

USER modos_user

RUN uv venv -p 3.12 --allow-existing
RUN uv pip install \
  "fastapi ~= 0.109.2" \
  "uvicorn ~= 0.27.0.post1"

ENTRYPOINT ["uv", "run", "--offline"]
CMD ["uvicorn", "--reload", "server:app"]
