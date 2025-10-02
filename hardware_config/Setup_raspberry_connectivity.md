# Comprehensive Pi Ethernet DHCP Sharing Setup

This setup turns your Raspberry Pi into a router that shares its WiFi internet connection through its Ethernet port using DHCP.

---

## Network Architecture
- **WiFi (wlan0):** Connected to your main router (`192.168.0.x` network)
- **Ethernet (eth0):** Acts as DHCP server (`192.168.137.x` network)
- **Internet sharing:** Traffic flows WiFi ↔ Ethernet via NAT/masquerading

---

## Complete Setup Steps

### 1. Install Required Packages
```bash
sudo apt update
sudo apt install dnsmasq iptables iptables-persistent
```

### 2. Configure NetworkManager Connection for Ethernet
```bash
# Create dedicated ethernet connection
sudo nmcli connection add type ethernet ifname eth0 con-name eth0-shared

# Set static IP for eth0
sudo nmcli connection modify eth0-shared ipv4.addresses 192.168.137.1/24
sudo nmcli connection modify eth0-shared ipv4.method manual
sudo nmcli connection modify eth0-shared connection.autoconnect yes

# Activate the connection
sudo nmcli connection up eth0-shared
```

### 3. Configure DHCP Server (dnsmasq)
```bash
# Create DHCP configuration for eth0
sudo nano /etc/dnsmasq.d/eth0-dhcp.conf
```

Add this content:
```
interface=eth0
dhcp-range=192.168.137.2,192.168.137.10,255.255.255.0,24h
dhcp-option=3,192.168.137.1    # Gateway
dhcp-option=6,8.8.8.8,8.8.4.4  # DNS servers
```

### 4. Enable IP Forwarding
```bash
# Enable IP forwarding permanently
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf

# Apply immediately
sudo sysctl -p
```

### 5. Configure NAT/Firewall Rules
```bash
# Set up NAT masquerading (internet sharing)
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE

# Allow forwarding between interfaces
sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT

# Save iptables rules permanently
sudo netfilter-persistent save
```

### 6. Enable and Start Services
```bash
# Enable services to start at boot
sudo systemctl enable dnsmasq
sudo systemctl enable netfilter-persistent

# Start services now
sudo systemctl start dnsmasq
```

---

## Verification Commands

### Check Network Configuration
```bash
# Verify eth0 has static IP
ip addr show eth0

# Check active NetworkManager connections
nmcli connection show --active

# Verify routing table
ip route show
```

### Check DHCP Service
```bash
# Verify dnsmasq is running
sudo systemctl status dnsmasq

# Check if DHCP port is listening
sudo netstat -ulnp | grep :67

# Monitor DHCP requests in real-time
sudo journalctl -u dnsmasq -f
```

### Check Firewall/NAT
```bash
# View current iptables rules
sudo iptables -L -v
sudo iptables -t nat -L -v

# Verify IP forwarding is enabled
cat /proc/sys/net/ipv4/ip_forward
```

---

## Configuration Files Summary

**/etc/dnsmasq.d/eth0-dhcp.conf**
```
interface=eth0
dhcp-range=192.168.137.2,192.168.137.10,255.255.255.0,24h
dhcp-option=3,192.168.137.1
dhcp-option=6,8.8.8.8,8.8.4.4
```

**/etc/sysctl.conf (addition)**
```
net.ipv4.ip_forward=1
```

**NetworkManager Connection**
- **Name:** eth0-shared
- **Interface:** eth0
- **IP:** 192.168.137.1/24
- **Method:** Manual (static)

---

## How It Works
1. Pi connects to WiFi via NetworkManager (gets internet from `192.168.0.x` network).
2. Ethernet gets static IP `192.168.137.1` via NetworkManager connection.
3. `dnsmasq` provides DHCP on eth0, assigns IPs `192.168.137.2-10` to connected devices.
4. `iptables` NAT translates traffic between wlan0 and eth0.
5. IP forwarding routes packets between the two networks.
6. Connected devices get internet through the Pi acting as a router.

---

## Client Connection (Desktop Side)
```bash
# Client automatically gets IP via DHCP
sudo dhclient enx00e04c6828a6

# Should receive IP in range 192.168.137.2-10
# Gateway: 192.168.137.1 (the Pi)
# DNS: 8.8.8.8, 8.8.4.4
```

---

✅ This setup is persistent across reboots and provides a complete ethernet-sharing solution using NetworkManager's native configuration methods.
