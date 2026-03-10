"""
server.py – BirdWatch-Pi webserver
Lightweight Flask app geoptimaliseerd voor Raspberry Pi in het veld.
Tekst-only interface, geen zware assets.
"""
import os
import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, Response, stream_with_context, request, send_file

import recorder
import analyzer
import exporter

app = Flask(__name__)

# Queue voor Server-Sent Events (live feed)
_sse_clients = []
_sse_lock = threading.Lock()


def _broadcast(entry: dict):
    msg = f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


analyzer.subscribe(_broadcast)


# ─── HTML Templates (inline, geen externe bestanden) ─────────────────────────

BASE_CSS = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Courier New', monospace;
    background: #0a0f0a;
    color: #7fff7f;
    font-size: 14px;
    line-height: 1.5;
  }
  header {
    background: #0d1a0d;
    border-bottom: 1px solid #2a4a2a;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header h1 { font-size: 16px; letter-spacing: 2px; color: #afffaf; }
  header .status { font-size: 11px; color: #4a8a4a; }
  header .status.active { color: #7fff7f; }
  nav {
    background: #0d1a0d;
    border-bottom: 1px solid #1a3a1a;
    padding: 6px 16px;
    display: flex;
    gap: 16px;
  }
  nav a {
    color: #5aaa5a;
    text-decoration: none;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 2px 8px;
  }
  nav a:hover, nav a.active { color: #afffaf; background: #1a2a1a; }
  .container { padding: 12px 16px; }
  .card {
    background: #0d1a0d;
    border: 1px solid #1a3a1a;
    padding: 12px;
    margin-bottom: 10px;
  }
  .card h2 { font-size: 12px; letter-spacing: 2px; color: #4a8a4a; margin-bottom: 8px; }
  .detection-row {
    padding: 4px 0;
    border-bottom: 1px solid #0f1f0f;
    display: flex;
    gap: 12px;
  }
  .detection-row:last-child { border-bottom: none; }
  .det-time { color: #4a8a4a; min-width: 70px; font-size: 12px; }
  .det-name { color: #afffaf; flex: 1; }
  .det-sci { color: #4a8a4a; font-style: italic; font-size: 12px; }
  .det-conf { min-width: 45px; text-align: right; }
  .conf-high { color: #7fff7f; }
  .conf-mid { color: #afaf00; }
  .conf-low { color: #8a6a00; }
  .form-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
  label { color: #4a8a4a; font-size: 12px; min-width: 140px; }
  input, select {
    background: #0a0f0a;
    border: 1px solid #2a4a2a;
    color: #7fff7f;
    padding: 4px 8px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    flex: 1;
  }
  button {
    background: #1a3a1a;
    border: 1px solid #3a6a3a;
    color: #afffaf;
    padding: 6px 16px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    cursor: pointer;
    letter-spacing: 1px;
  }
  button:hover { background: #2a4a2a; }
  button.danger { border-color: #6a3a1a; color: #ffaf7f; }
  .badge {
    display: inline-block;
    font-size: 10px;
    padding: 1px 5px;
    border: 1px solid currentColor;
    letter-spacing: 1px;
  }
  .new-flash { animation: flash 1s ease; }
  @keyframes flash {
    0% { background: #1a4a1a; }
    100% { background: transparent; }
  }
  #live-status { font-size: 11px; color: #4a8a4a; }
  #live-status.connected { color: #7fff7f; }
  .stat-row { display: flex; gap: 20px; flex-wrap: wrap; }
  .stat { text-align: center; }
  .stat .val { font-size: 24px; color: #afffaf; }
  .stat .lbl { font-size: 10px; color: #4a8a4a; letter-spacing: 1px; }
  #device-list { font-size: 12px; color: #4a8a4a; margin-top: 6px; }
  .export-list a { color: #5aaa5a; font-size: 12px; }
</style>
"""

NAV = """
<nav>
  <a href="/" {live}>▶ LIVE</a>
  <a href="/history" {hist}>◷ HISTORY</a>
  <a href="/settings" {cfg}>⚙ CONFIG</a>
  <a href="/export" {exp}>⬇ EXPORT</a>
</nav>
"""

def nav(active):
    keys = {"live": "", "hist": "", "cfg": "", "exp": ""}
    keys[active] = 'class="active"'
    return NAV.format(**keys)


def page(title, content, active="live"):
    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0">
<title>BirdWatch-Pi – {title}</title>
{BASE_CSS}
</head>
<body>
<header>
  <h1>🐦 BIRDWATCH-PI</h1>
  <span class="status active" id="rec-status">● REC</span>
</header>
{nav(active)}
<div class="container">
{content}
</div>
</body>
</html>"""


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    recent = analyzer.get_recent(50)
    rows = ""
    for d in recent:
        t = d["timestamp"][11:19]
        conf = d["confidence"]
        conf_cls = "conf-high" if conf >= 0.9 else ("conf-mid" if conf >= 0.8 else "conf-low")
        rows += f"""<div class="detection-row" id="det-{t}">
  <span class="det-time">{t}</span>
  <span class="det-name">{d['species_nl']}</span>
  <span class="det-sci">{d['species_sci']}</span>
  <span class="det-conf {conf_cls}">{conf:.0%}</span>
</div>"""

    if not rows:
        rows = '<div style="color:#4a8a4a;padding:8px;">Nog geen waarnemingen...</div>'

    content = f"""
<div class="card">
  <h2>LIVE WAARNEMINGEN &nbsp;<span id="live-status">● verbinden...</span></h2>
  <div id="detections">{rows}</div>
</div>

<script>
const MAX_ROWS = 50;
const box = document.getElementById('detections');
const status = document.getElementById('live-status');

function conf_class(c) {{
  if (c >= 0.9) return 'conf-high';
  if (c >= 0.8) return 'conf-mid';
  return 'conf-low';
}}

const es = new EventSource('/stream');
es.onopen = () => {{ status.textContent = '● verbonden'; status.className = 'connected'; }};
es.onerror = () => {{ status.textContent = '○ verbroken'; status.className = ''; }};
es.onmessage = (e) => {{
  const d = JSON.parse(e.data);
  const t = d.timestamp.substring(11,19);
  const cc = conf_class(d.confidence);
  const row = document.createElement('div');
  row.className = 'detection-row new-flash';
  row.innerHTML = `<span class="det-time">${{t}}</span>
    <span class="det-name">${{d.species_nl}}</span>
    <span class="det-sci">${{d.species_sci}}</span>
    <span class="det-conf ${{cc}}">${{(d.confidence*100).toFixed(0)}}%</span>`;
  box.insertBefore(row, box.firstChild);
  while (box.children.length > MAX_ROWS) box.removeChild(box.lastChild);
}};
</script>"""

    return page("Live", content, "live")


@app.route("/stream")
def stream():
    """Server-Sent Events endpoint voor live detecties."""
    q = queue.Queue(maxsize=20)
    with _sse_lock:
        _sse_clients.append(q)

    def generate():
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            try:
                msg = q.get(timeout=30)
                yield msg
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/history")
def history():
    entries = analyzer.load_history(200)
    # Statistieken
    total = len(entries)
    species = {}
    for e in entries:
        n = e.get("species_nl", "?")
        species[n] = species.get(n, 0) + 1
    top = sorted(species.items(), key=lambda x: x[1], reverse=True)[:10]

    stats = f"""<div class="card">
  <h2>STATISTIEKEN</h2>
  <div class="stat-row">
    <div class="stat"><div class="val">{total}</div><div class="lbl">WAARNEMINGEN</div></div>
    <div class="stat"><div class="val">{len(species)}</div><div class="lbl">SOORTEN</div></div>
  </div>
</div>"""

    top_html = "".join(
        f'<div class="detection-row"><span class="det-name">{n}</span>'
        f'<span class="det-conf conf-high">{c}×</span></div>'
        for n, c in top
    )
    top_card = f'<div class="card"><h2>TOP SOORTEN</h2>{top_html}</div>'

    rows = "".join(
        f'<div class="detection-row">'
        f'<span class="det-time">{e["timestamp"][8:10]}/{e["timestamp"][5:7]} {e["timestamp"][11:19]}</span>'
        f'<span class="det-name">{e["species_nl"]}</span>'
        f'<span class="det-sci">{e["species_sci"]}</span>'
        f'<span class="det-conf {"conf-high" if e["confidence"]>=0.9 else "conf-mid"}">{e["confidence"]:.0%}</span>'
        f'</div>'
        for e in entries
    ) or '<div style="color:#4a8a4a;padding:8px;">Geen geschiedenis gevonden.</div>'

    content = stats + top_card + f'<div class="card"><h2>ALLE WAARNEMINGEN</h2>{rows}</div>'
    return page("History", content, "hist")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    msg = ""
    if request.method == "POST":
        # Schrijf config.env bij
        data = request.form
        lines = []
        for key in ["AUDIO_DEVICE", "SAMPLE_RATE", "MIN_CONFIDENCE",
                    "LOCATION_LAT", "LOCATION_LON", "LANGUAGE"]:
            val = data.get(key, "")
            lines.append(f"{key}={val}")
        try:
            Path("/app/config.env").write_text("\n".join(lines))
            msg = '<div style="color:#7fff7f;margin-bottom:8px;">✓ Instellingen opgeslagen. Herstart container voor effect.</div>'
        except Exception as e:
            msg = f'<div style="color:#ff7f7f;margin-bottom:8px;">✗ Fout: {e}</div>'

    # Huidige waarden
    cur = {
        "AUDIO_DEVICE": os.getenv("AUDIO_DEVICE", "default"),
        "SAMPLE_RATE": os.getenv("SAMPLE_RATE", "48000"),
        "MIN_CONFIDENCE": os.getenv("MIN_CONFIDENCE", "0.7"),
        "LOCATION_LAT": os.getenv("LOCATION_LAT", "52.3"),
        "LOCATION_LON": os.getenv("LOCATION_LON", "5.0"),
        "LANGUAGE": os.getenv("LANGUAGE", "nl"),
    }

    # Apparatenlijst
    devices = recorder.list_devices()
    dev_opts = "".join(
        f'<option value="{d["index"]}" {"selected" if str(d["index"])==cur["AUDIO_DEVICE"] else ""}>'
        f'{d["index"]}: {d["name"]} ({d["channels"]}ch @ {d["sample_rate"]}Hz)</option>'
        for d in devices
    )
    if not dev_opts:
        dev_opts = '<option value="default">default (geen apparaten gevonden)</option>'

    content = f"""
{msg}
<div class="card">
  <h2>AUDIO CONFIGURATIE</h2>
  <form method="post">
    <div class="form-row">
      <label>Microfoon/Apparaat</label>
      <select name="AUDIO_DEVICE">{dev_opts}</select>
    </div>
    <div class="form-row">
      <label>Sample Rate (Hz)</label>
      <input name="SAMPLE_RATE" value="{cur['SAMPLE_RATE']}" type="number" step="1000">
    </div>
    <div class="form-row">
      <label>Min. Betrouwbaarheid</label>
      <input name="MIN_CONFIDENCE" value="{cur['MIN_CONFIDENCE']}" type="number" step="0.05" min="0.1" max="1.0">
    </div>
</div>
<div class="card">
  <h2>LOCATIE</h2>
    <div class="form-row">
      <label>Breedtegraad (lat)</label>
      <input name="LOCATION_LAT" value="{cur['LOCATION_LAT']}" type="number" step="0.01">
    </div>
    <div class="form-row">
      <label>Lengtegraad (lon)</label>
      <input name="LOCATION_LON" value="{cur['LOCATION_LON']}" type="number" step="0.01">
    </div>
    <div class="form-row">
      <label>Taal resultaten</label>
      <select name="LANGUAGE">
        <option value="nl" {"selected" if cur["LANGUAGE"]=="nl" else ""}>Nederlands</option>
        <option value="en" {"selected" if cur["LANGUAGE"]=="en" else ""}>English</option>
        <option value="de" {"selected" if cur["LANGUAGE"]=="de" else ""}>Deutsch</option>
      </select>
    </div>
  <div style="margin-top:10px;">
    <button type="submit">OPSLAAN</button>
  </div>
  </form>
</div>"""

    return page("Instellingen", content, "cfg")


@app.route("/export")
def export_page():
    exports = exporter.list_exports()
    export_links = "".join(
        f'<div class="detection-row"><span class="det-name export-list">'
        f'<a href="/export/download/{f}">{f}</a></span></div>'
        for f in exports
    ) or '<div style="color:#4a8a4a;padding:8px;">Geen exports beschikbaar.</div>'

    content = f"""
<div class="card">
  <h2>CSV EXPORT</h2>
  <p style="font-size:12px;color:#4a8a4a;margin-bottom:10px;">
    Exporteer alle waarnemingen naar CSV voor gebruik in Excel/LibreOffice.
  </p>
  <form method="post" action="/export/create">
    <button type="submit">⬇ NIEUWE CSV EXPORT</button>
  </form>
</div>
<div class="card">
  <h2>BESCHIKBARE EXPORTS</h2>
  {export_links}
</div>"""

    return page("Export", content, "exp")


@app.route("/export/create", methods=["POST"])
def export_create():
    filepath = exporter.export_to_file()
    filename = Path(filepath).name
    from flask import redirect
    return redirect(f"/export/download/{filename}")


@app.route("/export/download/<filename>")
def export_download(filename):
    filepath = Path("/data/exports") / filename
    if not filepath.exists() or not filename.endswith(".csv"):
        return "Bestand niet gevonden", 404
    return send_file(str(filepath), as_attachment=True, mimetype="text/csv")


@app.route("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ─── Startup ─────────────────────────────────────────────────────────────────

def _analysis_callback(filepath):
    analyzer.analyze(filepath)


if __name__ == "__main__":
    print("[BirdWatch-Pi] Starten...")
    recorder.start(on_chunk_ready=_analysis_callback)
    app.run(host="0.0.0.0", port=7766, threaded=True, debug=False)
