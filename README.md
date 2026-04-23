# Dendermonde Nieuws

Lokaal nieuwsdashboard voor de regio Dendermonde. Scrapt dagelijks 4 bronnen, toont een live dashboard via GitHub Pages, en stuurt elke zondag een AI-gegenereerde samenvatting per mail.

## Bronnen
- **VRT NWS** - regionaal nieuws Dendermonde
- **Dender Journaal** - hyperlocaal via RSS
- **Stad Dendermonde** - officiele persberichten
- **HLN Dendermonde** - krantenkoppen regio

## Setup

### 1. GitHub Pages activeren
Ga naar Settings -> Pages -> Branch: main, Folder: /docs -> Save

### 2. Secrets instellen
Ga naar Settings -> Secrets and variables -> Actions

| Naam | Waarde |
|------|--------|
| ANTHROPIC_API_KEY | Je Anthropic API key |
| SENDGRID_API_KEY | Je SendGrid API key |
| SENDGRID_FROM_EMAIL | Verzendadres (geverifieerd in SendGrid) |
| SENDGRID_TO_EMAIL | Ontvangstadres |

### 3. Eerste scrape starten
Actions -> Dagelijkse Scrape -> Run workflow

### 4. Mail testen
Actions -> Wekelijkse Mail -> Run workflow

## Schema
| Actie | Wanneer |
|-------|---------|
| Scrape + dashboard | Elke dag om 7u |
| Wekelijkse mail | Elke zondag om 17u |
