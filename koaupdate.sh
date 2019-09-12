#!/bin/bash
# This script automatically sends updates to the bot. In the future it should also restart the running instance.

echo "Updating bot..."

if [ -z ${KOAKUMA_HOME} ]; then
    echo "\$KOAKUMA_HOME is not defined. It needs to point to the bot's directory."
    exit 1
fi

if [ ! -d ${KOAKUMA_HOME} ]; then
    echo "Missing bot directory or env var set incorrectly, it points to ${KOAKUMA_HOME}"
    exit 1
fi

if [ -z ${KOAKUMA_CONNSTR} ]; then
    echo "\$KOAKUMA_CONNSTR is not defined. It needs to point to the bot's hosting machine."
    exit 1
fi

# redirects STDERR to /dev/null to hide ssh error messages
REMOTE_HOME=$(ssh ${KOAKUMA_CONNSTR} 'source ~/.profile; echo $KOAKUMA_HOME' 2> /dev/null)
ssh_return_value=$?

# Test if host is up
if [ $ssh_return_value -ne 0 ]; then
    echo "Unable to connect to host (${KOAKUMA_CONNSTR}) [Return value: $ssh_return_value]"
    exit 1
fi

if [ -z ${REMOTE_HOME} ]; then
    echo "The remote \$KOAKUMA_HOME env var is empty or set incorrectly."
    exit 1
fi

# Appending home of the remote koakuma
TARGET=${KOAKUMA_CONNSTR}:${REMOTE_HOME}
echo "Transferring from ${KOAKUMA_HOME} to ${TARGET}"

rsync -aXv --include=.python-version --exclude=.* --exclude=__pycache__ --exclude=venv --progress ${KOAKUMA_HOME}/ ${TARGET}
