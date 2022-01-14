FROM python:3.8.12 as base

# Get latest security updates for the image
RUN apt-get update && \ 
    apt-get upgrade -y && \
    apt-get clean

# Install music dependencies
RUN apt-get install -y ffmpeg --no-install-recommends

# Upgrade pip to the latest version
# RUN pip install -U pip

# Install the bot globally
RUN useradd --create-home little-devil
ENV PATH="/home/little-devil/.local/bin:${PATH}"
WORKDIR /usr/local/src/koa-bot
RUN chown -R little-devil:little-devil /usr/local/src/koa-bot
RUN chmod 755 /usr/local/src/koa-bot
# ###### Fix for poetry ######
# https://github.com/python-poetry/poetry/issues/2475#issuecomment-1005621857
# RUN chmod 755 /usr/local/src/
# #####T#E#M#P#O#R#A#R#Y######
USER little-devil

# Install the Poetry package manager
ENV POETRY_VERSION=1.1.12
RUN pip install --user --no-cache-dir poetry==$POETRY_VERSION

# Install only production dependencies
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install -E speed --no-ansi --no-root --no-dev

# Install bot
# RUN poetry config virtualenvs.create false && \
#     poetry install --no-ansi --no-dev

# Run bot
COPY ./ ./
RUN python -m koabot
