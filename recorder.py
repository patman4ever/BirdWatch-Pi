"""
recorder.py – Opneemt 15-seconden audiofragmenten van de geconfigureerde microfoon.
"""
import os
import time
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
from pathlib import Path

RECORDINGS_DIR = Path("/data/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", 48000))
AUDIO_DEVICE = os.getenv("AUDIO_DEVICE", "default")
CHUNK_SECONDS = 15
CHANNELS = 1

_recording = False
_thread = None


def list_devices():
    """Geef lijst van beschikbare audio-apparaten terug."""
    devices = []
    try:
        device_list = sd.query_devices()
        for i, d in enumerate(device_list):
            if d["max_input_channels"] > 0:
                devices.append({
                    "index": i,
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "sample_rate": int(d["default_samplerate"])
                })
    except Exception as e:
        print(f"[Recorder] Fout bij ophalen apparaten: {e}")
    return devices


def _get_device_index():
    device = AUDIO_DEVICE
    if device == "default" or device == "":
        return None
    try:
        return int(device)
    except ValueError:
        # Naam gebaseerd zoeken
        for i, d in enumerate(sd.query_devices()):
            if device.lower() in d["name"].lower():
                return i
    return None


def record_chunk():
    """Neem één chunk van CHUNK_SECONDS seconden op en sla op als WAV."""
    device_index = _get_device_index()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = RECORDINGS_DIR / f"rec_{timestamp}.wav"

    try:
        audio = sd.rec(
            int(CHUNK_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            device=device_index,
            dtype="float32"
        )
        sd.wait()
        sf.write(str(filepath), audio, SAMPLE_RATE)
        return str(filepath)
    except Exception as e:
        print(f"[Recorder] Opnamefout: {e}")
        return None


def _recording_loop(on_chunk_ready):
    global _recording
    while _recording:
        path = record_chunk()
        if path and on_chunk_ready:
            on_chunk_ready(path)


def start(on_chunk_ready=None):
    global _recording, _thread
    if _recording:
        return
    _recording = True
    _thread = threading.Thread(target=_recording_loop, args=(on_chunk_ready,), daemon=True)
    _thread.start()
    print(f"[Recorder] Gestart op apparaat '{AUDIO_DEVICE}' @ {SAMPLE_RATE}Hz")


def stop():
    global _recording
    _recording = False
    print("[Recorder] Gestopt.")
