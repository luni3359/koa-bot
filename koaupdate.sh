#!/bin/bash
# This script automatically sends updates to the bot. In the future it should also restart the running instance.

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

# Appending home of the remote koakuma
TARGET=${KOAKUMA_CONNSTR}:$(ssh ${KOAKUMA_CONNSTR} 'source ~/.profile; echo $KOAKUMA_HOME')
echo "Transferring from ${KOAKUMA_HOME} to ${TARGET}"

rsync -aXv --exclude=.* --exclude=__pycache__ --exclude=venv --include=.python-version --progress ${KOAKUMA_HOME}/ ${TARGET}
