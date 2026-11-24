FROM python:3.14-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    COLEG_HOME=/var/lib/coleg \
    HOME=/var/lib/coleg

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o 10001 -g 10001 /var/lib/coleg

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir . gunicorn==27.0.1

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/web.css', timeout=3).close()"

CMD ["sh", "-ec", "if [ ! -s \"$COLEG_HOME/indice.sqlite\" ]; then coleg atualizar; fi; exec gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 60 --no-control-socket coleg.web:application"]
