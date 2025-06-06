#!/bin/bash

# Validation script for AP setup

AP_INTERFACE="uap0"
INTERNET_INTERFACE="wlan0"
AP_IP="192.168.50.1"
DHCP_RANGE_START="192.168.50.10"
DHCP_RANGE_END="192.168.50.50"
AP_SSID="PiRepeater"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

echo -e "${BLUE}=== AP Setup Validation Script ===${NC}"
echo

# Function to print success
print_success() {
    echo -e "✅ ${GREEN}$1${NC}"
}

# Function to print error
print_error() {
    echo -e "❌ ${RED}$1${NC}"
    OVERALL_STATUS=1
}

# Function to print warning
print_warning() {
    echo -e "⚠️  ${YELLOW}$1${NC}"
}

# Function to print info
print_info() {
    echo -e "ℹ️  ${BLUE}$1${NC}"
}

# Function to check if an interface exists and is up
check_interface() {
    local interface=$1
    if ip link show "$interface" &> /dev/null; then
        if ip link show "$interface" | grep -q "state UP"; then
            print_success "Interface $interface exists and is UP"
            return 0
        else
            print_error "Interface $interface exists but is DOWN"
            return 1
        fi
    else
        print_error "Interface $interface does not exist"
        return 1
    fi
}

# Function to check if a service is active
check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        print_success "Service $service is running"
        return 0
    else
        print_error "Service $service is not running"
        echo "   Status: $(systemctl is-active $service 2>/dev/null || echo 'unknown')"
        return 1
    fi
}

# Function to check service enabled status
check_service_enabled() {
    local service=$1
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then
        print_success "Service $service is enabled for startup"
        return 0
    else
        print_warning "Service $service is not enabled for startup"
        return 1
    fi
}

# Function to check IP configuration
check_ip_configuration() {
    if ip addr show "$AP_INTERFACE" 2>/dev/null | grep -q "$AP_IP/24"; then
        print_success "AP interface $AP_INTERFACE has correct IP address $AP_IP/24"
        return 0
    else
        print_error "AP interface $AP_INTERFACE does not have correct IP address $AP_IP/24"
        print_info "Current IP configuration:"
        ip addr show "$AP_INTERFACE" 2>/dev/null | grep "inet " || echo "   No IP address assigned"
        return 1
    fi
}

# Function to check IP forwarding
check_ip_forwarding() {
    local forwarding_status=$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)
    if [[ "$forwarding_status" == "1" ]]; then
        print_success "IP forwarding is enabled"
        return 0
    else
        print_error "IP forwarding is disabled"
        return 1
    fi
}

# Function to check NAT rules
check_nat_rules() {
    if iptables -t nat -L POSTROUTING -n 2>/dev/null | grep -q "MASQUERADE.*$INTERNET_INTERFACE"; then
        print_success "NAT MASQUERADE rule is correctly set up for $INTERNET_INTERFACE"
    else
        print_error "NAT MASQUERADE rule is missing for $INTERNET_INTERFACE"
        OVERALL_STATUS=1
    fi

    if iptables -L FORWARD -n 2>/dev/null | grep -q "ACCEPT.*$AP_INTERFACE.*$INTERNET_INTERFACE"; then
        print_success "Forward rule from $AP_INTERFACE to $INTERNET_INTERFACE exists"
    else
        print_error "Forward rule from $AP_INTERFACE to $INTERNET_INTERFACE is missing"
        OVERALL_STATUS=1
    fi

    if iptables -L FORWARD -n 2>/dev/null | grep -q "ACCEPT.*$INTERNET_INTERFACE.*$AP_INTERFACE"; then
        print_success "Forward rule from $INTERNET_INTERFACE to $AP_INTERFACE exists"
    else
        print_error "Forward rule from $INTERNET_INTERFACE to $AP_INTERFACE is missing"
        OVERALL_STATUS=1
    fi
}

# Function to check internet connectivity from Pi
check_internet_connectivity() {
    print_info "Testing internet connectivity from Pi..."
    if timeout 10 ping -c 3 8.8.8.8 &> /dev/null; then
        print_success "Pi has internet connectivity via $INTERNET_INTERFACE"
        return 0
    else
        print_error "Pi does not have internet connectivity"
        return 1
    fi
}

# Function to check hostapd configuration
check_hostapd_config() {
    local config_file="/etc/hostapd/hostapd.conf"
    if [[ -f "$config_file" ]]; then
        print_success "hostapd configuration file exists"

        # Check key configuration parameters
        if grep -q "^interface=$AP_INTERFACE" "$config_file"; then
            print_success "hostapd configured for interface $AP_INTERFACE"
        else
            print_error "hostapd not configured for interface $AP_INTERFACE"
        fi

        if grep -q "^ssid=$AP_SSID" "$config_file"; then
            print_success "hostapd SSID configured as $AP_SSID"
        else
            print_warning "hostapd SSID might not be configured correctly"
        fi

        if grep -q "^wpa=2" "$config_file"; then
            print_success "WPA2 security enabled"
        else
            print_warning "WPA2 security might not be enabled"
        fi
    else
        print_error "hostapd configuration file not found at $config_file"
        return 1
    fi
}

