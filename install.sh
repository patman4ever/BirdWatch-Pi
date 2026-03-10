#!/bin/bash
# ================================================================
# BirdWatch-Pi – Installatie & start script
# Gebruik: sudo bash install.sh
# ================================================================
set -e

REPO_URL="https://github.com/patman4ever/BirdWatch-Pi"
INSTALL_DIR="$HOME/BirdWatch-Pi"
COMPOSE_CMD="docker compose"

echo ""
echo "🐦 BirdWatch-Pi Installer"
echo "========================="

# ── Controleer Docker ──────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "➜ Docker niet gevonden. Installeren..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "✓ Docker geïnstalleerd. Log opnieuw in als nieuwe sessie nodig is."
fi

if ! $COMPOSE_CMD version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
fi

# ── Clone of update repo ───────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "➜ Repo bijwerken..."
  cd "$INSTALL_DIR" && git pull
else
  echo "➜ Repo klonen van $REPO_URL..."
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ── Kopieer config als die nog niet bestaat ────────────────────
if [ ! -f "$INSTALL_DIR/config.env" ]; then
  cp "$INSTALL_DIR/config.env.example" "$INSTALL_DIR/config.env" 2>/dev/null || true
fi

# ── Maak data-directories ──────────────────────────────────────
mkdir -p "$INSTALL_DIR/data/recordings"
mkdir -p "$INSTALL_DIR/data/detections"
mkdir -p "$INSTALL_DIR/data/exports"

# ── Audio apparaten tonen ──────────────────────────────────────
echo ""
echo "📻 Beschikbare audio-invoerapparaten:"
arecord -l 2>/dev/null || echo "  (arecord niet beschikbaar – audio info via web UI)"

# ── Build en start ─────────────────────────────────────────────
echo ""
echo "➜ Container bouwen..."
$COMPOSE_CMD -f "$INSTALL_DIR/docker-compose.yml" build

echo ""
echo "➜ Container starten..."
$COMPOSE_CMD -f "$INSTALL_DIR/docker-compose.yml" up -d

# ── Wacht en geef URL ──────────────────────────────────────────
sleep 3
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "✓ BirdWatch-Pi is actief!"
echo ""
echo "  Web interface: http://$IP:7766"
echo "  Lokaal:        http://localhost:7766"
echo ""
echo "  Instellingen bewerken:"
echo "    nano $INSTALL_DIR/config.env"
echo "    $COMPOSE_CMD -C $INSTALL_DIR restart"
echo ""
echo "  Logs bekijken:"
echo "    $COMPOSE_CMD -C $INSTALL_DIR logs -f"
echo ""
