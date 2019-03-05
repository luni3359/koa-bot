#!/bin/bash
# This script is run automatically when the pi runs, directly from /etc/xdg/autostart/koa-bot.desktop
# env var is set at ~/.profile
python3 ${KOAKUMA_HOME}/koakuma.py
