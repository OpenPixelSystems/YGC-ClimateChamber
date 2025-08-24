# Raspberry Pi Kiosk Mode Setup Guide

This guide configures your Raspberry Pi to automatically boot into kiosk mode, launching Chromium in fullscreen displaying your climatechamber web application at `http://127.0.0.1:5000`.

## Prerequisites

Ensure you have:
- Raspberry Pi with Raspberry Pi OS (with desktop)
- Screen, keyboard, and mouse connected
- Your climatechamber service already configured and running
- Internet connection for initial setup

## Step 1: Install Required Packages

Update your system and install necessary packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y chromium-browser unclutter xdotool
```

**Package explanations:**
- `chromium-browser`: The web browser for kiosk mode
- `unclutter`: Hides mouse cursor when inactive
- `xdotool`: Allows programmatic control of X11 (useful for scripting)

## Step 2: Enable Auto-Login

Configure the Pi to automatically login to the desktop:

```bash
sudo raspi-config
```

Navigate to:
1. **System Options** → **Boot / Auto Login** → **Desktop Autologin**
2. Select "Desktop Autologin" (automatically login to desktop as 'pi' user)
3. Finish and reboot when prompted

Or configure manually:
```bash
sudo systemctl set-default graphical.target
sudo systemctl enable getty@tty1.service
```

## Step 3: Create Kiosk Script

Create a script that will launch Chromium in kiosk mode:

```bash
mkdir -p /home/pi/kiosk
nano /home/pi/kiosk/start_kiosk.sh
```

Add the following content:

```bash
#!/bin/bash

# Wait for network and web server to be ready
sleep 30

# Remove any existing Chromium crash flags
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' ~/.config/chromium/Default/Preferences
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' ~/.config/chromium/Default/Preferences

# Kill any existing Chromium processes
killall chromium-browser 2>/dev/null

# Wait a moment
sleep 5

# Hide mouse cursor
unclutter -idle 0.5 -root &

# Disable screen blanking
xset s noblank
xset s off
xset -dpms

# Wait for the climatechamber service to be ready
echo "Waiting for climatechamber service..."
while ! curl -s http://127.0.0.1:5000 > /dev/null; do
    echo "Waiting for web server..."
    sleep 5
done

echo "Web server is ready, starting Chromium..."

# Start Chromium in kiosk mode
chromium-browser \
    --noerrdialogs \
    --disable-infobars \
    --disable-features=TranslateUI \
    --disable-suggestions-service \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --disable-field-trial-config \
    --disable-ipc-flooding-protection \
    --kiosk \
    --incognito \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-default-apps \
    --disable-popup-blocking \
    --disable-translate \
    --no-default-browser-check \
    --no-pings \
    --media-cache-size=1 \
    --disk-cache-size=1 \
    --aggressive-cache-discard \
    http://127.0.0.1:5000
```

Make the script executable:
```bash
chmod +x /home/pi/kiosk/start_kiosk.sh
```

## Step 4: Configure Autostart

Create autostart entry for the desktop session:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/kiosk.desktop
```

Add the following content:

```ini
[Desktop Entry]
Type=Application
Name=Kiosk Mode
Comment=Start Chromium in Kiosk Mode
Exec=/home/pi/kiosk/start_kiosk.sh
Icon=chromium-browser
Terminal=false
Categories=Network;WebBrowser;
StartupNotify=false
```

## Step 5: Disable Screen Saver and Power Management

Edit the LXDE autostart file:

```bash
nano ~/.config/lxsession/LXDE-pi/autostart
```

Replace the contents with:

```bash
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash

# Disable screen blanking
@xset s noblank
@xset s off  
@xset -dpms

# Hide mouse cursor when inactive
@unclutter -idle 0.5 -root

# Start kiosk mode
@/home/pi/kiosk/start_kiosk.sh
```

## Step 6: Configure Boot Settings

Edit the boot config to optimize for kiosk mode:

```bash
sudo nano /boot/config.txt
```

Add or modify these settings:

```ini
# Disable rainbow splash screen
disable_splash=1

# Set GPU memory split
gpu_mem=128

# Disable overscan (removes black borders)
disable_overscan=1

# Force HDMI output (uncomment if needed)
# hdmi_force_hotplug=1
# hdmi_drive=2
```

## Step 7: Optional - Create Recovery Mode

Create a way to exit kiosk mode if needed:

```bash
nano /home/pi/kiosk/exit_kiosk.sh
```

Add:

```bash
#!/bin/bash
killall chromium-browser
killall unclutter
```

Make executable:
```bash
chmod +x /home/pi/kiosk/exit_kiosk.sh
```

**To exit kiosk mode:** Press `Ctrl+Alt+T` to open terminal, then run:
```bash
/home/pi/kiosk/exit_kiosk.sh
```

## Step 8: Test the Setup

1. **Reboot to test everything:**
   ```bash
   sudo reboot
   ```

2. **What should happen:**
   - Pi boots to desktop automatically
   - After ~30 seconds, Chromium opens in fullscreen
   - Your climatechamber web interface loads at `http://127.0.0.1:5000`
   - Mouse cursor disappears when inactive
   - Screen doesn't go to sleep

## Troubleshooting

### Web Application Not Loading

**Check if climatechamber service is running:**
```bash
sudo systemctl status climatechamber.service
```

**Test web server manually:**
```bash
curl http://127.0.0.1:5000
```

### Chromium Won't Start

**Check the kiosk script logs:**
```bash
tail -f ~/.xsession-errors
```

**Test script manually:**
```bash
/home/pi/kiosk/start_kiosk.sh
```

### Screen Goes Black

**Disable additional power management:**
```bash
sudo nano /etc/lightdm/lightdm.conf
```

Find `[Seat:*]` section and add:
```ini
xserver-command=X -s 0 -dpms
```

### Recovery Options

**SSH Access:** Always ensure SSH is enabled for remote troubleshooting:
```bash
sudo systemctl enable ssh
```

**Safe Mode:** Hold `Shift` during boot to access recovery options.

**Emergency Exit:** Connect via SSH and run:
```bash
killall chromium-browser
sudo systemctl stop climatechamber.service
```

## Advanced Customizations

### Custom Splash Screen
Replace the default splash with your logo:
```bash
sudo cp your_logo.png /usr/share/plymouth/themes/pix/splash.png
```

### Automatic Updates
Add to crontab for daily updates:
```bash
crontab -e
```

Add:
```bash
0 2 * * * /usr/bin/chromium-browser --headless --dump-dom http://127.0.0.1:5000 > /dev/null 2>&1
```

### Touch Screen Support
If using a touch screen, add these Chromium flags to the kiosk script:
```bash
--touch-events=enabled \
--enable-pinch \
```

### Custom Resolution
Force specific resolution in `/boot/config.txt`:
```ini
hdmi_group=2
hdmi_mode=82  # 1920x1080 60Hz
```

## Final Checklist

- [ ] Climatechamber service starts automatically
- [ ] Pi auto-logs into desktop
- [ ] Kiosk script launches Chromium fullscreen
- [ ] Web application loads at `http://127.0.0.1:5000`
- [ ] Screen doesn't go to sleep
- [ ] Mouse cursor hides when inactive
- [ ] SSH access available for troubleshooting

Your Raspberry Pi should now automatically boot into a kiosk displaying your climatechamber web interface!