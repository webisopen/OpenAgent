FROM python:3.11-slim

RUN --mount=type=bind,source=.,target=/app pip install /app
COPY examples/pendle.yaml /etc/openagent/config.yaml

ENTRYPOINT [ "openagent" ]
CMD [ "start", "--file", "/etc/openagent/config.yaml" ]