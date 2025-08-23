# GitLab SSH Setup and Project Installation Guide

This guide walks you through setting up SSH authentication for GitLab, cloning a repository, and setting up a Python virtual environment.

## Step 1: Generate SSH Key

Generate a new SSH key pair (replace with your actual GitLab email):

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

**Options during key generation:**
- Press `Enter` to accept the default file location (`/home/username/.ssh/id_ed25519`)
- Optionally set a passphrase for extra security (or press `Enter` for no passphrase)

## Step 2: Start SSH Agent and Add Key

```bash
# Start the SSH agent
eval "$(ssh-agent -s)"

# Add your private key to the SSH agent
ssh-add ~/.ssh/id_ed25519
```

## Step 3: Copy Public Key to GitLab

Display your public key:
```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (starts with `ssh-ed25519` and ends with your email).

**Add to GitLab:**
1. Go to GitLab → User Settings → SSH Keys (or visit: https://gitlab.com/-/profile/keys)
2. Paste your public key in the "Key" field
3. Give it a descriptive title (e.g., "Raspberry Pi", "Development Machine")
4. Set an expiration date (optional but recommended)
5. Click "Add key"

## Step 4: Test SSH Connection

Verify your SSH connection to GitLab:
```bash
ssh -T git@gitlab.com
```

You should see a message like:
```
Welcome to GitLab, @yourusername!
```

## Step 5: Clone Repository

Clone your repository using SSH (replace with your actual repository URL):
```bash
git clone git@gitlab.com:username/repository-name.git
```

**Example:**
```bash
git clone git@gitlab.com:mycompany/climatechamber.git
```

## Step 6: Navigate to Project and Setup Environment

Change to the climatechamber directory:
```bash
cd climatechamber
```

Create a Python virtual environment:
```bash
python3 -m venv venv
```

Activate the virtual environment:
```bash
source venv/bin/activate
```

**Note:** You'll see `(venv)` prefix in your terminal prompt when the environment is active.

## Step 7: Install Dependencies

Install the required packages:
```bash
pip install -r requirements.txt
```

## Quick Reference Commands

```bash
# Activate virtual environment (run from climatechamber directory)
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Check installed packages
pip list

# Update a package
pip install --upgrade package_name

# Add new package and update requirements
pip install new_package
pip freeze > requirements.txt
```

## Troubleshooting

### SSH Connection Issues
- **Permission denied**: Make sure your public key is correctly added to GitLab
- **Host key verification failed**: Run `ssh-keyscan gitlab.com >> ~/.ssh/known_hosts`
- **Key not loaded**: Re-run `ssh-add ~/.ssh/id_ed25519`

### Virtual Environment Issues
- **Command not found**: Make sure Python 3 is installed: `sudo apt install python3-venv`
- **Permission denied**: Don't use `sudo` with pip in virtual environments

### Dependencies Installation Issues
- **Package not found**: Update pip first: `pip install --upgrade pip`
- **Compilation errors**: Install development tools: `sudo apt install build-essential python3-dev`

## Security Best Practices

1. **Never share your private key** (`id_ed25519` file without `.pub` extension)
2. **Use a passphrase** for your SSH key for additional security
3. **Regularly rotate SSH keys** (set expiration dates in GitLab)
4. **Keep your virtual environment isolated** - don't install packages globally unless necessary

---

**Next Steps:** Once everything is set up, you can start working on your project. Remember to activate your virtual environment (`source venv/bin/activate`) each time you work on the project.