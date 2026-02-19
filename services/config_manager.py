
import json
import os
from services.logger import Logger

class ConfigManager:
    def __init__(self, config_file="user_config.json"):
        self.config_file = config_file
        self.logger = Logger()
        self.config = self.load_config()

    def load_config(self):
        """Loads configuration from JSON file, or returns defaults."""
        default_config = {
            "agents": {
                "Quant": {"provider": "Gemini", "model": "gemini-2.0-flash"},
                "Vision": {"provider": "OpenRouter", "model": "qwen/qwen3-vl-235b-a22b-thinking"},
                "Fundamental": {"provider": "Gemini", "model": "gemini-2.0-flash"},
                "Risk": {"provider": "Gemini", "model": "gemini-2.0-flash"},
                "Sentiment": {"provider": "Gemini", "model": "gemini-2.0-flash"},
                "Master": {"provider": "Gemini", "model": "gemini-2.0-flash"}
            }
        }
        
        if not os.path.exists(self.config_file):
            return default_config
            
        try:
            with open(self.config_file, 'r') as f:
                saved_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for agent, settings in default_config["agents"].items():
                    if agent not in saved_config.get("agents", {}):
                        if "agents" not in saved_config: saved_config["agents"] = {}
                        saved_config["agents"][agent] = settings
                return saved_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config

    def save_config(self, new_config):
        """Saves configuration to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(new_config, f, indent=4)
            self.config = new_config
            self.logger.info("Configuration saved successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            return False

    def get_agent_config(self, agent_name):
        """Returns (provider, model) tuple for a specific agent."""
        agent_settings = self.config.get("agents", {}).get(agent_name, {})
        return agent_settings.get("provider", "Gemini"), agent_settings.get("model", "gemini-2.0-flash")
