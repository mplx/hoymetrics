FROM python:3.12-slim

RUN pip install --no-cache-dir hoymiles-wifi supervisor

WORKDIR /app
COPY hoymetrics/ hoymetrics/
COPY supervisord.conf /etc/supervisor/conf.d/hoymetrics.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

VOLUME ["/data"]

# FETCH_MODE: unset = single fetch | "periodic" via FETCH_INTERVAL | "daemon" = Prometheus exporter
ENV FETCH_MODE=""
ENV DTU_IP=""
ENV LOG_FILE=""
# FETCH_INTERVAL: seconds between runs (periodic and daemon modes)
ENV FETCH_INTERVAL="60"
# PROMETHEUS_PORT: HTTP port for /metrics endpoint (daemon mode only)
ENV PROMETHEUS_PORT="9100"

EXPOSE 9100

ENTRYPOINT ["/docker-entrypoint.sh"]
