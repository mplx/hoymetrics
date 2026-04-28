#!/bin/sh
set -e

if [ "$FETCH_MODE" = "daemon" ]; then
    exec python3 /app/hoymetrics/daemon.py
elif [ -z "$FETCH_INTERVAL" ] || [ "$FETCH_INTERVAL" = "0" ]; then
    exec python3 /app/hoymetrics/hoymetrics.py
else
    exec supervisord -c /etc/supervisor/conf.d/hoymetrics.conf
fi
