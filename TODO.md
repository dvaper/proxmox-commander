# Offene Aufgaben - Proxmox Commander

## Setup-Wizard Verbesserungen

- [ ] **App-Admin Panel standardmaessig offen**: Der "App Administrator" Bereich im Setup-Wizard ist in einem zugeklappten Expansion Panel. Benutzer uebersehen ihn leicht. Panel sollte standardmaessig geoeffnet sein oder als separater Schritt.

- [ ] **Pflichtfeld deutlicher kennzeichnen**: App-Admin Passwort ist Pflichtfeld (min. 6 Zeichen), aber das ist nicht sofort ersichtlich. Bessere visuelle Kennzeichnung noetig.

## Sicherheit

- [ ] **Bestehende admin/admin Credentials**: Wenn App vor v0.2.3 eingerichtet wurde, existiert bereits ein Admin-User mit Passwort "admin". Loesung: Passwort-Aenderung erzwingen beim ersten Login oder Hinweis im UI.

## UX Verbesserungen

- [x] **NetBox Status-Anzeige**: Status-Badge im UI zeigt NetBox-Zustand (Starting/Ready/Error) - implementiert in v0.2.4

## Technische Schulden (aus Sicherheitsaudit)

- [ ] **Hardcoded IPs entfernen**: `cloud_init_service.py` enthaelt hardcoded Proxmox Node IPs und Phone-Home URL
- [ ] **SSH Public Keys konfigurierbar machen**: Aktuell hardcoded in `cloud_init_service.py`
- [ ] **JWT Secret Validierung**: Warnung/Fehler wenn Default "change-me-in-production" verwendet wird
