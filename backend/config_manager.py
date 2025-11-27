# ADA-Pi Backend Module: config_manager.py
# Basic configuration manager placeholder with real structure

import json
import os

CONFIG_PATH = "/etc/ada_pi/config.json"

DEFAULT_CONFIG = {
    "network": {
        "wifi_country": "GB"
    },
    "ups": {
        "shutdown_enabled": True,
        "shutdown_threshold": 20
    },
    "tacho": {
        "enabled": False,
        "upload_interval": 5
    }
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)

def get(section, key, default=None):
    cfg = load_config()
    return cfg.get(section, {}).get(key, default)

def set(section, key, value):
    cfg = load_config()
    if section not in cfg:
        cfg[section] = {}
    cfg[section][key] = value
    save_config(cfg)
