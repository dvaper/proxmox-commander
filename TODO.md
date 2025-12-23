# Offene Aufgaben - Proxmox Commander

## Setup-Wizard Verbesserungen

- [x] **App-Admin Panel nicht sichtbar genug**: Der "App Administrator" Bereich im Setup-Wizard ist in einem zugeklappten Expansion Panel versteckt. **Geloest**: Panel ist jetzt standardmaessig offen + Warnhinweis wenn Passwort fehlt.

- [x] **Pflichtfeld deutlicher kennzeichnen**: App-Admin Passwort ist Pflichtfeld (min. 6 Zeichen). **Geloest**: Warnung oben im Step + "Pflicht"/"OK" Chip am Panel + Error-Farbe.

- [x] **NetBox Token Laenge pruefen**: Der Setup-Wizard generiert ein NetBox API-Token mit 40 Zeichen hex. **Geprueft**: 40 hex chars ist NetBox Standard-Format (20 Bytes). SECRET_KEY braucht 50+, aber API-Token ist korrekt.

## Sicherheit

- [x] **Bestehende admin/admin Credentials**: Wenn App vor v0.2.3 eingerichtet wurde, existiert bereits ein Admin-User mit Passwort "admin". **Geloest**: `create_default_admin()` aktualisiert jetzt bestehende Super-Admins wenn Credentials in .env geaendert wurden.

## UX Verbesserungen

- [x] **NetBox Status-Anzeige**: Status-Badge im UI zeigt NetBox-Zustand (Starting/Ready/Error) - implementiert in v0.2.4

- [x] **Status-Badge Beschriftung**: Die Status-Badge in der Titel-Bar zeigt nur "Online/Starting/Error" ohne Kontext. **Geloest**: Label geaendert zu "Services: Online/Starting/Error".

## Technische Schulden (aus Sicherheitsaudit)

- [ ] **Hardcoded IPs entfernen**: `cloud_init_service.py` enthaelt hardcoded Proxmox Node IPs und Phone-Home URL
- [ ] **SSH Public Keys konfigurierbar machen**: Aktuell hardcoded in `cloud_init_service.py`
- [ ] **JWT Secret Validierung**: Warnung/Fehler wenn Default "change-me-in-production" verwendet wird
