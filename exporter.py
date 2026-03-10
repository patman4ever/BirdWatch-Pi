"""
exporter.py – Exporteert waarnemingen naar CSV voor offline analyse.
"""
import csv
import io
import json
from datetime import datetime
from pathlib import Path

DETECTIONS_FILE = Path("/data/detections/detections.jsonl")
EXPORT_DIR = Path("/data/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

CSV_FIELDS = ["timestamp", "species_nl", "species_sci", "confidence", "start_time", "end_time"]


def to_csv_string(entries: list) -> str:
    """Genereer CSV-string van detecties."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(entries)
    return output.getvalue()


def export_to_file(filename: str = None) -> str:
    """Exporteer alle waarnemingen naar CSV bestand. Geeft pad terug."""
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"birdwatch_export_{ts}.csv"

    filepath = EXPORT_DIR / filename

    entries = _load_all()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(entries)

    print(f"[Exporter] {len(entries)} waarnemingen geëxporteerd naar {filepath}")
    return str(filepath)


def _load_all() -> list:
    if not DETECTIONS_FILE.exists():
        return []
    entries = []
    with open(DETECTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries


def list_exports() -> list:
    return sorted([f.name for f in EXPORT_DIR.glob("*.csv")])
