import json
from pathlib import Path
from typing import Any, Dict, Union
from app import app_state

def try_convert(value: str) -> Union[int, float, str]:
    """Convert string values to appropriate numeric types if possible"""
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

def deep_merge(original: Dict, new: Dict) -> Dict:
    """Deep merge two dictionaries"""
    for key, value in new.items():
        if isinstance(value, dict) and key in original:
            original[key] = deep_merge(original[key], value)
        else:
            original[key] = value
    return original

def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from a JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Error loading configuration: {str(e)}")

def save_config(config_path: Union[str, Path], new_config: Dict[str, Any]) -> None:
    """Save configuration to a JSON file with deep merge"""
    try:
        # Load existing config
        try:
            original_config = load_config(config_path)
        except RuntimeError:
            original_config = {}
            
        # Merge configurations
        merged_config = deep_merge(original_config, new_config)
        
        # Ensure directory exists
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save merged config
        with open(config_path, 'w') as f:
            json.dump(merged_config, f, indent=4)

    except Exception as e:
        raise RuntimeError(f"Error saving configuration: {str(e)}")

def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from the configuration"""
    try:
        return config[key]['value']
    except (KeyError, TypeError):
        return default