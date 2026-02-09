FROM python:3.14-slim-trixie AS base
WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc

RUN useradd -ms /bin/bash app
COPY --chown=app:app pyproject.toml uv.lock /app/
RUN pip install --upgrade pip uv
ENV UV_PROJECT_ENVIRONMENT "/app/.venv"
ENV PYTHONPATH "/app"
ENTRYPOINT ["/bin/bash", "/app/docker/entrypoint.sh"]

# DEV
FROM base AS dev
RUN apt-get update && apt-get install -y \
    bash git curl neovim
RUN uv sync --all-extras
COPY --chown=app:app . /app/
CMD ["dev_server"]

# PRD
FROM base AS prd
RUN uv sync
COPY --chown=app:app . /app/
USER app
CMD ["prd_server"]
