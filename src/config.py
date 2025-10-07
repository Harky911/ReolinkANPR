"""Configuration management for ReolinkANPR."""

import yaml
from pathlib import Path
from typing import Dict, Any

class Config:
    """Load and manage configuration from YAML file."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
        # Don't validate - allow web config to set everything

    def _create_default_config(self):
        """Create default configuration file."""
        default_config = {
            'camera': {
                'name': 'Front Door',
                'host': '192.168.1.100',
                'username': 'admin',
                'password': 'CHANGE_ME',
                'channel': 0,
                'recording_duration': 6
            },
            'alpr': {
                'detection_model': 'yolo-v9-t-640-license-plate-end2end',
                'ocr_model': 'cct-s-v1-global-model',
                'min_confidence': 0.9
            },
            'system': {
                'log_level': 'INFO',
                'log_file': 'logs/anpr.log',
                'database_path': 'data/anpr.db',
                'web_host': '0.0.0.0',
                'web_port': 5001
            }
        }

        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        print(f"✓ Created default config at {self.config_path}")
        print(f"✓ Please configure at http://localhost:5001/config")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file, create default if missing."""
        if not self.config_path.exists():
            print(f"Config file not found, creating default...")
            self._create_default_config()

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, *keys):
        """Get configuration value by nested keys."""
        value = self._config
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value

    # Camera settings
    @property
    def camera_host(self) -> str:
        return self.get('camera', 'host')

    @property
    def camera_username(self) -> str:
        return self.get('camera', 'username')

    @property
    def camera_password(self) -> str:
        return self.get('camera', 'password')

    @property
    def camera_channel(self) -> int:
        return self.get('camera', 'channel')

    @property
    def camera_name(self) -> str:
        return self.get('camera', 'name')

    # Recording settings (from camera section)
    @property
    def recording_duration(self) -> int:
        return self.get('camera', 'recording_duration') or 6

    # ALPR settings
    @property
    def detector_model(self) -> str:
        return self.get('alpr', 'detection_model') or 'yolo-v9-t-640-license-plate-end2end'

    @property
    def ocr_model(self) -> str:
        return self.get('alpr', 'ocr_model') or 'cct-s-v1-global-model'

    @property
    def min_confidence(self) -> float:
        return self.get('alpr', 'min_confidence') or 0.9

    # System settings
    @property
    def database_path(self) -> str:
        return self.get('system', 'database_path') or 'data/anpr.db'

    @property
    def web_host(self) -> str:
        return self.get('system', 'web_host') or '0.0.0.0'

    @property
    def web_port(self) -> int:
        return self.get('system', 'web_port') or 5001

    @property
    def log_level(self) -> str:
        return self.get('system', 'log_level') or 'INFO'

    @property
    def log_file(self) -> str:
        return self.get('system', 'log_file') or 'logs/anpr.log'

    # Recording settings (optional)
    @property
    def before_recording_enabled(self) -> bool:
        return self.get('recording', 'before_recording_enabled') or False

    @property
    def before_recording_settings(self) -> dict:
        return self.get('recording', 'before_recording_settings') or {}

    @property
    def after_recording_enabled(self) -> bool:
        return self.get('recording', 'after_recording_enabled') or False

    @property
    def after_recording_settings(self) -> dict:
        return self.get('recording', 'after_recording_settings') or {}

    def ensure_directories(self):
        """Create required directories if they don't exist."""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
