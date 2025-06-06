#!/bin/bash

set -e

# Function to check if a package is installed
is_package_installed() {
    dpkg -s "$1" &> /dev/null
}

# --- Config variables ---
AP_INTERFACE="uap0"
INTERNET_INTERFACE="wlan0"
AP_IP="192.168.50.1"
DHCP_RANGE_START="192.168.50.10"
DHCP_RANGE_END="192.168.50.50"
DHCP_LEASE_TIME="24h"
AP_SSID="PiRepeater"

# --- Request password from user ---
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

AP_CHANNEL=6

echo "== Updating and installing required packages =="
apt update

# Install packages if not already installed
for package in hostapd dnsmasq iptables iptables-persistent; do
    if ! is_package_installed "$package"; then
        apt install -y "$package"
    else
        echo "$package is already installed."
    fi
done

echo "== Stopping services to avoid conflicts =="
systemctl stop hostapd || true
systemctl stop dnsmasq || true
systemctl disable hostapd || true
systemctl disable dnsmasq || true

echo "== Creating AP virtual interface $AP_INTERFACE =="
# Remove existing interface if it exists and is wrong type
if ip link show $AP_INTERFACE &> /dev/null; then
    if ! iw dev $AP_INTERFACE info 2>/dev/null | grep -q "type AP"; then
        echo "Removing existing $AP_INTERFACE (wrong type)..."
        ip link delete $AP_INTERFACE 2>/dev/null || true
        sleep 1
    fi
fi

# Create interface if it doesn't exist
if ! ip link show $AP_INTERFACE &> /dev/null; then
    echo "Creating $AP_INTERFACE interface..."
    # Retry logic for interface creation
    for i in {1..5}; do
        if iw phy phy0 interface add $AP_INTERFACE type __ap; then
            echo "Successfully created $AP_INTERFACE"
            break
        else
            echo "Attempt $i failed, retrying in 2 seconds..."
            sleep 2
            if [ $i -eq 5 ]; then
                echo "❌ Failed to create $AP_INTERFACE after 5 attempts"
                exit 1
            fi
        fi
    done
else
    echo "$AP_INTERFACE interface already exists"
fi

# Bring up the uap0 interface
ip link set dev $AP_INTERFACE up

echo "== Configuring NetworkManager to ignore $AP_INTERFACE =="
mkdir -p /etc/NetworkManager/conf.d/
cat <<EOF >/etc/NetworkManager/conf.d/unmanaged.conf
[keyfile]
unmanaged-devices=interface-name:$AP_INTERFACE
EOF
systemctl restart NetworkManager

echo "== Creating robust setup script for $AP_INTERFACE =="
cat <<EOF >/usr/local/bin/setup-$AP_INTERFACE.sh
#!/bin/bash

# Robust setup script for $AP_INTERFACE with proper error handling
set -e

# Configuration
AP_INTERFACE="$AP_INTERFACE"
AP_IP="$AP_IP"
MAX_RETRIES=15
RETRY_DELAY=2

# Logging function
log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a /var/log/setup-$AP_INTERFACE.log
}

log_message "Starting $AP_INTERFACE interface setup..."

# Function to wait for phy0 to be available
wait_for_phy() {
    local retries=0
    while [ \$retries -lt \$MAX_RETRIES ]; do
        if iw phy phy0 info &> /dev/null; then
            log_message "phy0 is available"
            return 0
        fi
        log_message "Waiting for phy0... (attempt \$((retries + 1))/\$MAX_RETRIES)"
        sleep \$RETRY_DELAY
        retries=\$((retries + 1))
    done
    log_message "ERROR: phy0 not available after \$MAX_RETRIES attempts"
    return 1
}

# Function to create interface with retries
create_interface() {
    # Check if interface exists and is correct type
    if ip link show \$AP_INTERFACE &> /dev/null; then
        if iw dev \$AP_INTERFACE info 2>/dev/null | grep -q "type AP"; then
            log_message "\$AP_INTERFACE already exists and is AP type"
            return 0
        else
            log_message "Removing existing \$AP_INTERFACE (wrong type)"
            ip link delete \$AP_INTERFACE 2>/dev/null || true
            sleep 1
        fi
    fi

    local retries=0
    while [ \$retries -lt \$MAX_RETRIES ]; do
        if iw phy phy0 interface add \$AP_INTERFACE type __ap 2>/dev/null; then
            log_message "Successfully created \$AP_INTERFACE interface"
            return 0
        fi
        log_message "Failed to create interface, attempt \$((retries + 1))/\$MAX_RETRIES"
        sleep \$RETRY_DELAY
        retries=\$((retries + 1))
    done

    log_message "ERROR: Failed to create interface after \$MAX_RETRIES attempts"
    return 1
}

