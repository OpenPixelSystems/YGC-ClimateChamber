# SystemD Service Setup for Climate Chamber

This guide shows how to create a systemctl service that automatically starts your climatechamber project at boot using the virtual environment.

## Step 1: Create the Service File

Create a new systemd service file:

```bash
sudo nano /etc/systemd/system/climatechamber.service
```

Add the following configuration (adjust paths as needed):

```ini
[Unit]
Description=Climate Chamber Application
After=multi-user.target
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/home/raspberry/climatechamber
Environment=PATH=/home/raspberry/climatechamber/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/raspberry/climatechamber/debug_env.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Step 2: Adjust Paths (Important!)

**Update these paths in the service file to match your setup:**

- Replace `/home/raspberry/` with your actual home directory path
- If your project is in a different location, update `WorkingDirectory` and `ExecStart` paths
- Change `User=raspberry` and `Group=raspberry` to your actual username

**To find your paths:**
```bash
# Get current user
whoami

# Get full path to your project
cd climatechamber
pwd

# Verify virtual environment path
ls -la venv/bin/python
```

## Step 3: Enable and Start the Service

Reload systemd to recognize the new service:
```bash
sudo systemctl daemon-reload
```

Enable the service to start at boot:
```bash
sudo systemctl enable climatechamber.service
```

Start the service immediately:
```bash
sudo systemctl start climatechamber.service
```

## Step 4: Verify Service is Running

Check service status:
```bash
sudo systemctl status climatechamber.service
```

You should see output like:
```
● climatechamber.service - Climate Chamber Application
   Loaded: loaded (/etc/systemd/system/climatechamber.service; enabled; vendor preset: enabled)
   Active: active (running) since [timestamp]
   ...
```

## Service Management Commands

```bash
# Check service status
sudo systemctl status climatechamber.service

# Start the service
sudo systemctl start climatechamber.service

# Stop the service
sudo systemctl stop climatechamber.service

# Restart the service
sudo systemctl restart climatechamber.service

# Disable auto-start at boot
sudo systemctl disable climatechamber.service

# Enable auto-start at boot
sudo systemctl enable climatechamber.service

# View real-time logs
sudo journalctl -u climatechamber.service -f

# View recent logs
sudo journalctl -u climatechamber.service -n 50
```

## Step 5: View Logs

To see what your application is doing:

```bash
# View recent logs
sudo journalctl -u climatechamber.service

# Follow logs in real-time
sudo journalctl -u climatechamber.service -f

# View logs from today
sudo journalctl -u climatechamber.service --since today

# View logs with timestamps
sudo journalctl -u climatechamber.service -o short-iso
```

## Troubleshooting

### Service Won't Start
1. **Check file permissions:**
   ```bash
   ls -la /home/raspberry/climatechamber/run.py
   chmod +x /home/raspberry/climatechamber/run.py
   ```

2. **Verify virtual environment:**
   ```bash
   /home/raspberry/climatechamber/venv/bin/python --version
   ```

3. **Test manual execution:**
   ```bash
   cd /home/raspberry/climatechamber
   source venv/bin/activate
   python run.py
   ```

### Service Fails After Working Manually
- Check the `User` and `Group` settings in the service file
- Ensure all paths are absolute (not relative)
- Verify environment variables are set correctly

### Common Error Solutions

**Permission denied:**
```bash
# Fix ownership
sudo chown -R raspberry:raspberry /home/raspberry/climatechamber

# Make run.py executable
chmod +x /home/raspberry/climatechamber/run.py
```

**Module not found:**
- Ensure the virtual environment path is correct in `Environment=PATH=`
- Verify all dependencies are installed in the virtual environment

**Network-related issues:**
- The service waits for network connectivity (`After=network-online.target`)
- If your app needs internet access, this should resolve connection issues

## Advanced Configuration Options

### Environment Variables
If your application needs environment variables:

```ini
[Service]
Environment=PYTHONPATH=/home/raspberry/climatechamber
Environment=DEBUG=False
Environment=LOG_LEVEL=INFO
```

### Resource Limits
To limit CPU/memory usage:

```ini
[Service]
CPUQuota=50%
MemoryLimit=512M
```

### Custom Logging
To log to a specific file:

```ini
[Service]
StandardOutput=file:/var/log/climatechamber/output.log
StandardError=file:/var/log/climatechamber/error.log
```

Remember to create the log directory:
```bash
sudo mkdir -p /var/log/climatechamber
sudo chown raspberry:raspberry /var/log/climatechamber
```

## Testing the Auto-Start

To verify everything works on boot:

1. Reboot your system:
   ```bash
   sudo reboot
   ```

2. After reboot, check if the service started automatically:
   ```bash
   sudo systemctl status climatechamber.service
   ```

3. Check the logs to ensure no errors occurred:
   ```bash
   sudo journalctl -u climatechamber.service
   ```

Your climatechamber application should now automatically start every time the system boots!