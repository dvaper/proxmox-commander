# Offene Aufgaben - Proxmox Commander

## Setup-Wizard Verbesserungen

- [ ] **App-Admin Panel nicht sichtbar genug**: Der "App Administrator" Bereich im Setup-Wizard ist in einem zugeklappten Expansion Panel versteckt. Benutzer uebersehen ihn leicht und koennen den Wizard abschliessen ohne ein Admin-Passwort zu setzen. **Loesung**: Panel standardmaessig offen ODER als separater Pflicht-Schritt VOR dem Speichern.

- [ ] **Pflichtfeld deutlicher kennzeichnen**: App-Admin Passwort ist Pflichtfeld (min. 6 Zeichen), aber das ist nicht sofort ersichtlich. Bessere visuelle Kennzeichnung noetig (z.B. roter Stern, Warnhinweis).

- [ ] **NetBox Token Laenge pruefen**: Der Setup-Wizard generiert ein NetBox API-Token. Muss dieses Token (wie SECRET_KEY) auch eine Mindestlaenge haben? Aktuell 40 Zeichen hex - pruefen ob das ausreicht.

## Sicherheit

- [ ] **Bestehende admin/admin Credentials**: Wenn App vor v0.2.3 eingerichtet wurde, existiert bereits ein Admin-User mit Passwort "admin". Loesung: Passwort-Aenderung erzwingen beim ersten Login oder Hinweis im UI.

## UX Verbesserungen

- [x] **NetBox Status-Anzeige**: Status-Badge im UI zeigt NetBox-Zustand (Starting/Ready/Error) - implementiert in v0.2.4

- [ ] **Status-Badge Beschriftung**: Die Status-Badge in der Titel-Bar zeigt nur "Online/Starting/Error" ohne Kontext. Nicht klar erkennbar *was* den Status hat. **Loesung**: Label hinzufuegen, z.B. "NetBox: Online" oder Tooltip mit Details.

## Technische Schulden (aus Sicherheitsaudit)

- [ ] **Hardcoded IPs entfernen**: `cloud_init_service.py` enthaelt hardcoded Proxmox Node IPs und Phone-Home URL
- [ ] **SSH Public Keys konfigurierbar machen**: Aktuell hardcoded in `cloud_init_service.py`
- [ ] **JWT Secret Validierung**: Warnung/Fehler wenn Default "change-me-in-production" verwendet wird
