#!/bin/bash

set -e  # Exit on any error
set -o pipefail

apt install -y hostapd dnsmasq iw iptables

BACKUP_DIR="/etc/dual_wifi_backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$HOME/dual_wifi_setup.log"
exec &> >(tee -a "$LOG_FILE")

echo "🔧 Backing up configuration files to $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
cp /etc/dhcpcd.conf "$BACKUP_DIR"/
cp /etc/dnsmasq.conf "$BACKUP_DIR"/
cp /etc/default/hostapd "$BACKUP_DIR"/
cp /etc/sysctl.conf "$BACKUP_DIR"/
[ -f /etc/hostapd/hostapd.conf ] && cp /etc/hostapd/hostapd.conf "$BACKUP_DIR"/
[ -f /etc/rc.local ] && cp /etc/rc.local "$BACKUP_DIR"/

trap 'echo "⚠️  Error occurred. Restoring previous configuration..."; cp -r "$BACKUP_DIR"/* /etc/ && systemctl restart dhcpcd && systemctl restart hostapd && systemctl restart dnsmasq && echo "✅ Restoration complete."; exit 1' ERR

echo "📦 Updating and installing required packages..."
apt update && apt full-upgrade -y
apt install -y hostapd dnsmasq iw

echo "🛑 Stopping conflicting services..."
systemctl stop hostapd || true
systemctl stop dnsmasq || true

echo "🧩 Creating virtual AP interface uap0..."
iw dev wlan0 interface add uap0 type __ap || true

echo "📌 Assigning static IP to uap0..."
cat <<EOF >> /etc/dhcpcd.conf

interface uap0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF

service dhcpcd restart

echo "🧰 Configuring dnsmasq..."
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
cat <<EOF > /etc/dnsmasq.conf
interface=uap0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

echo "🌐 Configuring hostapd..."
cat <<EOF > /etc/hostapd/hostapd.conf
interface=uap0
driver=nl80211
ssid=Pi4BAP
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=Pi4password
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

sed -i 's|#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

echo "📢 Enabling IP forwarding..."
sed -i 's|#net.ipv4.ip_forward=1|net.ipv4.ip_forward=1|' /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1

echo "📤 Setting up NAT with iptables..."
iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
iptables -A FORWARD -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i uap0 -o wlan0 -j ACCEPT

sh -c "iptables-save > /etc/iptables.ipv4.nat"

echo "🔁 Modifying /etc/rc.local for boot-time restoration..."
RCLOCAL="/etc/rc.local"
[ ! -f "$RCLOCAL" ] && echo -e '#!/bin/bash\nexit 0' > "$RCLOCAL" && chmod +x "$RCLOCAL"

sed -i '/exit 0/i \
iw dev wlan0 interface add uap0 type __ap || true\n\
iptables-restore < /etc/iptables.ipv4.nat' "$RCLOCAL"

echo "🚀 Enabling and starting services..."
systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq
systemctl start hostapd
systemctl start dnsmasq

echo "🔁 Rebooting..."
reboot
