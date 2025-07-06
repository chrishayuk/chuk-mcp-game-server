# chuk_mcp_game_server/plugins/plugin_registry.py
"""
Plugin Registry
===============

Registry for managing game plugins with discovery and validation.
Provides centralized plugin management for the MCP game framework.
"""

import logging
from typing import Dict, List, Type, Any, Optional
from abc import ABC, abstractmethod

from ..core.models import GameStateBase, GameConfig, GameInfo

logger = logging.getLogger(__name__)


class GamePlugin(ABC):
    """Abstract base class for game plugins."""
    
    @abstractmethod
    def get_game_type(self) -> str:
        """Return the unique game type identifier."""
        pass
    
    @abstractmethod
    def get_game_info(self) -> GameInfo:
        """Return game information and metadata."""
        pass
    
    @abstractmethod
    def get_config_model(self) -> Type[GameConfig]:
        """Return the Pydantic model for game configuration."""
        pass
    
    @abstractmethod
    def get_state_model(self) -> Type[GameStateBase]:
        """Return the Pydantic model for game state."""
        pass
    
    @abstractmethod
    def create_initial_state(self, game_id: str, config: GameConfig) -> GameStateBase:
        """Create initial game state from validated configuration."""
        pass
    
    def validate_config(self, config_dict: Dict[str, Any]) -> GameConfig:
        """Validate and parse game configuration using the game's config model."""
        config_model = self.get_config_model()
        try:
            return config_model(**config_dict)
        except Exception as e:
            logger.error(f"Config validation failed for {self.get_game_type()}: {e}")
            raise ValueError(f"Invalid configuration: {str(e)}")
    
    def get_json_schema(self) -> Dict[str, Any]:
        """Get JSON schema for game configuration."""
        config_model = self.get_config_model()
        return config_model.model_json_schema()


class PluginRegistry:
    """Registry for managing game plugins."""
    
    def __init__(self):
        self.plugins: Dict[str, GamePlugin] = {}
        logger.info("Plugin registry initialized")
    
    def register(self, plugin: GamePlugin):
        """Register a game plugin."""
        game_type = plugin.get_game_type()
        
        if game_type in self.plugins:
            raise ValueError(f"Game type '{game_type}' already registered")
        
        # Validate plugin
        try:
            info = plugin.get_game_info()
            config_model = plugin.get_config_model()
            state_model = plugin.get_state_model()
            
            logger.info(f"Registering game plugin: {game_type} - {info.name}")
            
        except Exception as e:
            raise ValueError(f"Invalid plugin for {game_type}: {str(e)}")
        
        self.plugins[game_type] = plugin
        logger.debug(f"Successfully registered plugin: {game_type}")
    
    def get(self, game_type: str) -> GamePlugin:
        """Get a plugin by game type."""
        if game_type not in self.plugins:
            available = ", ".join(self.plugins.keys())
            raise ValueError(f"Unknown game type: {game_type}. Available: {available}")
        return self.plugins[game_type]
    
    def list_types(self) -> List[str]:
        """Get list of registered game types."""
        return list(self.plugins.keys())
    
    def get_all_info(self) -> Dict[str, GameInfo]:
        """Get info for all registered games."""
        return {
            game_type: plugin.get_game_info()
            for game_type, plugin in self.plugins.items()
        }
    
    def has_plugin(self, game_type: str) -> bool:
        """Check if a plugin is registered."""
        return game_type in self.plugins
    
    def unregister(self, game_type: str) -> bool:
        """Unregister a plugin."""
        if game_type in self.plugins:
            del self.plugins[game_type]
            logger.info(f"Unregistered plugin: {game_type}")
            return True
        return False
    
    def clear(self):
        """Clear all registered plugins."""
        count = len(self.plugins)
        self.plugins.clear()
        logger.info(f"Cleared {count} plugins from registry")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_plugins": len(self.plugins),
            "registered_types": list(self.plugins.keys()),
            "plugin_info": {
                game_type: {
                    "name": plugin.get_game_info().name,
                    "category": plugin.get_game_info().category,
                    "version": plugin.get_game_info().version
                }
                for game_type, plugin in self.plugins.items()
            }
        }


def load_plugin_from_module(module_name: str) -> GamePlugin:
    """Load a game plugin from a module."""
    try:
        module = __import__(module_name, fromlist=[''])
        
        if hasattr(module, 'create_plugin'):
            plugin = module.create_plugin()
            if not isinstance(plugin, GamePlugin):
                raise ValueError(f"create_plugin() must return a GamePlugin instance")
            return plugin
        else:
            raise ValueError(f"Module {module_name} missing create_plugin() function")
            
    except ImportError as e:
        raise ValueError(f"Failed to import {module_name}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error creating plugin from {module_name}: {str(e)}")


def discover_plugins(game_names: List[str], package_prefix: str = "games") -> PluginRegistry:
    """Discover and load game plugins."""
    registry = PluginRegistry()
    
    for game_name in game_names:
        try:
            module_name = f"{package_prefix}.{game_name}"
            plugin = load_plugin_from_module(module_name)
            registry.register(plugin)
            
        except Exception as e:
            logger.error(f"Failed to load game {game_name}: {e}")
    
    return registry