
import json
import os
from services.logger import Logger

class ConfigManager:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        self.logger = Logger()
        self.config = self.load_config()

    def default_config(self):
        return {
            "agents": {
                "Quant": {"provider": "Gemini", "model": "gemini-3-flash-preview"},
                "Vision": {"provider": "Gemini", "model": "gemini-3-flash-preview"},
                "Fundamental": {"provider": "Gemini", "model": "gemini-3-flash-preview"},
                "Risk": {"provider": "Gemini", "model": "gemini-3-flash-preview"},
                "Sentiment": {"provider": "Gemini", "model": "gemini-3-flash-preview"},
                "Master": {"provider": "Gemini", "model": "gemini-3-flash-preview"}
            },
            "risk": {
                "account_balance": 10000.0,
                "risk_percent": 1.0
            }
        }

    def load_config(self):
        """Loads configuration from JSON file, or returns defaults."""
        default_config = self.default_config()
        
        if not os.path.exists(self.filepath):
            return default_config
            
        try:
            with open(self.filepath, 'r') as f:
                saved_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_config = default_config.copy()
                
                # Recursively merge dictionaries
                def deep_merge(source, destination):
                    for key, value in source.items():
                        if isinstance(value, dict) and key in destination and isinstance(destination[key], dict):
                            destination[key] = deep_merge(value, destination[key])
                        else:
                            destination[key] = value
                    return destination

                merged_config = deep_merge(saved_config, merged_config)
                return merged_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config

    def save_config(self, new_config):
        """Saves configuration to JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(new_config, f, indent=4)
            self.config = new_config
            self.logger.info("Configuration saved successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            return False

    def get_agent_config(self, agent_name):
        agents = self.config.get("agents", {})
        agent_conf = agents.get(agent_name, {})
        return agent_conf.get("provider", "Gemini"), agent_conf.get("model", "")
        
    def get_risk_config(self):
        risk = self.config.get("risk", {})
        return float(risk.get("account_balance", 10000.0)), float(risk.get("risk_percent", 1.0))
