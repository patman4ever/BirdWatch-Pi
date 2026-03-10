# 🐦 BirdWatch-Pi

> Uitgeklede vogelherkenning op batterij voor in het veld.  
> Audio-analyse via BirdNET · Tekst-only UI · CSV export

---

## Vereisten

| Hardware | Minimum |
|----------|---------|
| Raspberry Pi | 3B+ / 4B / 5 |
| Opslag | 16 GB SD-kaart |
| Microfoon | USB-microfoon of USB-soundcard + lavalier |
| Voeding | Powerbank (5V/3A, USB-C voor Pi 4/5) |

**Software:** Raspberry Pi OS Lite (64-bit) · Docker

---

## Installatie (één commando)

```bash
curl -fsSL https://raw.githubusercontent.com/patman4ever/BirdWatch-Pi/main/install.sh | bash
```

Of handmatig:
```bash
git clone https://github.com/patman4ever/BirdWatch-Pi
cd BirdWatch-Pi
nano config.env          # stel microfoon in
docker compose up -d
```

---

## Configuratie

Bewerk `config.env` (geen herinstallatie nodig):

```env
# Microfoon: indexnummer van 'arecord -l', bijv. 1
AUDIO_DEVICE=1

# Sample rate (48000 aanbevolen)
SAMPLE_RATE=48000

# Minimale betrouwbaarheid waarneming (0.0–1.0)
MIN_CONFIDENCE=0.70

# GPS locatie (voor seizoensfilter BirdNET)
LOCATION_LAT=52.30
LOCATION_LON=5.00

# Taal soortnamen
LANGUAGE=nl
```

Na aanpassing:
```bash
docker compose restart
```

---

## Web Interface

Open een browser op hetzelfde netwerk:

```
http://<ip-van-pi>:7766
```

| Pagina | Beschrijving |
|--------|-------------|
| **LIVE** | Real-time tekst-feed van detecties |
| **HISTORY** | Overzicht + statistieken per soort |
| **CONFIG** | Audio & locatie instellen |
| **EXPORT** | Download CSV voor Excel/LibreOffice |

### Microfoon kiezen via web UI
Ga naar **CONFIG** → kies het gewenste apparaat uit de dropdown → **OPSLAAN** → herstart container.

---

## CSV Export

Via de web interface (**EXPORT** tab) of direct:

```bash
# Interactief
curl -X POST http://localhost:7766/export/create

# Bestand terughalen
scp pi@<ip>:~/BirdWatch-Pi/data/exports/*.csv ./
```

CSV-kolommen: `timestamp`, `species_nl`, `species_sci`, `confidence`, `start_time`, `end_time`

---

## Veldinzet op batterij

### Tips voor langere batterijduur

```bash
# Schakel Wi-Fi uit als niet nodig (bespaart ~150mA)
sudo rfkill block wifi

# Zet GPU-geheugen laag (geen scherm nodig)
echo "gpu_mem=16" | sudo tee -a /boot/config.txt

# Schakel HDMI uit
tvservice -o
```

### Lokale toegang zonder netwerk
De Pi maakt een eigen Wi-Fi hotspot aan met dit script:
```bash
bash scripts/hotspot.sh start   # SSID: BirdWatch-Pi, WW: birdwatch
bash scripts/hotspot.sh stop
```
Verbind dan met het netwerk **BirdWatch-Pi** en open `http://10.42.0.1:7766`.

---

## Nuttige commando's

```bash
# Status
docker compose ps

# Live logs
docker compose logs -f

# Stoppen
docker compose down

# Data backup (kopieer van Pi naar laptop)
rsync -av pi@<ip>:~/BirdWatch-Pi/data/ ./birdwatch-backup/
```

---

## Data opslag

```
data/
├── detections/
│   └── detections.jsonl    ← alle waarnemingen (1 per regel)
├── exports/
│   └── birdwatch_export_*.csv
└── recordings/             ← tijdelijk (automatisch opgeruimd)
```

---

## Licentie
MIT – gebaseerd op [BirdWatch](https://github.com/patman4ever/BirdWatch) door patman4ever.  
BirdNET-Analyzer © Cornell Lab of Ornithology.