# Function to configure IP with retries
configure_ip() {
    # Flush any existing IP addresses
    ip addr flush dev \$AP_INTERFACE 2>/dev/null || true

    local retries=0
    while [ \$retries -lt \$MAX_RETRIES ]; do
        if ip addr add \$AP_IP/24 dev \$AP_INTERFACE 2>/dev/null; then
            log_message "Successfully assigned IP \$AP_IP/24 to \$AP_INTERFACE"
            return 0
        fi
        log_message "Failed to assign IP, attempt \$((retries + 1))/\$MAX_RETRIES"
        sleep \$RETRY_DELAY
        retries=\$((retries + 1))
    done

    log_message "ERROR: Failed to assign IP after \$MAX_RETRIES attempts"
    return 1
}

# Function to bring up interface with retries
bring_up_interface() {
    local retries=0
    while [ \$retries -lt \$MAX_RETRIES ]; do
        if ip link set dev \$AP_INTERFACE up 2>/dev/null; then
            # Verify interface is actually up
            sleep 1
            if ip link show \$AP_INTERFACE | grep -q "state UP"; then
                log_message "Successfully brought up \$AP_INTERFACE"
                return 0
            fi
        fi
        log_message "Failed to bring up interface, attempt \$((retries + 1))/\$MAX_RETRIES"
        sleep \$RETRY_DELAY
        retries=\$((retries + 1))
    done

    log_message "ERROR: Failed to bring up interface after \$MAX_RETRIES attempts"
    return 1
}

# Main execution with comprehensive error handling
main() {
    # Wait for wireless hardware to be ready
    if ! wait_for_phy; then
        exit 1
    fi

    # Create the interface
    if ! create_interface; then
        exit 1
    fi

    # Configure IP address
    if ! configure_ip; then
        exit 1
    fi

    # Bring up the interface
    if ! bring_up_interface; then
        exit 1
    fi

    # Wait for interface to stabilize
    sleep 3

    # Final verification
    if ip link show \$AP_INTERFACE | grep -q "state UP" && ip addr show \$AP_INTERFACE | grep -q "\$AP_IP/24"; then
        log_message "SUCCESS: \$AP_INTERFACE is fully configured and ready"

        # Create ready signal for dependent services
        touch /var/run/uap0-ready

        # Restore iptables rules if they exist
        if [ -f /etc/iptables.ipv4.nat ]; then
            log_message "Restoring iptables rules..."
            iptables-restore < /etc/iptables.ipv4.nat || log_message "WARNING: Failed to restore iptables rules"
        fi

        exit 0
    else
        log_message "ERROR: Final verification failed"
        exit 1
    fi
}

# Execute main function
main
EOF
chmod +x /usr/local/bin/setup-$AP_INTERFACE.sh

echo "== Creating enhanced systemd service for $AP_INTERFACE =="
cat <<EOF >/etc/systemd/system/setup-$AP_INTERFACE.service
[Unit]
Description=Setup $AP_INTERFACE AP interface
After=network.target NetworkManager.service wpa_supplicant.service
Wants=network.target
Before=hostapd.service dnsmasq.service
RequiredBy=hostapd.service dnsmasq.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-$AP_INTERFACE.sh
RemainAfterExit=yes
Restart=on-failure
RestartSec=10
TimeoutStartSec=120

# Ensure proper environment
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
RequiredBy=hostapd.service dnsmasq.service
EOF

echo "== Creating systemd service overrides for proper dependencies =="
# Create override directories
mkdir -p /etc/systemd/system/hostapd.service.d
mkdir -p /etc/systemd/system/dnsmasq.service.d

# Create hostapd service override to wait for interface
cat <<EOF >/etc/systemd/system/hostapd.service.d/override.conf
[Unit]
After=setup-$AP_INTERFACE.service
Requires=setup-$AP_INTERFACE.service

[Service]
# Wait for interface to be ready before starting
ExecStartPre=/bin/bash -c 'timeout 60 bash -c "while [ ! -f /var/run/uap0-ready ]; do sleep 1; done"'
Restart=on-failure
RestartSec=10
EOF

# Create dnsmasq service override to wait for interface
cat <<EOF >/etc/systemd/system/dnsmasq.service.d/override.conf
[Unit]
After=setup-$AP_INTERFACE.service
Requires=setup-$AP_INTERFACE.service

[Service]
# Wait for interface to be ready before starting
ExecStartPre=/bin/bash -c 'timeout 60 bash -c "while [ ! -f /var/run/uap0-ready ]; do sleep 1; done"'
Restart=on-failure
RestartSec=10
EOF

echo "== Configuring hostapd =="
cat <<EOF >/etc/hostapd/hostapd.conf
interface=$AP_INTERFACE
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=$AP_CHANNEL
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASS
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Configure hostapd daemon
cat <<EOF >/etc/default/hostapd
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF

echo "== Configuring dnsmasq =="
# Backup original dnsmasq.conf
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.orig 2>/dev/null || true

cat <<EOF >/etc/dnsmasq.conf
# Only bind to the AP interface
interface=$AP_INTERFACE
# Don't bind to wlan0 or other interfaces
bind-interfaces
# DHCP range
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,255.255.255.0,$DHCP_LEASE_TIME
# Use the Pi as DNS server
dhcp-option=6,$AP_IP
EOF

echo "== Enabling IP forwarding =="
sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1

echo "== Setting up iptables rules for NAT =="
# Clear any existing rules that might conflict
iptables -t nat -F POSTROUTING 2>/dev/null || true
iptables -F FORWARD 2>/dev/null || true

