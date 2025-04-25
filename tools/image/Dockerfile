ARG VERSION_BUILD



# include source files
WORKDIR /app
ADD CHANGELOG.md LICENSE README.md pyproject.toml uv.lock /app
ADD src ./src

# Set user
RUN useradd -ms /bin/bash modos_user
RUN chown -R modos_user:modos_user /app
RUN chmod -R 755 /app
USER modos_user

# modos setup
RUN uv venv -p 3.12
RUN uv sync --frozen

# Test run
RUN modos --help

ENTRYPOINT ["uv", "run"]
CMD ["modos"]
