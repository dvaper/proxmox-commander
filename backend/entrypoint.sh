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

# Terraform-Module kopieren falls nicht vorhanden
if [ -d "/app/default-data/terraform" ] && [ -d "/data/terraform" ]; then
    # Immer sicherstellen dass modules/ existiert
    if [ ! -d "/data/terraform/modules" ]; then
        echo "Kopiere Terraform-Module nach /data/terraform..."
        cp -r /app/default-data/terraform/modules /data/terraform/
        echo "Terraform-Module installiert."
    fi
    # Provider und Variables kopieren falls nicht vorhanden
    if [ ! -f "/data/terraform/provider.tf" ]; then
        cp /app/default-data/terraform/provider.tf /data/terraform/
        echo "Terraform provider.tf installiert."
    fi
    if [ ! -f "/data/terraform/variables.tf" ]; then
        cp /app/default-data/terraform/variables.tf /data/terraform/
        echo "Terraform variables.tf installiert."
    fi
fi

# Starte die Anwendung
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
