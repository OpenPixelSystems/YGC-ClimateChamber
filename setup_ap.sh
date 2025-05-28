#!/bin/bash

# Raspberry Pi Access Point Setup Script
# WARNING: This will disconnect the Pi from your current WiFi network!
# Make sure you have physical access to the Pi or another way to connect

echo "=== Raspberry Pi Access Point Setup ==="
echo "WARNING: This will disconnect from current WiFi network!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt install -y hostapd dnsmasq

# Stop services during configuration
echo "Stopping services for configuration..."
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq

# Backup original configuration files
echo "Backing up configuration files..."
sudo cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup

# Configure static IP for wlan0
echo "Configuring static IP..."
cat << EOF | sudo tee -a /etc/dhcpcd.conf

# Static IP configuration for Access Point
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF

# Configure dnsmasq (DHCP server)
echo "Configuring DHCP server..."
cat << EOF | sudo tee -a /etc/dnsmasq.conf

# Access Point DHCP Configuration
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

# Configure hostapd (WiFi Access Point)
echo "Configuring WiFi Access Point..."
cat << EOF | sudo tee /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=ClimateControl-AP
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=ClimateControl2024
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Tell system where to find hostapd config
echo "Configuring hostapd daemon..."
sudo sed -i 's/#DAEMON_CONF=""/DAEMON_CONF="\/etc\/hostapd\/hostapd.conf"/' /etc/default/hostapd

# Enable services
echo "Enabling services..."
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq

# Create a script to restore original WiFi configuration
echo "Creating restoration script..."
cat << 'EOF' | sudo tee /home/pi/restore_wifi.sh
#!/bin/bash
echo "Restoring original WiFi configuration..."
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
sudo systemctl disable hostapd
sudo systemctl disable dnsmasq
sudo cp /etc/dhcpcd.conf.backup /etc/dhcpcd.conf
sudo cp /etc/dnsmasq.conf.backup /etc/dnsmasq.conf
sudo systemctl restart dhcpcd
echo "WiFi client mode restored. Reboot recommended."
EOF

sudo chmod +x /home/pi/restore_wifi.sh

echo ""
echo "=== Configuration Complete ==="
echo "Access Point Details:"
echo "  SSID: ClimateControl-AP"
echo "  Password: ClimateControl2024"
echo "  Pi IP Address: 192.168.4.1"
echo ""
echo "Your Flask app should listen on 0.0.0.0:80 or 0.0.0.0:5000"
echo "Users will access it at: http://192.168.4.1 (or :5000 if using port 5000)"
echo ""
echo "To restore WiFi client mode later, run: /home/pi/restore_wifi.sh"
echo ""
echo "READY TO REBOOT AND ENABLE ACCESS POINT MODE?"
echo "Press Ctrl+C to cancel, or Enter to reboot now..."
read

# Create a failsafe service that will revert to WiFi if AP fails
echo "Creating failsafe service..."
cat << 'EOF' | sudo tee /etc/systemd/system/ap-failsafe.service
[Unit]
Description=Access Point Failsafe Service
After=network.target

[Service]
Type=oneshot
ExecStart=/home/pi/ap-failsafe.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Create the failsafe script
cat << 'EOF' | sudo tee /home/pi/ap-failsafe.sh
#!/bin/bash

# Wait for system to fully boot
sleep 30

# Check if hostapd is running and if any clients are connected
AP_RUNNING=$(systemctl is-active hostapd)
CLIENTS_CONNECTED=$(iw dev wlan0 station dump | grep Station | wc -l)

# If AP mode has been running for 5 minutes without any connections, revert to WiFi
if [ "$AP_RUNNING" = "active" ]; then
    sleep 300  # Wait 5 minutes
    CLIENTS_CONNECTED=$(iw dev wlan0 station dump | grep Station | wc -l)

    if [ $CLIENTS_CONNECTED -eq 0 ]; then
        echo "$(date): No clients connected to AP for 5 minutes, reverting to WiFi mode" >> /home/pi/ap-failsafe.log
        /home/pi/restore_wifi.sh
        sleep 10
        sudo reboot
    fi
fi
EOF

sudo chmod +x /home/pi/ap-failsafe.sh

# Create manual revert script that can be triggered by button press
cat << 'EOF' | sudo tee /home/pi/manual_revert.sh
#!/bin/bash
# This script can be triggered by a GPIO button or other method
echo "$(date): Manual revert triggered" >> /home/pi/ap-failsafe.log
/home/pi/restore_wifi.sh
sleep 5
sudo reboot
EOF

sudo chmod +x /home/pi/manual_revert.sh

# Enable the failsafe service
sudo systemctl enable ap-failsafe.service

echo ""
echo "=== Failsafe Features Added ==="
echo "1. Automatic revert: If no devices connect to AP within 5 minutes"
echo "2. Manual revert script: /home/pi/manual_revert.sh"
echo "3. Logs saved to: /home/pi/ap-failsafe.log"
echo ""
echo "Additional failsafe options:"
echo "- Connect GPIO pin 18 to ground to trigger manual revert"
echo "- Or run: sudo /home/pi/manual_revert.sh"
echo ""

sudo reboot