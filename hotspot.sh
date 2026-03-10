#!/bin/bash
# ================================================================
# scripts/hotspot.sh – Wi-Fi hotspot voor veldgebruik zonder router
# Gebruik: bash scripts/hotspot.sh start|stop
# ================================================================
SSID="BirdWatch-Pi"
PASSWORD="birdwatch"
IP="10.42.0.1"
IFACE="wlan0"

start_hotspot() {
  echo "➜ Hotspot starten ($SSID)..."

  # Controleer NetworkManager
  if command -v nmcli &>/dev/null; then
    nmcli device wifi hotspot ifname $IFACE ssid "$SSID" password "$PASSWORD" 2>/dev/null \
      && echo "✓ Hotspot actief via NetworkManager" \
      && echo "  Verbind met: $SSID / $PASSWORD" \
      && echo "  Web UI: http://$IP:7766" \
      && exit 0
  fi

  # Fallback: hostapd + dnsmasq
  if ! command -v hostapd &>/dev/null; then
    echo "➜ hostapd en dnsmasq installeren..."
    sudo apt-get install -y hostapd dnsmasq
  fi

  sudo systemctl stop hostapd dnsmasq 2>/dev/null || true

  # Hostapd config
  sudo tee /tmp/hostapd.conf > /dev/null <<EOF
interface=$IFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$PASSWORD
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

  # Dnsmasq config
  sudo tee /tmp/dnsmasq-hotspot.conf > /dev/null <<EOF
interface=$IFACE
dhcp-range=10.42.0.10,10.42.0.50,12h
address=/#/$IP
EOF

  sudo ip addr add $IP/24 dev $IFACE 2>/dev/null || true
  sudo ip link set $IFACE up

  sudo hostapd /tmp/hostapd.conf -B
  sudo dnsmasq -C /tmp/dnsmasq-hotspot.conf

  echo "✓ Hotspot actief!"
  echo "  SSID:     $SSID"
  echo "  Wachtw.:  $PASSWORD"
  echo "  Web UI:   http://$IP:7766"
}

stop_hotspot() {
  echo "➜ Hotspot stoppen..."
  nmcli con down Hotspot 2>/dev/null || true
  sudo pkill hostapd 2>/dev/null || true
  sudo pkill dnsmasq 2>/dev/null || true
  echo "✓ Hotspot gestopt."
}

case "$1" in
  start) start_hotspot ;;
  stop)  stop_hotspot ;;
  *)     echo "Gebruik: $0 start|stop" ;;
esac
