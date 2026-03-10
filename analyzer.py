"""
analyzer.py – Analyseert audiobestanden met BirdNET via birdnetlib.
Slaat detecties op in /data/detections als JSON-regels (JSONL).
"""
import os
import json
from datetime import datetime
from pathlib import Path

DETECTIONS_FILE = Path("/data/detections/detections.jsonl")
DETECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", 0.7))
LAT = float(os.getenv("LOCATION_LAT", 52.3))
LON = float(os.getenv("LOCATION_LON", 5.0))

# In-memory cache van laatste detecties voor live feed
_recent_detections = []
MAX_RECENT = 100

_listeners = []  # callbacks voor nieuwe detecties


def subscribe(callback):
    """Registreer een callback die aangeroepen wordt bij elke nieuwe detectie."""
    _listeners.append(callback)


def analyze(filepath: str):
    """
    Analyseer een WAV-bestand en sla detecties op.
    Geeft lijst van detectie-dicts terug.
    """
    try:
        from birdnetlib import Recording
        from birdnetlib.analyzer import Analyzer
    except ImportError:
        print("[Analyzer] birdnetlib niet beschikbaar, gebruik demo-modus.")
        return _demo_detections(filepath)

    try:
        analyzer = Analyzer()
        recording = Recording(
            analyzer,
            filepath,
            lat=LAT,
            lon=LON,
            date=datetime.now(),
            min_conf=MIN_CONFIDENCE,
        )
        recording.analyze()

        results = []
        for d in recording.detections:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "species_nl": d.get("common_name", d.get("scientific_name", "onbekend")),
                "species_sci": d.get("scientific_name", ""),
                "confidence": round(d.get("confidence", 0), 3),
                "start_time": d.get("start_time", 0),
                "end_time": d.get("end_time", 0),
                "file": filepath,
            }
            results.append(entry)
            _save(entry)
            _notify(entry)

        # Verwijder verwerkt audiobestand om schijfruimte te sparen
        try:
            Path(filepath).unlink()
        except Exception:
            pass

        return results

    except Exception as e:
        print(f"[Analyzer] Fout bij analyse: {e}")
        return []


def _demo_detections(filepath):
    """Simuleer detecties als birdnetlib niet beschikbaar is."""
    import random
    demo_birds = [
        ("Koolmees", "Parus major"),
        ("Merel", "Turdus merula"),
        ("Vink", "Fringilla coelebs"),
        ("Roodborst", "Erithacus rubecula"),
    ]
    if random.random() > 0.4:
        name, sci = random.choice(demo_birds)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "species_nl": name,
            "species_sci": sci,
            "confidence": round(random.uniform(0.70, 0.99), 3),
            "start_time": 0,
            "end_time": 15,
            "file": filepath,
        }
        _save(entry)
        _notify(entry)
        return [entry]
    return []


def _save(entry: dict):
    global _recent_detections
    with open(DETECTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _recent_detections.append(entry)
    if len(_recent_detections) > MAX_RECENT:
        _recent_detections = _recent_detections[-MAX_RECENT:]


def _notify(entry: dict):
    for cb in _listeners:
        try:
            cb(entry)
        except Exception:
            pass


def get_recent(limit=50):
    return list(reversed(_recent_detections[-limit:]))


def load_history(limit=500):
    """Laad waarnemingen uit JSONL bestand."""
    results = []
    if not DETECTIONS_FILE.exists():
        return results
    try:
        with open(DETECTIONS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines[-limit:]):
            line = line.strip()
            if line:
                results.append(json.loads(line))
    except Exception as e:
        print(f"[Analyzer] Fout bij laden geschiedenis: {e}")
    return results
