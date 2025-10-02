# Climate Chamber User Guide

This guide explains how to connect to and access the Climate Chamber control system on a Raspberry Pi.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Connection Methods](#connection-methods)
3. [Method 1: Direct Connection with Screen](#method-1-direct-connection-with-screen)
4. [Method 2: Network Connection via Ethernet](#method-2-network-connection-via-ethernet)
5. [SSH Access](#ssh-access)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Climate Chamber Raspberry Pi with software pre-installed and configured
- System runs in **kiosk mode** - the Climate Chamber application starts automatically on boot
- Default credentials:
  - **Username**: `raspberry`
  - **Password**: `pi`

---

## Connection Methods

There are two ways to connect to the Raspberry Pi Climate Chamber:

- **Method 1**: Direct connection with a screen and mouse
- **Method 2**: Network connection via Ethernet cable (remote access)

---

## Method 1: Direct Connection with Screen

This method allows you to view the Climate Chamber interface directly on a connected monitor. The application will automatically start in kiosk mode.

### Required Hardware
- Raspberry Pi with Climate Chamber software installed
- USB-C power cable
- Micro HDMI cable
- Monitor with HDMI input
- USB mouse (or wireless USB dongle for wireless mouse)

### Setup Steps

1. **Connect Power**
   - Connect the USB-C power cable to the Raspberry Pi

2. **Connect Display**
   - Connect the Micro HDMI cable from the Raspberry Pi to your monitor
   - Ensure the monitor is powered on and set to the correct HDMI input

3. **Connect Mouse**
   - Plug in a USB mouse or wireless mouse dongle to the Raspberry Pi USB port

4. **Verify Connection**
   - The monitor should automatically display the Climate Chamber web application in full-screen kiosk mode
   - The application starts automatically when the Raspberry Pi boots

---

## Method 2: Network Connection via Ethernet

This method allows you to control the Climate Chamber remotely from your computer. The Raspberry Pi acts as a DHCP server and assigns your computer an IP address in the `192.168.137.0/24` range.

### Required Hardware
- Raspberry Pi with Climate Chamber software installed
- USB-C power cable
- Ethernet cable
- Computer with Ethernet port
- VNC Viewer software (e.g., UltraVNC, RealVNC) - for desktop access

### Setup Steps

1. **Connect Power**
   - Connect the USB-C power cable to the Raspberry Pi

2. **Connect Ethernet Cable**
   - Connect one end of the Ethernet cable to the Raspberry Pi
   - Connect the other end to your computer's Ethernet port
   - The Raspberry Pi will automatically assign an IP address to your computer

3. **Test Network Connection**
   - Open Command Prompt (Windows) or Terminal (Mac/Linux) on your computer
   - Type the following command and press Enter:
     ```bash
     ping 192.168.137.1
     ```
   - You should see successful ping responses (e.g., "Reply from 192.168.137.1...")
   - If ping fails, check cable connections and ensure the Raspberry Pi has fully booted (wait 2-3 minutes)

4. **Connect via VNC (for Desktop Access)**
   - VNC allows you to remotely access the Raspberry Pi desktop environment
   - Since the system runs in kiosk mode, the Climate Chamber application will be visible automatically
   - Open your VNC Viewer application (e.g., UltraVNC, RealVNC)
   - Enter the connection details:
     - **IP Address**: `192.168.137.1`
     - **Username**: `raspberry`
     - **Password**: `pi`
   - Click "Connect"
   - You should now see the Raspberry Pi desktop with the Climate Chamber app running in kiosk mode

5. **Connect via Web Browser (Alternative)**
   - Open a web browser on your computer
   - Navigate to: `http://192.168.137.1:5000`
   - The Climate Chamber web interface should appear

---

## SSH Access

SSH (Secure Shell) allows you to access the Raspberry Pi command line remotely for advanced troubleshooting and system management.

### Connecting via SSH

1. **Open Terminal/Command Prompt**
   - Windows: Open Command Prompt or PowerShell
   - Mac/Linux: Open Terminal

2. **SSH Login Command**
   ```bash
   ssh raspberry@192.168.137.1
   ```

3. **Enter Password**
   - When prompted, enter the password: `pi`

4. **Successful Connection**
   - You should now see the Raspberry Pi command prompt
   - Example: `raspberry@raspberrypi:~ $`

### Useful SSH Commands

**Restart Climate Chamber Service:**
```bash
sudo systemctl restart climatechamber.service
```

**Check Service Status:**
```bash
sudo systemctl status climatechamber.service
```

**View Application Logs:**
```bash
sudo journalctl -u climatechamber.service -f
```

**Exit SSH Session:**
```bash
exit
```

---

## WiFi Connectivity

**⚠️ Note**: WiFi configuration through the web interface does not work when running as a service due to permission errors.

**Recommended Solution**: Use Ethernet connection (as described in Method 2 above)

**Alternative**: Configure WiFi via SSH before using the application:
```bash
sudo raspi-config
# Select: System Options → Wireless LAN → Enter SSID and password
```

---

## Troubleshooting

### Problem: Application Not Responding or Behaving Incorrectly

**Solution 1: Restart via Web Interface**
1. Navigate to the Climate Chamber web interface
2. Go to "System Config" or "Logs" page
3. Click "Restart Service" or "Restart Application" button
4. Wait 30-60 seconds for the service to restart
5. Refresh your browser

**Solution 2: Restart via SSH**
1. Connect to Raspberry Pi via SSH (see [SSH Access](#ssh-access))
2. Run the restart command:
   ```bash
   sudo systemctl restart climatechamber.service
   ```
3. Wait for confirmation message
4. Refresh your web browser or VNC connection

**Solution 3: Hard Reset (Last Resort)**
1. Unplug the USB-C power cable from the Raspberry Pi
2. Wait 10 seconds
3. Plug the power cable back in
4. Wait 1-2 minutes for the system to boot up
5. Reconnect via your preferred method

### Problem: Cannot Connect via Network (192.168.137.1)

**Possible Solutions:**
- Check that the Ethernet cable is securely connected to both devices
- Verify that your computer's Ethernet adapter is enabled
- Check Windows/Mac network settings to ensure Ethernet is active
- Try a different Ethernet cable
- Restart the Raspberry Pi

### Problem: Cannot Ping 192.168.137.1

**Possible Solutions:**
- Ensure the Raspberry Pi has fully booted (wait 2-3 minutes after power-on)
- Check if your computer's firewall is blocking ping requests
- Verify Ethernet adapter settings (should be set to obtain IP automatically - the Raspberry Pi assigns IPs in the 192.168.137.0/24 range)
- Check that the Ethernet cable is functioning properly

### Problem: VNC Shows Black Screen or Won't Connect

**Possible Solutions:**
- Ensure VNC server is enabled on Raspberry Pi
- Try connecting via web browser instead: `http://192.168.137.1:5000`
- Check VNC credentials: username `raspberry`, password `pi`
- Restart the Raspberry Pi

### Problem: Application Features Not Working

For application-specific issues (Peltier control, temperature readings, graphs, etc.), see the INTERFACE_MANUAL.md file for detailed feature documentation and troubleshooting.

---

## Safety Warnings

⚠️ **Important Safety Information:**

- Never exceed safe temperature limits configured in the system
- Always monitor the chamber during operation
- Ensure adequate ventilation for Peltier heat dissipation
- Do not touch Peltier elements during operation (hot/cold surfaces)
- Stop operation immediately if you smell burning or see smoke
- Use the emergency stop feature if temperatures exceed safe limits

---

## Next Steps

Once connected, open a web browser and go to `http://192.168.137.1:5000` to access the Climate Chamber interface.

For complete instructions on using the application, see **INTERFACE_MANUAL.md**.

## Getting Help

If you encounter connection or system issues:

1. Check system logs via SSH: `sudo journalctl -u climatechamber.service -f`
2. Verify hardware connections and power supply
3. Contact system administrator or development team

---

## Quick Reference

### Connection Information
- **Raspberry Pi IP Address**: `192.168.137.1`
- **Web Interface**: `http://192.168.137.1:5000`
- **DHCP Range**: `192.168.137.0/24` (Pi assigns IP to connected devices)
- **Default Username**: `raspberry`
- **Default Password**: `pi`

### Quick Commands

**Test Network Connection:**
```bash
ping 192.168.137.1
```

**SSH Login:**
```bash
ssh raspberry@192.168.137.1
```

**Restart Climate Chamber Service:**
```bash
sudo systemctl restart climatechamber.service
```

**View Real-time Logs:**
```bash
sudo journalctl -u climatechamber.service -f
```

**Check Service Status:**
```bash
sudo systemctl status climatechamber.service
```

---

**Document Version**: 1.1
**Last Updated**: 2025-10-02
