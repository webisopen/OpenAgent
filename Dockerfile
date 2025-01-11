# Node stage
FROM node:20.10.0 as builder
WORKDIR /app/widget
COPY widget/package.json widget/yarn.lock ./
RUN yarn install
COPY widget ./
RUN yarn run build

# Python stage
FROM python:3.11.5-slim-bullseye

WORKDIR /app

COPY . .
ENV PYTHONPATH=${PYTHONPATH}:${PWD}
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

COPY --from=builder /app/dist /app/dist

CMD ["python", "main.py"]
