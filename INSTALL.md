# ReolinkANPR Installation Guide

Complete guide to set up ReolinkANPR for your Reolink camera.

## Prerequisites

- **Python 3.11 or higher** (required for TCP push event support)
- **Reolink camera** (with RTSP support)
- **Network access** to your camera
- **Linux, macOS, or Windows** (Linux/macOS recommended for best performance)

## Step 1: Install Dependencies

### On Linux (Ubuntu/Debian)

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv git

# Install system libraries for OpenCV and FFmpeg
sudo apt install -y libgl1-mesa-glx libglib2.0-0 ffmpeg
```

### On macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and FFmpeg
brew install python3 ffmpeg
```

### On Windows

1. Download and install Python from [python.org](https://www.python.org/downloads/)
2. Make sure to check "Add Python to PATH" during installation
3. Download and install FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
4. Add FFmpeg to your system PATH

## Step 2: Download ReolinkANPR

```bash
# Clone or download the repository
git clone https://github.com/yourusername/ReolinkANPR.git
cd ReolinkANPR

# Or if you downloaded a ZIP, extract it and navigate to the folder
```

## Step 3: Set Up Python Environment

**Important:** If your default `python3` is version 3.10 or lower, use `python3.11` or `python3.12` instead:

```bash
# Check your Python version first
python3 --version

# If it shows Python 3.10 or lower, use python3.11 or python3.12 instead:
# python3.11 -m venv venv
# or
# python3.12 -m venv venv

# Create virtual environment (with Python 3.11+)
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** FastALPR installation may take a few minutes as it downloads AI models.

## Step 4: Configure Your Camera

### 4.1 Enable RTSP on Reolink Camera

1. Open the Reolink app or web interface
2. Go to **Settings** → **Network** → **Advanced**
3. Enable **RTSP**
4. Note the **RTSP port** (usually 554)

### 4.2 Enable AI Vehicle Detection

1. Go to **Settings** → **AI**
2. Enable **Vehicle Detection**
3. Adjust detection sensitivity as needed
4. Save settings

### 4.3 Get Camera IP Address

1. Go to **Settings** → **Network** → **Network Status**
2. Note the **IP Address** (e.g., 192.168.1.100)
3. Consider setting a **static IP** for reliability

## Step 5: Start ReolinkANPR

On first run, ReolinkANPR automatically creates a default `config.yaml` file:

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Start the system (creates default config on first run)
python3 run.py
```

You should see:
```
============================================================
ReolinkANPR is running!

  Web Dashboard: http://localhost:5001

Press Ctrl+C to stop
============================================================
```

## Step 6: Configure Your Camera via Web Interface

Open your web browser and navigate to **http://localhost:5001/config**

**Configure your settings:**

1. **Camera Settings**
   - Host: Your camera's IP address (e.g., 192.168.1.100)
   - Username: Camera username (usually "admin")
   - Password: Camera password (**IMPORTANT: Change from default!**)
   - Channel: 0 for direct camera, or NVR channel number (0, 1, 2...)
   - Camera Name: Friendly name for identification

2. **ALPR Settings**
   - Detection Model: YOLO v9 Tiny 640 (recommended)
   - OCR Model: CCT-S v1 Global (recommended)
   - Min Confidence: 0.90 (90% confidence threshold)

3. **Recording Duration**
   - Recording Duration: 6 seconds (adjust based on vehicle speed)

4. **Click "Save Configuration"**

5. **Restart ReolinkANPR** (Ctrl+C in terminal, then `python3 run.py` again)

**Note:** No manual YAML file editing required! Everything is configured through the web interface.

## Step 7: Access the Dashboard

Open your web browser and navigate to:

**http://localhost:5001**

You should see the ReolinkANPR dashboard with statistics and events.

## Troubleshooting

### Cannot connect to camera

- Verify camera IP address is correct
- Check camera is powered on and connected to network
- Ensure RTSP is enabled in camera settings
- Try pinging the camera: `ping 192.168.1.100`
- Check username and password are correct

### FastALPR not found

```bash
# Reinstall FastALPR
pip uninstall fast-alpr
pip install fast-alpr
```

### No detections appearing

- Ensure Vehicle AI detection is enabled on camera
- Check camera has a clear view of vehicles
- Try lowering `min_confidence` via web config (http://localhost:5001/config)
- Check logs in `logs/anpr.log`

### Dashboard not loading

- Check port 5001 is not in use
- Check firewall settings
- Ensure ReolinkANPR is running (check terminal output)

## Running as a Service (Linux)

To run ReolinkANPR automatically on startup:

1. Create service file:

```bash
sudo nano /etc/systemd/system/simplified-anpr.service
```

2. Add the following (replace paths):

```ini
[Unit]
Description=ReolinkANPR Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/ReolinkANPR
ExecStart=/path/to/ReolinkANPR/venv/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable simplified-anpr
sudo systemctl start simplified-anpr

# Check status
sudo systemctl status simplified-anpr
```

## Next Steps

- Monitor the dashboard for detections
- Adjust camera position for best plate visibility
- Fine-tune `min_confidence` and other settings via web config
- Review logs for any issues

## Support

For issues or questions, please check:
- `logs/anpr.log` for detailed logs
- Camera settings and network connectivity
- Python version compatibility (3.11+ required for TCP push events)

Enjoy ReolinkANPR!
