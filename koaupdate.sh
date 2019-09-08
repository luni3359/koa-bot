#!/bin/bash
# This script automatically sends updates to the bot and restarts the current instance.

if [ -z ${KOAKUMA_HOME} ]; then
    echo "\$KOAKUMA_HOME is not defined. It needs to point to the bot's directory."
    exit 1
fi

if [ -z ${KOAKUMA_CONNSTR} ]; then
    echo "\$KOAKUMA_CONNSTR is not defined. It needs to point to the bot's hosting machine."
    exit 1
fi

if [ ! -d ${KOAKUMA_HOME} ]; then
    echo "Missing bot directory or env var set incorrectly, it points to ${KOAKUMA_HOME}"
    exit 1
fi

rsync -aXv --exclude=.* --exclude=__pycache__ --exclude=venv --progress ${KOAKUMA_HOME} ${KOAKUMA_CONNSTR}
