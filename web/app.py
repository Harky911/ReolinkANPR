"""Web dashboard for ReolinkANPR."""

import sys
import asyncio
import yaml
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, flash
import threading
import nest_asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.database import Database
from src.camera_client import CameraClient

# Allow nested event loops (required for Flask + asyncio)
nest_asyncio.apply()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simplified-anpr-2025'

# Load configuration
config = Config("config.yaml")
db = Database(config.database_path)

# Initialize database
asyncio.run(db.initialize())

# Paths - use absolute path to data directory
DATA_DIR = (Path(__file__).parent.parent / config.database_path).parent.resolve()

# Camera client for settings control - initialized on first use
camera_client = None
camera_client_lock = threading.Lock()

# Create a background event loop for camera operations
async_loop = None
async_thread = None


def setup_async_loop():
    """Setup a background event loop for async operations."""
    global async_loop, async_thread
    
    if async_loop is None:
        def run_loop():
            global async_loop
            async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(async_loop)
            async_loop.run_forever()
        
        async_thread = threading.Thread(target=run_loop, daemon=True)
        async_thread.start()
        
        # Wait for loop to be ready
        import time
        while async_loop is None:
            time.sleep(0.01)


def run_async(coro):
    """Helper to run async functions from sync context."""
    global async_loop
    
    if async_loop is None:
        setup_async_loop()
    
    future = asyncio.run_coroutine_threadsafe(coro, async_loop)
    return future.result(timeout=10)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html', active_page='dashboard')


@app.route('/api/events')
def api_events():
    """Get events with pagination and filtering."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', '', type=str)
    filter_type = request.args.get('filter', 'all', type=str)

    # Calculate offset
    offset = (page - 1) * limit

    # Get paginated events
    events, total = run_async(
        db.get_paginated_events(limit, offset, search, filter_type)
    )

    # Calculate pagination
    total_pages = (total + limit - 1) // limit

    return jsonify({
        'events': events,
        'page': page,
        'pages': total_pages,
        'total': total,
        'per_page': limit
    })


@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve detection images."""
    image_path = DATA_DIR / filename

    if image_path.exists():
        return send_file(image_path)
    else:
        return "", 404


@app.route('/config')
def config_page():
    """Configuration page."""
    return render_template('config.html', config=config, active_page='config')


@app.route('/docs')
def docs_page():
    """Documentation page."""
    return render_template('documentation.html', active_page='docs')


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration."""
    config_file = Path(__file__).parent.parent / "config.yaml"

    if request.method == 'GET':
        # Read current config
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        return jsonify(config_data)

    elif request.method == 'POST':
        # Update config
        try:
            new_config = request.json

            # Write to file
            with open(config_file, 'w') as f:
                yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)

            return jsonify({'success': True, 'message': 'Configuration saved. Restart service for changes to take effect.'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/notifications/test', methods=['POST'])
def api_test_notifications():
    """Test notification settings."""
    async def send_test():
        try:
            # Load current config
            from src.notifier import Notifier
            test_config = Config("config.yaml")
            notifier = Notifier(test_config)
            
            # Get requested service from request
            data = request.json or {}
            service = data.get('service', 'all')
            
            # Send test
            result = await notifier.send_test(service)
            
            if result:
                return {'success': True, 'message': 'Test notification sent! Check your Telegram/Home Assistant.'}
            else:
                return {'success': False, 'message': 'No notification services enabled'}
                
        except Exception as e:
            return {'success': False, 'message': f'Failed to send test: {str(e)}'}
    
    result = asyncio.run(send_test())
    return jsonify(result)


@app.route('/api/camera/rtsp/status', methods=['GET'])
def api_rtsp_status():
    """Get RTSP status."""
    global camera_client
    
    async def get_status():
        global camera_client
        
        # Initialize camera client if needed
        if camera_client is None:
            camera_client = CameraClient(config)
            await camera_client.connect()
        
        try:
            body = [{"cmd": "GetNetPort", "action": 0, "param": {"channel": 0}}]
            response = await camera_client.host.send(body)
            
            if response and len(response) > 0:
                net_port = response[0].get("value", {}).get("NetPort", {})
                rtsp_enabled = net_port.get("rtspEnable", 0)
                rtsp_port = net_port.get("rtspPort", 554)
                
                return {
                    'success': True,
                    'enabled': rtsp_enabled == 1,
                    'port': rtsp_port
                }
            
            return {'success': False, 'message': 'No response from camera'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    with camera_client_lock:
        result = run_async(get_status())
    return jsonify(result)


@app.route('/api/camera/rtsp/toggle', methods=['POST'])
def api_rtsp_toggle():
    """Toggle RTSP on/off."""
    global camera_client
    
    async def toggle_rtsp():
        global camera_client
        
        # Initialize camera client if needed
        if camera_client is None:
            camera_client = CameraClient(config)
            await camera_client.connect()
        
        try:
            data = request.json
            enable = data.get('enable', True)
            
            body = [{
                "cmd": "SetNetPort",
                "action": 0,
                "param": {
                    "NetPort": {
                        "rtspEnable": 1 if enable else 0,
                        "rtspPort": 554
                    }
                }
            }]
            
            response = await camera_client.host.send(body)
            
            if response and response[0].get("code") == 0:
                status = "enabled" if enable else "disabled"
                return {
                    'success': True,
                    'message': f'RTSP {status} successfully'
                }
            
            return {'success': False, 'message': 'Failed to change RTSP settings'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    with camera_client_lock:
        result = run_async(toggle_rtsp())
    return jsonify(result)


@app.route('/api/camera/settings', methods=['GET'])
def get_camera_settings():
    """Get current camera ISP settings."""
    global camera_client

    try:
        with camera_client_lock:
            # Create camera client if needed
            if camera_client is None:
                camera_client = CameraClient(config)
                run_async(camera_client.connect())

            settings = run_async(camera_client.get_isp_settings())

        if settings:
            return jsonify({'success': True, 'settings': settings})
        else:
            return jsonify({'success': False, 'message': 'Failed to get camera settings'}), 500

    except Exception as e:
        print(f"Error in get_camera_settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/settings', methods=['POST'])
def set_camera_settings():
    """Set camera ISP settings."""
    global camera_client

    try:
        settings = request.json
        print(f"Received settings to apply: {settings}")

        with camera_client_lock:
            # Create camera client if needed
            if camera_client is None:
                camera_client = CameraClient(config)
                run_async(camera_client.connect())

            success = run_async(camera_client.set_isp_settings(settings))

        if success:
            return jsonify({'success': True, 'message': 'Camera settings applied'})
        else:
            return jsonify({'success': False, 'message': 'Failed to apply settings'}), 500

    except Exception as e:
        print(f"Error in set_camera_settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("ReolinkANPR Web Dashboard")
    print("=" * 60)
    print(f"Dashboard: http://localhost:{config.web_port}")
    print("=" * 60)

    app.run(
        host=config.web_host,
        port=config.web_port,
        debug=False
    )
