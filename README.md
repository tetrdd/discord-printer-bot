# 🖨️ Discord Printer Bot

A full-featured Discord bot for controlling 3D printers via **OctoEverywhere**.

Built for a public-first experience where users can register their own printers and manage them entirely through Discord.

## 🏗️ Architecture

### Centralized Printer Configuration (SQLite)

Printer configurations are stored in a **SQLite database**. This provides:

- **Per-user printer management** - Each user can register and manage their own printers
- **Dynamic configuration** - Add/remove printers without restarting the bot
- **Fine-grained permissions** - Public/private printers with allowed users
- **User preferences** - Timezone, language, notification channels, and **custom temperature presets**

The database is stored at `data/printers.db` and is created automatically on first run.

---

## ✨ Features

### 🎮 Printer Control
- **Status monitoring** - Real-time print progress, temperatures, ETA
- **Print controls** - Pause, resume, cancel, home, motors off
- **Emergency stop** - With confirmation for safety
- **Temperature control** - Hotend and bed with **per-user custom presets**
- **File browser** - Browse, print, and delete G-code files
- **Macros** - Run Klipper macros with custom aliases
- **Live adjustments** - Speed, flow, fan, and Z-offset during prints
- **Camera** - Snapshots and stream links
- **Print history** - View completed prints
- **Bed mesh** - Visualize bed mesh data

### 🔐 Permission System
- **Printer ownership** - Each printer has an owner
- **Privacy settings** -
  - **Private**: Only owner and allowed users can see and control.
  - **Public**: Anyone can see the status, but only owner and allowed users can control.
- **Access control** - Allow specific users to access private printers
- **Multiple printers** - Support for unlimited printers per user with easy switching (`/switch-printer`)

### 🌐 Remote Access
- **OctoEverywhere support** - Primary method for remote access. Control your printer from anywhere.

---

## 📋 Commands

### 🆕 Printer Configuration
- `/register-printer` - Register a new OctoEverywhere printer
- `/my-settings` - View or update your personal settings and active printer
- `/printer-settings <id>` - View or update printer settings (owner only)
- `/list-printers` - List all printers you can access
- `/switch-printer <id>` - Switch your active printer
- `/add-user <printer> <user>` - Add a user to your printer's allowed list
- `/remove-user <printer> <user>` - Remove a user from your printer's allowed list

### Core Commands
- `/status` - Get current printer status
- `/menu` - Show main menu
- `/control` - Print control menu (pause/resume/cancel)
- `/temperatures` - Temperature control
- `/presets-manager` - Manage your personal material presets
- `/files` - Browse G-code files
- `/camera` - Take camera snapshot
- `/stream` - Get camera stream link

---

## 🚀 Quick Start

### 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application", go to "Bot" tab, and copy the bot token.
3. Enable `MESSAGE CONTENT INTENT` under the Bot tab.
4. Under "OAuth2" → "URL Generator", select `bot` and `applications.commands`.
5. Invite the bot to your server.

### 2. Configure the Bot
Set the `DISCORD_TOKEN` environment variable:
```bash
export DISCORD_TOKEN="YOUR_BOT_TOKEN"
```
Or create a `config.yaml`:
```yaml
discord:
  bot_token: "YOUR_DISCORD_BOT_TOKEN_HERE"
```

### 3. Install Dependencies
```bash
# Requires Python 3.13+
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the Bot
```bash
python bot.py
```

---

## 📦 LXC Setup (Debian 13 / Proxmox)

Since you are typically `root` by default in an LXC container, `sudo` is not required.

### 1. Update and Install Dependencies
```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git
```

### 2. Setup the Bot
```bash
git clone https://github.com/your-repo/discord-printer-bot.git /opt/printer-bot
cd /opt/printer-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run as a Service
Create a service file: `/etc/systemd/system/discord-printer.service`
```ini
[Unit]
Description=Discord Printer Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/printer-bot
ExecStart=/opt/printer-bot/venv/bin/python bot.py
Restart=always
Environment="DISCORD_TOKEN=your_token_here"

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable --now discord-printer
```

---

## 🛡️ Security

- **OctoEverywhere only** - Optimized for secure remote access.
- **Permission system** - Granular access control per printer.
- **Private by default** - Your printer is yours unless you choose to share it.

## 🤝 Contributing

MIT - Do whatever you want with it.

---

**Built with ❤️ for the 3D printing community**
