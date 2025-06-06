#!/bin/bash

set -e

# --- Config variables ---
WIFI_INTERFACE="wlan0"
PING_HOST="8.8.8.8"
PING_COUNT=3
TIMEOUT=30

echo "=== WiFi Connection Setup Script ==="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Check if wifi interface exists
if ! ip link show "$WIFI_INTERFACE" &> /dev/null; then
    echo "❌ WiFi interface $WIFI_INTERFACE not found"
    echo "Available interfaces:"
    ip link show | grep -E "^[0-9]+:" | cut -d: -f2 | sed 's/^ *//'
    exit 1
fi

echo "== Ensuring WiFi interface is up =="
ip link set "$WIFI_INTERFACE" up

echo "== Scanning for available networks =="
echo "Scanning... (this may take a few seconds)"

# Scan for networks and parse results
scan_results=$(iwlist "$WIFI_INTERFACE" scan 2>/dev/null | grep -E "ESSID|Quality|Encryption" | paste - - - | sort -k2 -nr)

if [[ -z "$scan_results" ]]; then
    echo "❌ No WiFi networks found. Make sure WiFi is enabled and networks are nearby."
    exit 1
fi

echo ""
echo "Available WiFi networks:"
echo "========================"

# Parse and display networks
declare -a ssids
declare -a qualities
declare -a encryptions
i=0

while IFS= read -r line; do
    if [[ $line =~ ESSID:\"([^\"]+)\" ]]; then
        ssid="${BASH_REMATCH[1]}"
        if [[ -n "$ssid" && "$ssid" != "" ]]; then
            quality=$(echo "$line" | grep -o "Quality=[0-9]*/[0-9]*" | cut -d= -f2)
            encryption=$(echo "$line" | grep -o "Encryption key:[on|off]*" | cut -d: -f2)

            ssids[$i]="$ssid"
            qualities[$i]="$quality"
            encryptions[$i]="$encryption"

            echo "[$((i+1))] $ssid (Quality: $quality, Encryption: $encryption)"
            ((i++))
        fi
    fi
done <<< "$scan_results"

if [[ ${#ssids[@]} -eq 0 ]]; then
    echo "❌ No valid WiFi networks found."
    exit 1
fi

echo ""
echo "Select a network (enter number 1-${#ssids[@]}):"
read -p "Choice: " choice

# Validate choice
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt ${#ssids[@]} ]]; then
    echo "❌ Invalid choice"
    exit 1
fi

selected_ssid="${ssids[$((choice-1))]}"
selected_encryption="${encryptions[$((choice-1))]}"

echo "Selected network: $selected_ssid"

# Get password if network is encrypted
if [[ "$selected_encryption" == "on" ]]; then
    while true; do
        read -s -p "Enter password for '$selected_ssid': " wifi_password
        echo
        if [[ ${#wifi_password} -lt 8 ]]; then
            echo "❌ Password must be at least 8 characters long"
        else
            break
        fi
    done
else
    wifi_password=""
    echo "ℹ️  Network is open (no password required)"
fi

echo ""
echo "== Disconnecting from current network =="
# Kill any existing wpa_supplicant processes
pkill wpa_supplicant || true
sleep 2

echo "== Creating wpa_supplicant configuration =="
WPA_CONFIG="/tmp/wpa_supplicant_temp.conf"

cat > "$WPA_CONFIG" << EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US
EOF

if [[ "$selected_encryption" == "on" ]]; then
    # Add encrypted network
    wpa_passphrase "$selected_ssid" "$wifi_password" >> "$WPA_CONFIG"
else
    # Add open network
    cat >> "$WPA_CONFIG" << EOF

network={
    ssid="$selected_ssid"
    key_mgmt=NONE
}
EOF
fi

echo "== Connecting to $selected_ssid =="
echo "Attempting to connect... (timeout: ${TIMEOUT}s)"

# Start wpa_supplicant in background
wpa_supplicant -B -i "$WIFI_INTERFACE" -c "$WPA_CONFIG" -D nl80211,wext

# Wait for connection
echo "Waiting for connection..."
connected=false
for ((i=1; i<=TIMEOUT; i++)); do
    if iwconfig "$WIFI_INTERFACE" 2>/dev/null | grep -q "$selected_ssid"; then
        connected=true
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

if [[ "$connected" == false ]]; then
    echo "❌ Failed to connect to $selected_ssid within ${TIMEOUT} seconds"
    pkill wpa_supplicant || true
    rm -f "$WPA_CONFIG"
    exit 1
fi

echo "✅ Connected to $selected_ssid"

echo "== Obtaining IP address =="
echo "Requesting IP address via DHCP..."

# Release any existing IP
dhclient -r "$WIFI_INTERFACE" 2>/dev/null || true

# Request new IP
if timeout 20 dhclient "$WIFI_INTERFACE"; then
    ip_addr=$(ip addr show "$WIFI_INTERFACE" | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
    if [[ -n "$ip_addr" ]]; then
        echo "✅ Obtained IP address: $ip_addr"
    else
        echo "⚠️  DHCP completed but no IP address detected"
    fi
else
    echo "❌ Failed to obtain IP address via DHCP"
    pkill wpa_supplicant || true
    rm -f "$WPA_CONFIG"
    exit 1
fi

echo ""
echo "== Testing internet connection =="
echo "Pinging $PING_HOST ($PING_COUNT times)..."

if ping -c "$PING_COUNT" -W 5 "$PING_HOST" > /dev/null 2>&1; then
    echo "✅ Internet connection successful!"

    # Test DNS resolution as well
    if ping -c 1 -W 5 google.com > /dev/null 2>&1; then
        echo "✅ DNS resolution working"
    else
        echo "⚠️  Internet reachable but DNS resolution may have issues"
    fi
else
    echo "❌ Internet connection failed"
    echo "You are connected to WiFi but internet may not be available"
fi

echo ""
echo "== Connection Summary =="
echo "Network: $selected_ssid"
echo "Interface: $WIFI_INTERFACE"
echo "IP Address: $(ip addr show "$WIFI_INTERFACE" | grep "inet " | awk '{print $2}' | cut -d'/' -f1 || echo 'Not assigned')"
echo "Gateway: $(ip route | grep default | grep "$WIFI_INTERFACE" | awk '{print $3}' || echo 'Not found')"

echo ""
echo "== Making connection persistent =="
# Copy temp config to permanent location
cp "$WPA_CONFIG" /etc/wpa_supplicant/wpa_supplicant.conf
rm -f "$WPA_CONFIG"

# Enable wpa_supplicant service
systemctl enable wpa_supplicant@"$WIFI_INTERFACE".service
systemctl start wpa_supplicant@"$WIFI_INTERFACE".service

echo "✅ WiFi connection setup complete!"
echo ""
echo "Your Raspberry Pi is now connected to: $selected_ssid"
echo "The connection will persist after reboot."

# Clear password from memory
unset wifi_password