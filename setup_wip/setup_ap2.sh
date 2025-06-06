#!/bin/bash

set -e

# --- Config AP variables ---
AP_INTERFACE="uap0"
INTERNET_INTERFACE="wlan0"
AP_IP="192.168.4.1"
DHCP_RANGE_START="192.168.4.2"
DHCP_RANGE_END="192.168.4.20"
DHCP_LEASE_TIME="24h"
AP_SSID="ClimateChamberAP"

# --- Setup internet connection ---
echo "Checking internet connectivity..."
if ping -q -c 2 -W 2 8.8.8.8 >/dev/null; then
  echo "Internet connection is active. Continuing..."
else
  echo "No internet connection detected."

  read -rp "Do you want to set up a Wi-Fi connection now? [Y/n]: " edit_WiFi_connection
  if [[ "$edit_WiFi_connection" =~ ^[Yy]$ || -z "$edit_WiFi_connection" ]]; then
    echo "Scanning for available Wi-Fi networks..."
    if ! command -v nmcli &>/dev/null; then
      echo "Error: nmcli not found. Please install NetworkManager or use an alternative scanner."
      exit 1
    fi

    mapfile -t ssids < <(nmcli -t -f SSID dev wifi | grep -v '^$' | sort -u)

    echo "Available networks:"
    for i in "${!ssids[@]}"; do
      echo "$((i+1)). ${ssids[$i]}"
    done

    echo "Enter the number of the Wi-Fi network to connect to, or type 'M' to manually enter SSID:"
    read -r selection

    if [[ "$selection" =~ ^[Mm]$ ]]; then
      read -rp "Enter SSID: " ssid
    else
      index=$((selection - 1))
      ssid="${ssids[$index]}"
    fi

    read -rsp "Enter password for '$ssid': " password
    echo

    echo "Writing Wi-Fi configuration..."
    cat > /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$ssid"
    psk="$password"
    key_mgmt=WPA-PSK
}
EOF

    echo "Restarting networking services..."
    wpa_cli -i wlan0 reconfigure >/dev/null 2>&1 || sudo systemctl restart wpa_supplicant.service
    dhclient wlan0 || sudo systemctl restart NetworkManager.service

    echo "Waiting for internet connection..."
    for i in {1..5}; do
      if ping -q -c 1 -W 2 8.8.8.8 >/dev/null; then
        echo "Connected to the internet."
        break
      else
        echo "Retrying ($i/5)..."
        sleep 2
      fi
    done

    if ! ping -q -c 1 -W 2 8.8.8.8 >/dev/null; then
      echo "Failed to establish internet connection. Please check your Wi-Fi credentials or configuration."
      exit 1
    fi
  else
    echo "Skipping Wi-Fi configuration."
  fi
fi

# --- Setup I2C and SPI interface ---
read -p "Do you want to enable SPI and I2C interfaces? (y/n) " enable_hardware

if [[ "$enable_hardware" =~ ^[Yy]$ ]]; then
    CONFIG_FILE="/boot/config.txt"

    # Enable I2C
    grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE" || echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_FILE"

    # Enable SPI
    grep -q "^dtparam=spi=on" "$CONFIG_FILE" || echo "dtparam=spi=on" | sudo tee -a "$CONFIG_FILE"

    # Enable modules
    MODULES_FILE="/etc/modules"
    for module in i2c-dev spi-dev; do
        grep -q "^$module" "$MODULES_FILE" || echo "$module" | sudo tee -a "$MODULES_FILE"
    done
fi

# --- Setup Wi-Fi access point ---
while true; do
    read -s -p "Enter Wi-Fi password for AP (min 8 characters): " AP_PASS_1
    echo
    read -s -p "Confirm Wi-Fi password: " AP_PASS_2
    echo
    if [[ "$AP_PASS_1" != "$AP_PASS_2" ]]; then
        echo "❌ Passwords do not match. Please try again."
    elif (( ${#AP_PASS_1} < 8 )); then
        echo "❌ Password must be at least 8 characters long."
    else
        AP_PASS="$AP_PASS_1"
        unset AP_PASS_1
        unset AP_PASS_2
        break
    fi
done

echo "Installing required packages..."
apt update && apt install -y hostapd dnsmasq iw

echo "Stopping services for configuration..."
systemctl stop hostapd
systemctl stop dnsmasq

echo "Creating virtual AP interface..."
iw dev wlan0 interface add $AP_INTERFACE type __ap || true

echo "Configuring static IP for $AP_INTERFACE..."
cat >> /etc/dhcpcd.conf <<EOF

interface $AP_INTERFACE
    static ip_address=$AP_IP/24
    nohook wpa_supplicant
EOF

service dhcpcd restart

echo "Configuring dnsmasq..."
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
cat > /etc/dnsmasq.conf <<EOF
interface=$AP_INTERFACE
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,255.255.255.0,$DHCP_LEASE_TIME
EOF

echo "Creating hostapd config..."
cat > /etc/hostapd/hostapd.conf <<EOF
interface=$AP_INTERFACE
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > /etc/default/hostapd

echo "Enabling IP forwarding..."
sed -i 's|#net.ipv4.ip_forward=1|net.ipv4.ip_forward=1|' /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1

echo "Setting up NAT with iptables..."
iptables -t nat -A POSTROUTING -o $INTERNET_INTERFACE -j MASQUERADE
iptables -A FORWARD -i $INTERNET_INTERFACE -o $AP_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i $AP_INTERFACE -o $INTERNET_INTERFACE -j ACCEPT
sh -c "iptables-save > /etc/iptables.ipv4.nat"

echo "Configuring iptables to restore on boot..."
RC_LOCAL="/etc/rc.local"
if [ ! -f "$RC_LOCAL" ]; then
    echo -e "#!/bin/bash\nexit 0" > "$RC_LOCAL"
    chmod +x "$RC_LOCAL"
fi

sed -i '/^exit 0/i \
# Create virtual AP interface on boot\n\
iw dev wlan0 interface add uap0 type __ap || true\n\
# Restore iptables rules\n\
iptables-restore < /etc/iptables.ipv4.nat\n' "$RC_LOCAL"

echo "Starting and enabling services..."
systemctl start hostapd
systemctl start dnsmasq
systemctl enable hostapd
systemctl enable dnsmasq

echo "Rebooting system to apply changes..."
reboot
