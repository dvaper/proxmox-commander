#!/bin/bash
# Entrypoint Script fuer Proxmox Commander API

# Default-Playbooks kopieren falls Verzeichnis leer ist
if [ -d "/app/default-data/playbooks" ] && [ -d "/data/playbooks" ]; then
    if [ -z "$(ls -A /data/playbooks 2>/dev/null)" ]; then
        echo "Kopiere Default-Playbooks nach /data/playbooks..."
        cp -r /app/default-data/playbooks/* /data/playbooks/
        echo "Default-Playbooks installiert."
    fi
fi

# Starte die Anwendung
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