# Add NAT and forwarding rules
iptables -t nat -A POSTROUTING -o $INTERNET_INTERFACE -j MASQUERADE
iptables -A FORWARD -i $INTERNET_INTERFACE -o $AP_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i $AP_INTERFACE -o $INTERNET_INTERFACE -j ACCEPT

echo "== Saving iptables rules =="
iptables-save > /etc/iptables.ipv4.nat

echo "== Creating enhanced /etc/rc.local for iptables restoration =="
cat <<'EOF' >/etc/rc.local
#!/bin/sh -e
# Restore iptables rules
if [ -f /etc/iptables.ipv4.nat ]; then
    iptables-restore < /etc/iptables.ipv4.nat
fi
exit 0
EOF
chmod +x /etc/rc.local

echo "== Creating additional boot-time interface check =="
# Add a cron job to ensure interface persists
cat <<EOF >/etc/cron.d/check-uap0
# Check uap0 interface every minute and recreate if missing
* * * * * root /usr/local/bin/setup-$AP_INTERFACE.sh >/dev/null 2>&1 || true
EOF

echo "== Reloading systemd and configuring services =="
systemctl daemon-reload
systemctl unmask hostapd
systemctl unmask dnsmasq

# Clean up any existing interface and ready signal
ip link delete $AP_INTERFACE 2>/dev/null || true
rm -f /var/run/uap0-ready

# Enable services with proper dependencies
systemctl enable setup-$AP_INTERFACE.service
systemctl enable hostapd.service
systemctl enable dnsmasq.service

echo "== Testing setup script execution =="
if /usr/local/bin/setup-$AP_INTERFACE.sh; then
    echo "✅ Setup script executed successfully"
else
    echo "❌ Setup script failed - check logs"
    echo "Debug: Run 'sudo tail -f /var/log/setup-$AP_INTERFACE.log' for details"
fi

echo "== Starting services in correct order =="
systemctl start setup-$AP_INTERFACE.service
sleep 3

systemctl start dnsmasq.service
sleep 2

systemctl start hostapd.service
sleep 3

# Give services time to fully start
sleep 5

# Verify services are running
echo "== Service Status Check =="
for service in setup-$AP_INTERFACE dnsmasq hostapd; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service failed to start"
        echo "   Status: $(systemctl is-active $service 2>/dev/null)"
        echo "   Try: sudo journalctl -u $service --no-pager -l"
    fi
done

# Verify interface status
echo ""
echo "== Interface Status Check =="
if ip link show $AP_INTERFACE &> /dev/null; then
    if ip link show $AP_INTERFACE | grep -q "state UP"; then
        echo "✅ $AP_INTERFACE exists and is UP"
        if ip addr show $AP_INTERFACE | grep -q "$AP_IP/24"; then
            echo "✅ $AP_INTERFACE has correct IP address"
        else
            echo "❌ $AP_INTERFACE missing correct IP address"
        fi
    else
        echo "❌ $AP_INTERFACE exists but is DOWN"
    fi
else
    echo "❌ $AP_INTERFACE does not exist"
fi

echo ""
echo "== AP Configuration Summary =="
echo "SSID: $AP_SSID"
echo "Password: [hidden]"
echo "AP IP: $AP_IP"
echo "DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
echo "Channel: $AP_CHANNEL"

echo ""
echo "== Setup AP complete! =="
echo ""
echo "📋 Troubleshooting commands:"
echo "   • Check setup logs: sudo tail -f /var/log/setup-$AP_INTERFACE.log"
echo "   • Check service status: sudo systemctl status setup-$AP_INTERFACE hostapd dnsmasq"
echo "   • Check interface: ip addr show $AP_INTERFACE"
echo "   • Test interface creation: sudo /usr/local/bin/setup-$AP_INTERFACE.sh"
echo "   • View service logs: sudo journalctl -u hostapd -u dnsmasq -f"

# Optional: Enable SPI and I2C interfaces
read -p "Do you want to enable SPI and I2C interfaces? (y/n) " enable_hardware

if [[ "$enable_hardware" =~ ^[Yy]$ ]]; then
    CONFIG_FILE="/boot/config.txt"

    # Enable I2C
    if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
        echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_FILE"
    else
        echo "I2C already enabled in $CONFIG_FILE"
    fi

    # Enable SPI
    if ! grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
        echo "dtparam=spi=on" | sudo tee -a "$CONFIG_FILE"
    else
        echo "SPI already enabled in $CONFIG_FILE"
    fi

    # Enable modules
    MODULES_FILE="/etc/modules"

    for module in i2c-dev spi-dev; do
        if ! grep -q "^$module" "$MODULES_FILE"; then
            echo "$module" | sudo tee -a "$MODULES_FILE"
        else
            echo "Module $module already present in $MODULES_FILE"
        fi
    done
fi

echo ""
echo "🔄 IMPORTANT: Test persistence by rebooting!"
read -p "Reboot now to test interface persistence? (y/n) " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
    sleep 5
    sudo reboot
fi