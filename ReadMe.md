# Climate Chamber FLASK Interface
## Raspberry pi setup
1) Flash Raspberry Pi memory card with Raspberry Pi OS image.
2) Log into raspberry pi using SSH
3) Install git on Raspberry Pi ``sudo apt install git``
4) Clone project onto Pi ``git clone https://gitlab.com/tmc-climatechamber/climatechamber.git``
5) Setup virtual environment ``./setup_env.sh`` (May require ``sudo chmod +x setup_env.sh`` first)
6) Setup AP mode if used in internetless mode ``./setup_ap.sh`` and enter WiFi key
7) Setup WiFi connection if need be ``./setup_wifi.sh`` 

### Setup_ap.sh file
The Setup_ap.sh file's purpose is to setup the raspberry pi in Access Point mode. 
This means that the raspberry pi will broadcast a SSID in the wifi environment allowing users to connect to it.
This connection allows users to browse to the FLASK webpage or SSH into the device.

### Setup_env.sh file
The Setup_env.sh file is used to set up a Python virtual environment on a Raspberry Pi. 
This script creates an isolated environment for Python projects, which helps manage dependencies and avoid conflicts between different project requirements. 
It starts by creating a virtual environment in a specified directory, activates it, and then installs the necessary Python packages listed in a requirements.txt file. 
This setup ensures that all dependencies for a project are installed in an isolated environment, making it easier to manage and replicate the project setup across different systems. 
The script outputs instructions on how to activate the virtual environment for future use.

### Setup_wifi.sh file
The Setup_wifi.sh file is designed to configure and manage WiFi connections on a Raspberry Pi. 
It automates the process of scanning for available WiFi networks, allows the user to select a network, and facilitates the connection to the chosen network. 
The script ensures that the WiFi interface is active, checks for available networks, and handles the connection process, including the input of necessary credentials. 
Additionally, it verifies the internet connection by pinging a host and checks DNS resolution to ensure full connectivity. 
Once connected, it makes the connection persistent across reboots by updating the necessary configuration files and enabling the appropriate services.