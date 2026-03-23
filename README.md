# 🖨️ Discord Printer Bot

A full-featured Discord bot for controlling 3D printers via **Moonraker/Klipper**, **OctoPrint**, or **OctoEverywhere**.

Based on the [telegram-printer-bot](https://github.com/tetrdd/telegram-printer-bot) but rebuilt for Discord with enhanced features.

## ✨ Features

### 🎮 Printer Control
- **Status monitoring** - Real-time print progress, temperatures, ETA
- **Print controls** - Pause, resume, cancel, home, motors off
- **Emergency stop** - With confirmation for safety
- **Temperature control** - Hotend and bed with presets (PLA, PETG, ABS, etc.)
- **File browser** - Browse, print, and delete G-code files
- **Macros** - Run Klipper macros with custom aliases
- **Live adjustments** - Speed, flow, fan, and Z-offset during prints
- **Camera** - Snapshots and stream links
- **Print history** - View completed prints (Moonraker only)
- **Bed mesh** - Visualize bed mesh data (Moonraker only)

### 🔐 Permission System
- **Printer ownership** - Each printer has an owner
- **Privacy settings** - Public or private printers
- **Access control** - Allow specific users to access private printers
- **Multiple printers** - Support for unlimited printers per user
- **Role-based access** - Optional Discord role restrictions

### 🌐 Remote Access
- **OctoEverywhere support** - Control printers remotely via cloud
- **Moonraker** - Local or remote Klipper setups
- **OctoPrint** - Local or remote OctoPrint instances

## 📋 Commands

### Core Commands
- `/status` - Get current printer status
- `/menu` - Show main menu
- `/control` - Print control menu (pause/resume/cancel)
- `/temperatures` - Temperature control
- `/files` - Browse G-code files
- `/camera` - Take camera snapshot
- `/stream` - Get camera stream link

### Advanced Commands
- `/macros` - List available macros
- `/run-macro <name>` - Run a specific macro
- `/adjust` - Print adjustments menu
- `/speed <percentage>` - Set speed override (50-150%)
- `/flow <percentage>` - Set flow override (75-125%)
- `/fan <percentage>` - Set fan speed (0-100%)
- `/z-offset <adjustment>` - Adjust Z-offset
- `/history` - View print history
- `/bed-mesh` - View bed mesh profile

### Printer Management
- `/printers` - List accessible printers
- `/switch-printer <id>` - Switch to a different printer
- `/printer-info <id>` - Get printer details
- `/set-privacy <id> <private>` - Set printer privacy (owner only)
- `/add-user <printer> <user>` - Add user to allowed list (owner only)
- `/remove-user <printer> <user>` - Remove user from allowed list (owner only)
- `/rename-printer <id> <name>` - Rename printer (owner only)

## 🚀 Quick Start

### 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" tab and click "Add Bot"
4. Copy the bot token
5. Under "OAuth2" → "URL Generator", select `bot` and `applications.commands`
6. Copy the generated URL and open it to invite the bot to your server

### 2. Configure the Bot
```bash
# Clone or download this repo
cd discord-printer-bot

# Copy config example
cp config.yaml.example config.yaml

# Edit config.yaml with your values
# - Discord bot token
# - Printer connection details
# - Owner IDs and permissions
```

### 3. Install Dependencies
```bash
# Requires Python 3.10+
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the Bot
```bash
python bot.py
```

### 5. Use the Bot
In Discord, use `/status` to see your printer status!

## 📖 Configuration

### Printer Connection Types

#### Moonraker/Klipper (Local)
```yaml
printers:
  - name: "Voron"
    moonraker:
      url: "http://192.168.1.100:7125"
      api_key: ""  # Optional if not configured in Moonraker
```

#### OctoPrint (Local)
```yaml
printers:
  - name: "Ender 3"
    octoprint:
      url: "http://192.168.1.101:5000"
      api_key: "YOUR_API_KEY"  # Get from OctoPrint Settings → API
```

#### OctoEverywhere (Remote)
```yaml
printers:
  - name: "Remote Printer"
    octoeverywhere:
      key: "YOUR_OCTOEVERYWHERE_KEY"  # From octoeverywhere.com
```

### Permission System

Each printer can have:
- **owner_id**: Discord user ID of the owner (full control)
- **is_private**: If true, only owner + allowed_users can access
- **allowed_users**: List of Discord user IDs with access

Example:
```yaml
printers:
  - name: "Private Printer"
    moonraker:
      url: "http://192.168.1.100:7125"
    owner_id: 123456789012345678  # Your Discord ID
    is_private: true
    allowed_users:
      - 987654321098765432  # Friend's Discord ID
```

To find your Discord ID:
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click your name and select "Copy ID"

### Camera Configuration
```yaml
camera:
  snapshot_url: "http://192.168.1.100/webcam/?action=snapshot"
  stream_url: "http://192.168.1.100/webcam/?action=stream"
```

Common camera URLs:
- **Moonraker/MjpegStreamer**: `http://IP/webcam/?action=snapshot`
- **OctoPrint**: `http://IP:5000/plugin/mjpegstreamer-adaptive/?action=snapshot`
- **Fluidd/Crowsnest**: `http://IP/webcam/?action=snapshot`

## 🔧 Running as a Service

### Linux (systemd)
```bash
# Create service file
sudo nano /etc/systemd/system/discord-printer-bot.service
```

```ini
[Unit]
Description=Discord Printer Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/discord-printer-bot
ExecStart=/opt/discord-printer-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now discord-printer-bot
sudo systemctl status discord-printer-bot
```

## 🛡️ Security

- **No exposed ports** - Bot only makes outbound connections
- **API key protection** - Keys stored in config.yaml (don't commit to git!)
- **Permission system** - Granular access control per printer
- **Confirmation dialogs** - For destructive actions (cancel, E-stop, delete)

## 📝 Notes

- **Print history** and **bed mesh** are only available on Moonraker/Klipper
- **Macros** are only available on Moonraker/Klipper
- **OctoEverywhere** requires a free/paid account at [octoeverywhere.com](https://octoeverywhere.com)
- Bot requires `message_content` intent for future features

## 🤝 Contributing

This bot was created for Ed's 3D printing setup. Feel free to fork and adapt!

## 📄 License

MIT - Do whatever you want with it.

---

**Built with ❤️ for the 3D printing community**
