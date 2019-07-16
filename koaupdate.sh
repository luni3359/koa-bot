#!/bin/bash
# This script automatically sends updates to the bot and restarts the current
# instance. In the future I should change this so that it uses rsync instead
cd ${KOAKUMA_HOME}

sftp -b sftp_commands.txt ${KOAKUMA_CONNSTR}
