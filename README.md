# 🖨️ Discord Printer Bot

A full-featured Discord bot for controlling 3D printers via **Moonraker/Klipper**, **OctoPrint**, or **OctoEverywhere**.

Based on the [telegram-printer-bot](https://github.com/tetrdd/telegram-printer-bot) but rebuilt for Discord with enhanced features.

## 🏗️ Architecture

### Centralized Printer Configuration (SQLite)

As of v2.0, printer configurations are stored in a **SQLite database** instead of `config.yaml`. This provides:

- **Per-user printer management** - Each user can register and manage their own printers
- **Dynamic configuration** - Add/remove printers without restarting the bot
- **Fine-grained permissions** - Public/private printers with allowed users
- **User preferences** - Timezone, language, notification channels

The database is stored at `data/printers.db` and is created automatically on first run.

---

## 📋 Database Schema

### Tables

#### `users`
Stores user preferences and settings.

| Column | Type | Description |
|--------|------|-------------|
| `discord_id` | INTEGER | Primary key, Discord user ID |
| `timezone` | TEXT | User's timezone (e.g., "Europe/Berlin") |
| `language` | TEXT | Language preference (e.g., "en", "de") |
| `notify_channel` | TEXT | Discord channel ID for notifications |

#### `printers`
Stores printer configurations.

| Column | Type | Description |
|--------|------|-------------|
| `printer_id` | INTEGER | Primary key, auto-increment |
| `owner_discord_id` | INTEGER | Owner's Discord ID |
| `name` | TEXT | Printer display name |
| `type` | TEXT | Connection type: "moonraker", "octoprint", or "octoeverywhere" |
| `url` | TEXT | Printer URL (Moonraker/OctoPrint) or empty for OctoEverywhere |
| `api_key` | TEXT | API key (optional) |
| `privacy` | TEXT | "public" or "private" |
| `creation_timestamp` | DATETIME | When the printer was registered |

#### `printer_allowed_users`
Many-to-many relationship for printer access control.

| Column | Type | Description |
|--------|------|-------------|
| `printer_id` | INTEGER | Reference to printers table |
| `user_discord_id` | INTEGER | Discord user ID with access |

---

## 🔄 Migration Guide (v1.x → v2.0)

If you're upgrading from v1.x (config.yaml-based), follow these steps to migrate your printer configurations to the new SQLite database.

### Step 1: Backup Your Config

```bash
cp config.yaml config.yaml.backup
```

### Step 2: Run Migration Script

A migration script is provided to import your existing printers:

```bash
python migrate_from_yaml.py
```

This script will:
1. Read your existing `config.yaml`
2. Create user entries for all printer owners
3. Import all printers into the database
4. Preserve privacy settings and allowed users

### Step 3: Verify Migration

Use the bot commands to verify your printers were imported:

```
/list-printers
/printer-settings <id>
```

### Step 4: Update Your Config

After migration, remove the `printers:` section from `config.yaml`. Keep only:
- Discord token
- Temperature presets
- Macro configuration
- File browser settings
- Monitoring settings

Example minimal `config.yaml` after migration:

```yaml
discord:
  bot_token: "YOUR_DISCORD_BOT_TOKEN_HERE"

temp_presets:
  hotend:
    PLA: 200
    PETG: 230
  bed:
    PLA: 60
    PETG: 80

macros:
  aliases:
    LOAD_FILAMENT: "🔄 Load Filament"
```

### Manual Migration (if needed)

If the migration script fails, you can manually register printers using Discord commands:

1. Start the bot with the new version
2. Use `/register-printer` to add each printer
3. Use `/add-user` to grant access to other users

---

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

### 🆕 Printer Configuration (v2.0)
- `/register-printer` - Register a new printer (opens interactive modal)
- `/my-settings` - View or update your personal settings (timezone, language, notifications)
- `/printer-settings <id>` - View or update printer settings (owner only)
- `/list-printers` - List all printers you can access
- `/add-user <printer> <user>` - Add a user to your printer's allowed list
- `/remove-user <printer> <user>` - Remove a user from your printer's allowed list

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

### Printer Management (Legacy)
- `/printers` - List accessible printers
- `/switch-printer <id>` - Switch to a different printer
- `/printer-info <id>` - Get printer details

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

## 📦 LXC Setup

This section outlines how to set up the discord-printer-bot within an LXC container, focusing on Proxmox environments.

### Prerequisites and Host Context

*   **Host System:** Proxmox Virtual Environment (or any system supporting LXC).
*   **LXC Container:** A Debian or Ubuntu-based container. Ensure it has sufficient resources (CPU, RAM, disk space) for the bot and any associated processes.
*   **Nesting:** If you plan to run Docker within the LXC container for other services, you'll need to enable nested virtualization for the container. This is typically done in the Proxmox GUI under the container's Hardware settings.
*   **Network Setup:** Ensure the container has a working network connection. Bridged networking is common in Proxmox, allowing the container to appear as a separate device on your network.

### Creating and Configuring the LXC Container

1.  **Create Container:**
    *   In Proxmox, create a new LXC container.
    *   Choose a Debian or Ubuntu minimal image (e.g., Debian 12 "Bookworm" or Ubuntu 22.04 "Jammy Jellyfish").
    *   Configure network settings (e.g., using `vmbr0` for bridged networking).
    *   Enable **unprivileged** container usage unless root access within the container is absolutely necessary and security implications are understood.

2.  **Enable Nesting (if required):**
    *   For unprivileged containers, add `lxc.include: /etc/default/lxc-usermodmap` to the container's configuration (`/etc/pve/lxc/<CTID>.conf`).
    *   Inside the container, you may need to configure `sysctl` parameters for KVM/nesting if not already set by default. Often, this involves enabling `kvmhidden=1`.

3.  **Inside the Container:**
    *   Update package lists:
        ```bash
        sudo apt update && sudo apt upgrade -y
        ```
    *   Install Python 3.11-3.13, pip, and git. (If your base image doesn't have these, you might need to compile Python from source or use tools like `pyenv`):
        ```bash
        # Example for installing Python 3.11 on Debian/Ubuntu (may vary)
        sudo apt install -y python3.11 python3-pip python3.11-venv git
        # Ensure python3 points to your desired version, or use python3.11 explicitly
        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        sudo update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
        ```
    *   Create a virtual environment:
        ```bash
        python3 -m venv discord-printer-bot-venv
        source discord-printer-bot-venv/bin/activate
        ```
    *   Install dependencies:
        ```bash
        pip install -r requirements.txt
        ```

### Running the Bot

1.  **Activate Virtual Environment:**
    ```bash
    source /path/to/your/discord-printer-bot-venv/bin/activate
    ```
2.  **Run Bot:**
    ```bash
    python bot.py
    ```

3.  **Background Execution Options:**
    *   **nohup:** For simple backgrounding:
        ```bash
        nohup python bot.py &
        ```
    *   **Systemd Service:** For robust management (recommended):
        Create a service file (e.g., `/etc/systemd/system/discord-printer.service`) with content similar to this:
        ```ini
        [Unit]
        Description=Discord Printer Bot
        After=network.target

        [Service]
        User=your_user     # Replace with the user running the bot
        Group=your_group   # Replace with the group running the bot
        WorkingDirectory=/path/to/your/discord-printer-bot
        ExecStart=/path/to/your/discord-printer-bot-venv/bin/python /path/to/your/discord-printer-bot/bot.py
        Restart=on-failure
        Environment="PATH=/path/to/your/discord-printer-bot-venv/bin:/usr/bin" # Ensure venv Python is used

        [Install]
        WantedBy=multi-user.target
        ```
        Then enable and start the service:
        ```bash
        sudo systemctl enable discord-printer.service
        sudo systemctl start discord-printer.service
        ```

### Security and Permissions Notes

*   **Unprivileged Containers:** By default, LXC containers run as unprivileged users on the host. This is a significant security advantage, preventing container escapes from gaining root access to your Proxmox host.
*   **No Privileged Escalation:** Avoid running the bot or its dependencies with `sudo` inside the container unless absolutely necessary and the risks are understood. The bot should operate with the permissions of the user it's run under.
*   **Restricted Access:** LXC provides a good level of isolation. Ensure that only necessary ports are exposed and that the container's filesystem access is appropriately restricted. Limit direct host mounts to minimal, essential directories.
*   **Dependency Security:** Regularly update Python packages and system packages within the container to patch known vulnerabilities. Run `pip list --outdated` and `sudo apt list --upgradable` periodically.

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