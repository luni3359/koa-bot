FROM python:3.8.12 as base

# Get latest security updates for the image
RUN apt-get update && \ 
    apt-get upgrade -y && \
    apt-get clean

# Install music dependencies
RUN apt-get install -y ffmpeg --no-install-recommends

# Install the Poetry package manager
RUN pip install --no-cache-dir \
                --disable-pip-version-check \
                poetry==1.1.12

# Create user account and install the bot system-wide
RUN useradd --create-home little-devil
ENV PATH="/home/little-devil/.local/bin:${PATH}"
WORKDIR /usr/local/src/koa-bot
RUN chown -R little-devil:little-devil /usr/local/src/koa-bot
RUN chmod 755 /usr/local/src/koa-bot

# Install only production dependencies
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install -E speed --no-ansi --no-root --no-dev

# Run bot
USER little-devil
COPY ./ ./
RUN python -m koabot
