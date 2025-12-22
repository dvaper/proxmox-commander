FROM python:3.11-slim

WORKDIR /app

# Timezone setzen
ENV TZ=Europe/Berlin

# System-Abhängigkeiten inkl. tzdata für Timezone-Support
RUN apt-get update && apt-get install -y --no-install-recommends \
    ansible \
    openssh-client \
    git \
    curl \
    unzip \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Terraform installieren
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin/ \
    && rm /tmp/terraform.zip \
    && terraform version

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App kopieren
COPY app/ ./app/

# Default-Daten (Playbooks, etc.)
COPY default-data/ ./default-data/

# Entrypoint Script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Datenverzeichnisse (werden zur Laufzeit gemountet)
RUN mkdir -p /data/db /data/inventory /data/playbooks /data/roles /data/terraform /data/ssh

# SSH-Verzeichnis mit korrekten Berechtigungen
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Git safe.directory für gemountete Repositories
RUN git config --global --add safe.directory /repo \
    && git config --global credential.helper store

# Port
EXPOSE 8000

# Start via Entrypoint (kopiert Default-Playbooks falls noetig)
ENTRYPOINT ["/entrypoint.sh"]
