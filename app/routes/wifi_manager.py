"""
WiFi Network Management Routes
Handles scanning for available networks and connecting to selected networks
"""

import subprocess
import json
import re
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

wifi_bp = Blueprint("wifi", __name__)


def check_nmcli_available():
    """Check if nmcli is available on the system"""
    try:
        result = subprocess.run(
            ["which", "nmcli"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def scan_wifi_networks():
    """Scan for available WiFi networks using nmcli"""
    try:
        # Check if nmcli is available
        if not check_nmcli_available():
            return {
                "success": False,
                "error": "NetworkManager (nmcli) not available on this system",
            }

        # Use nmcli to scan for networks (run as raspberry user)
        result = subprocess.run(
            [
                "sudo",
                "-u",
                "raspberry",
                "nmcli",
                "-t",
                "-f",
                "SSID,SIGNAL,SECURITY",
                "dev",
                "wifi",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"success": False, "error": "Failed to scan networks"}

        networks = []
        seen_ssids = set()

        for line in result.stdout.strip().split("\n"):
            if not line or line.count(":") < 2:
                continue

            parts = line.split(":")
            ssid = parts[0].strip()
            signal = parts[1].strip()
            security = parts[2].strip()

            # Skip empty SSIDs and duplicates
            if not ssid or ssid in seen_ssids:
                continue

            seen_ssids.add(ssid)

            networks.append(
                {
                    "ssid": ssid,
                    "signal": int(signal) if signal.isdigit() else 0,
                    "security": security,
                    "secured": bool(security and security != "--"),
                }
            )

        # Sort by signal strength (highest first)
        networks.sort(key=lambda x: x["signal"], reverse=True)

        return {"success": True, "networks": networks}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Network scan timeout"}
    except FileNotFoundError:
        return {"success": False, "error": "NetworkManager (nmcli) command not found"}
    except Exception as e:
        return {"success": False, "error": f"Scan failed: {str(e)}"}


def connect_to_network(ssid, password=None):
    """Connect to a WiFi network using nmcli"""
    try:
        # Check if nmcli is available
        if not check_nmcli_available():
            return {
                "success": False,
                "error": "NetworkManager (nmcli) not available on this system",
            }

        # Validate inputs
        if not ssid or not isinstance(ssid, str):
            return {"success": False, "error": "Invalid network name provided"}

        if password is not None and not isinstance(password, str):
            return {"success": False, "error": "Invalid password provided"}

        # First, check if we're already connected to this network
        current_result = subprocess.run(
            [
                "sudo",
                "-u",
                "raspberry",
                "nmcli",
                "-t",
                "-f",
                "NAME",
                "connection",
                "show",
                "--active",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if current_result.returncode == 0:
            active_connections = current_result.stdout.strip().split("\n")
            if ssid in active_connections:
                return {"success": True, "message": f"Already connected to {ssid}"}

        # Try to connect to the network
        cmd = ["sudo", "-u", "raspberry", "nmcli", "dev", "wifi", "connect", ssid]
        if password and password.strip():
            cmd.extend(["password", password])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {"success": True, "message": f"Successfully connected to {ssid}"}
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return {"success": False, "error": f"Connection failed: {error_msg}"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Connection timeout"}
    except FileNotFoundError:
        return {"success": False, "error": "NetworkManager (nmcli) command not found"}
    except Exception as e:
        return {"success": False, "error": f"Connection failed: {str(e)}"}


def get_current_connection():
    """Get current WiFi connection info including IP addresses"""
    try:
        # Check if nmcli is available
        if not check_nmcli_available():
            return {
                "success": False,
                "error": "NetworkManager (nmcli) not available on this system",
            }

        # Get active connections
        result = subprocess.run(
            [
                "sudo",
                "-u",
                "raspberry",
                "nmcli",
                "-t",
                "-f",
                "NAME,TYPE,DEVICE",
                "connection",
                "show",
                "--active",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"success": False, "error": "Failed to get connection info"}

        current_wifi = None
        wifi_device = None
        ethernet_device = None

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                if parts[1] == "802-11-wireless":
                    current_wifi = parts[0]
                    wifi_device = parts[2]
                elif parts[1] == "802-3-ethernet":
                    ethernet_device = parts[2]

        # Get IP addresses for active interfaces
        wifi_ip = None
        ethernet_ip = None

        if wifi_device:
            try:
                ip_result = subprocess.run(
                    ["ip", "addr", "show", wifi_device],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if ip_result.returncode == 0:
                    # Extract IPv4 address
                    for line in ip_result.stdout.split("\n"):
                        if "inet " in line and "scope global" in line:
                            wifi_ip = line.strip().split()[1].split("/")[0]
                            break
            except Exception:
                pass

        if ethernet_device:
            try:
                ip_result = subprocess.run(
                    ["ip", "addr", "show", ethernet_device],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if ip_result.returncode == 0:
                    # Extract IPv4 address
                    for line in ip_result.stdout.split("\n"):
                        if "inet " in line and "scope global" in line:
                            ethernet_ip = line.strip().split()[1].split("/")[0]
                            break
            except Exception:
                pass

        return {
            "success": True,
            "current": current_wifi,
            "wifi_ip": wifi_ip,
            "ethernet_ip": ethernet_ip,
            "wifi_device": wifi_device,
            "ethernet_device": ethernet_device,
        }

    except FileNotFoundError:
        return {"success": False, "error": "NetworkManager (nmcli) command not found"}
    except Exception as e:
        return {"success": False, "error": f"Failed to get connection info: {str(e)}"}


@wifi_bp.route("/wifi-networks")
def wifi_networks():
    """Display WiFi networks page"""
    return render_template("wifi_networks.html")


@wifi_bp.route("/api/wifi/scan")
def api_scan_networks():
    """API endpoint to scan for WiFi networks"""
    return jsonify(scan_wifi_networks())


@wifi_bp.route("/api/wifi/current")
def api_current_connection():
    """API endpoint to get current WiFi connection"""
    return jsonify(get_current_connection())


@wifi_bp.route("/api/wifi/connect", methods=["POST"])
def api_connect_network():
    """API endpoint to connect to a WiFi network"""
    data = request.get_json()

    if not data or "ssid" not in data:
        return jsonify({"success": False, "error": "SSID is required"}), 400

    ssid = data["ssid"]
    password = data.get("password")

    result = connect_to_network(ssid, password)
    return jsonify(result)
