FROM python:3.12-slim-bullseye

WORKDIR /app

COPY . .
ENV PYTHONPATH=${PYTHONPATH}:${PWD}
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

EXPOSE 8000

CMD ["poetry", "run", "python", "main.py"]