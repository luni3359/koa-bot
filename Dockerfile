FROM python:3.10.10-slim as base

# Get latest security updates for the image & install audio dependencies
RUN apt-get update && apt-get install -y \
    curl \
    # ffmpeg \
    # gcc \
    g++ \
    --no-install-recommends && \
    # apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create user account and install the bot system-wide
RUN useradd --create-home little-devil
USER little-devil

WORKDIR /app

# Install Poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/1.4/install-poetry.py | \
    # POETRY_HOME=/opt/poetry/ \
    python -
ENV PATH="/home/little-devil/.local/bin:${PATH}"

#RUN chown -R little-devil:little-devil /usr/local/src/koa-bot && \
#    chmod 755 /usr/local/src/koa-bot

# Install only production dependencies
COPY pyproject.toml ./
RUN poetry install -E speed --no-ansi --no-root --only main

# Copy code and run bot
COPY ./ ./
CMD [ "poetry", "run", "python", "-m", "koabot" ]
