FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release && \
    # Add Docker’s official GPG key
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    # Set up the Docker repository
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./poetry.lock ./

RUN pip install poetry --no-cache-dir && \
    poetry config virtualenvs.create false && \
    poetry install --without "dev,prod" --no-root

COPY ./app ./app
COPY ./blacklist.txt ./blacklist.txt
COPY ./Regression_Data.csv ./Regression_Data.csv

CMD ["celery", "-A", "app.celery.config", "worker", "--loglevel=info", "--concurrency=5"]
