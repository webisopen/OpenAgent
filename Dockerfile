FROM python:3.11-slim

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=.,target=/app pip install /app

RUN mkdir -p /etc/openagent
COPY examples/pendle.yaml /etc/openagent/config.yaml

ENTRYPOINT [ "openagent" ]
CMD [ "start", "--file", "/etc/openagent/config.yaml" ]