FROM python:3.10.10-slim as base

# Get latest security updates for the image & install audio dependencies
RUN apt-get update && apt-get install -y \
    curl \
    # ffmpeg \
    # gcc \
    g++ \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create user account and install the bot system-wide
RUN useradd -u 1500  --create-home little-devil
USER little-devil

WORKDIR /app

# Install Poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/1.4/install-poetry.py | \
    python -
ENV PATH="/home/little-devil/.local/bin:${PATH}"

# Install only production dependencies
COPY pyproject.toml ./
RUN poetry install -E speed --no-ansi --no-root --only main

# Copy code and run bot
COPY ./ ./

# FROM --platform=$BUILDPLATFORM base AS builder
# ARG TARGETARCH
# RUN --mount=type=cache,target=/root/.cache/pip \
#     --mount=type=cache,target=/root/.cache/pypoetry \
#     pip wheel --no-deps --wheel-dir=/wheels .

# USER 1

# FROM base AS final
# ARG TARGETARCH
# COPY --from=builder /wheels /wheels
# RUN --mount=type=cache,target=/root/.cache/pip \
#     --mount=type=cache,target=/root/.cache/pypoetry \
#     pip install --no-deps /wheels/*.whl && \
#     rm -rf /wheels

CMD [ "poetry", "run", "python", "-m", "koabot" ]