# Function to check dnsmasq configuration
check_dnsmasq_config() {
    local config_file="/etc/dnsmasq.conf"
    if [[ -f "$config_file" ]]; then
        print_success "dnsmasq configuration file exists"

        if grep -q "^interface=$AP_INTERFACE" "$config_file"; then
            print_success "dnsmasq configured for interface $AP_INTERFACE"
        else
            print_error "dnsmasq not configured for interface $AP_INTERFACE"
        fi

        if grep -q "^dhcp-range=" "$config_file"; then
            local dhcp_range=$(grep "^dhcp-range=" "$config_file" | head -1)
            print_success "DHCP range configured: $dhcp_range"
        else
            print_error "DHCP range not configured in dnsmasq"
        fi
    else
        print_error "dnsmasq configuration file not found at $config_file"
        return 1
    fi
}

# Function to check wireless interface capabilities
check_wireless_capabilities() {
    print_info "Checking wireless interface capabilities..."

    # Check if interface supports AP mode
    if iw phy phy0 info 2>/dev/null | grep -A 20 "Supported interface modes" | grep -q "AP"; then
        print_success "Wireless interface supports AP mode"
    else
        print_error "Wireless interface does not support AP mode"
    fi

    # Show current interface status
    print_info "Current wireless interfaces:"
    iw dev 2>/dev/null | grep -E "(Interface|type|channel)" | sed 's/^/   /'
}

# Function to check DHCP leases
check_dhcp_leases() {
    local lease_file="/var/lib/dhcp/dhcpcd.leases"
    local dnsmasq_lease_file="/var/lib/misc/dnsmasq.leases"

    if [[ -f "$dnsmasq_lease_file" ]] && [[ -s "$dnsmasq_lease_file" ]]; then
        local lease_count=$(wc -l < "$dnsmasq_lease_file")
        print_success "DHCP leases found: $lease_count active lease(s)"
        print_info "Current DHCP leases:"
        cat "$dnsmasq_lease_file" | while read line; do
            echo "   $line"
        done
        return 0
    else
        print_warning "No DHCP leases found (this is normal if no devices are connected)"
        return 0
    fi
}

# Function to check AP visibility
check_ap_visibility() {
    print_info "Checking if AP is broadcasting..."
    if command -v iwlist >/dev/null 2>&1; then
        if timeout 10 iwlist scan 2>/dev/null | grep -q "ESSID:\"$AP_SSID\""; then
            print_success "AP $AP_SSID is visible in wireless scan"
            return 0
        else
            print_warning "AP $AP_SSID not found in wireless scan (might be normal)"
            return 1
        fi
    else
        print_warning "iwlist not available, cannot check AP visibility"
        return 1
    fi
}

# Function to show network routing
check_routing() {
    print_info "Network routing table:"
    ip route show | grep -E "(default|192\.168\.50)" | sed 's/^/   /' || echo "   No relevant routes found"
}

# Main validation logic
echo -e "${BLUE}=== Interface Status ===${NC}"
check_interface "$INTERNET_INTERFACE"
check_interface "$AP_INTERFACE"

echo
echo -e "${BLUE}=== Service Status ===${NC}"
check_service "hostapd"
check_service "dnsmasq"
check_service "setup-$AP_INTERFACE"
check_service_enabled "hostapd"
check_service_enabled "dnsmasq"
check_service_enabled "setup-$AP_INTERFACE"

echo
echo -e "${BLUE}=== Network Configuration ===${NC}"
check_ip_configuration
check_ip_forwarding
check_routing

echo
echo -e "${BLUE}=== Firewall/NAT Rules ===${NC}"
check_nat_rules

echo
echo -e "${BLUE}=== Service Configuration ===${NC}"
check_hostapd_config
check_dnsmasq_config

echo
echo -e "${BLUE}=== Connectivity Tests ===${NC}"
check_internet_connectivity
check_wireless_capabilities
check_ap_visibility

echo
echo -e "${BLUE}=== DHCP Status ===${NC}"
check_dhcp_leases

echo
echo -e "${BLUE}=== Validation Summary ===${NC}"
if [[ $OVERALL_STATUS -eq 0 ]]; then
    print_success "All critical configurations are correct! AP should be working."
    echo
    print_info "To connect to your AP:"
    echo "   SSID: $AP_SSID"
    echo "   Password: [as configured]"
    echo "   AP IP: $AP_IP"
    echo "   DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
else
    print_error "Some configurations need attention. Check the errors above."
    echo
    print_info "Common fixes:"
    echo "   • Restart services: sudo systemctl restart hostapd dnsmasq"
    echo "   • Check logs: sudo journalctl -u hostapd -u dnsmasq --since '5 minutes ago'"
    echo "   • Verify configuration files in /etc/hostapd/ and /etc/dnsmasq.conf"
fi

echo