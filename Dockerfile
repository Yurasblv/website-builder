FROM python:3.11-buster as builder

RUN pip install poetry==2.0.0

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /core

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM python:3.11-slim-buster as runtime

# Install curl and other dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    cron \
    logrotate \
    nano \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

ENV VIRTUAL_ENV=/core/.venv \
    PATH="/core/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app

COPY . .

RUN echo "0 0,12 * * * /usr/sbin/logrotate /app/log-rotate.conf --state /app/log-rotate-state" > /etc/cron.d/logrotate-cron \
    && chmod 0644 /etc/cron.d/logrotate-cron \
    && crontab /etc/cron.d/logrotate-cron

RUN chmod +x ./app-start.sh

CMD ["sh", "-c", "cron && ./app-start.sh"]
