# chuk_mcp_game_server/plugins/__init__.py
"""
Plugin System
=============

Plugin system for the MCP game framework.
Provides plugin registry, base classes, and discovery utilities.

Public API:
    Core Classes:
        - GamePlugin: Abstract base class for game plugins
        - PluginRegistry: Registry for managing game plugins
    
    Functions:
        - load_plugin_from_module: Load plugin from Python module
        - discover_plugins: Auto-discover and load plugins

Example Usage:
    ```python
    from chuk_mcp_game_server.plugins import PluginRegistry, GamePlugin
    from chuk_mcp_game_server.core.models import GameInfo, GameCategory
    
    class MyGamePlugin(GamePlugin):
        def get_game_type(self) -> str:
            return "my_game"
        
        def get_game_info(self) -> GameInfo:
            return GameInfo(
                name="My Game",
                description="A sample game",
                category=GameCategory.DEMO
            )
        # ... implement other required methods
    
    # Register plugin
    registry = PluginRegistry()
    registry.register(MyGamePlugin())
    
    # Use plugin
    plugin = registry.get("my_game")
    state = plugin.create_initial_state("game_123", config)
    ```
"""

# Core plugin classes
from .plugin_registry import GamePlugin, PluginRegistry

# Utility functions
from .plugin_registry import load_plugin_from_module, discover_plugins

# Version information - imported from project metadata
try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("chuk_mcp_game_server")
    except PackageNotFoundError:
        # Fallback during development when package isn't installed
        __version__ = "1.0.0"
except ImportError:
    # Python < 3.8 fallback
    try:
        from importlib_metadata import version, PackageNotFoundError
        try:
            __version__ = version("chuk_mcp_game_server")
        except PackageNotFoundError:
            __version__ = "1.0.0"
    except ImportError:
        __version__ = "1.0.0"

__author__ = "MCP Game Framework"

# Public API
__all__ = [
    # Core classes
    "GamePlugin",
    "PluginRegistry",
    
    # Utility functions
    "load_plugin_from_module",
    "discover_plugins",
]

# Convenience function for creating a registry with common plugins
def create_plugin_registry(auto_discover: bool = False, 
                          plugin_modules: list = None) -> PluginRegistry:
    """
    Create a plugin registry with optional auto-discovery.
    
    Args:
        auto_discover: Whether to auto-discover plugins
        plugin_modules: List of module names to load plugins from
    
    Returns:
        PluginRegistry: Configured plugin registry
    """
    registry = PluginRegistry()
    
    if plugin_modules:
        for module_name in plugin_modules:
            try:
                plugin = load_plugin_from_module(module_name)
                registry.register(plugin)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load plugin from {module_name}: {e}")
    
    return registry


def create_empty_registry() -> PluginRegistry:
    """Create an empty plugin registry."""
    return PluginRegistry()


def load_plugins_from_list(plugin_modules: list, 
                          package_prefix: str = "games") -> PluginRegistry:
    """
    Load plugins from a list of module names.
    
    Args:
        plugin_modules: List of module names to load
        package_prefix: Package prefix for module resolution
    
    Returns:
        PluginRegistry: Registry with loaded plugins
    """
    return discover_plugins(plugin_modules, package_prefix)


def validate_plugin(plugin: GamePlugin) -> tuple[bool, str]:
    """
    Validate a plugin implementation.
    
    Args:
        plugin: Plugin instance to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Check required methods are implemented
        game_type = plugin.get_game_type()
        if not game_type or not isinstance(game_type, str):
            return False, "get_game_type() must return a non-empty string"
        
        game_info = plugin.get_game_info()
        if not game_info:
            return False, "get_game_info() must return a GameInfo instance"
        
        config_model = plugin.get_config_model()
        if not config_model:
            return False, "get_config_model() must return a Pydantic model class"
        
        state_model = plugin.get_state_model()
        if not state_model:
            return False, "get_state_model() must return a Pydantic model class"
        
        # Test schema generation
        schema = plugin.get_json_schema()
        if not isinstance(schema, dict):
            return False, "get_json_schema() must return a dictionary"
        
        return True, "Plugin validation successful"
        
    except Exception as e:
        return False, f"Plugin validation failed: {str(e)}"


def get_plugin_info(plugin: GamePlugin) -> dict:
    """
    Get comprehensive information about a plugin.
    
    Args:
        plugin: Plugin instance
    
    Returns:
        dict: Plugin information dictionary
    """
    try:
        game_info = plugin.get_game_info()
        return {
            "game_type": plugin.get_game_type(),
            "name": game_info.name,
            "description": game_info.description,
            "category": game_info.category,
            "version": game_info.version,
            "author": game_info.author,
            "features": game_info.features,
            "min_players": game_info.min_players,
            "max_players": game_info.max_players,
            "complexity_score": game_info.complexity_score,
            "estimated_duration_minutes": game_info.estimated_duration_minutes,
            "config_schema": plugin.get_json_schema()
        }
    except Exception as e:
        return {
            "error": f"Failed to get plugin info: {str(e)}"
        }


# Package information
PACKAGE_INFO = {
    "name": "chuk_mcp_game_server.plugins",
    "version": __version__,
    "description": "Plugin system for MCP game framework",
    "features": [
        "Abstract base class for game plugins",
        "Centralized plugin registry with validation",
        "Dynamic plugin loading from modules",
        "Plugin discovery utilities",
        "Type-safe plugin interfaces",
        "Comprehensive error handling",
        "Plugin validation and information extraction",
        "JSON schema generation for configurations"
    ],
    "dependencies": [
        "typing",
        "abc",
        "logging"
    ]
}

def get_package_info():
    """Get information about this package."""
    return PACKAGE_INFO.copy()

def get_version():
    """Get package version."""
    return __version__

def list_plugin_requirements():
    """Get list of requirements for implementing a plugin."""
    return [
        "Inherit from GamePlugin abstract base class",
        "Implement get_game_type() -> str",
        "Implement get_game_info() -> GameInfo", 
        "Implement get_config_model() -> Type[GameConfig]",
        "Implement get_state_model() -> Type[GameStateBase]",
        "Implement create_initial_state(game_id, config) -> GameStateBase",
        "Optional: Override validate_config() for custom validation",
        "Optional: Override get_json_schema() for custom schema"
    ]

def get_plugin_template():
    """Get a template for implementing a new plugin."""
    return '''
from chuk_mcp_game_server.plugins import GamePlugin
from chuk_mcp_game_server.core import (
    GameStateBase, GameConfig, GameInfo, 
    GameCategory, DifficultyLevel, GameFeature
)
from typing import Type
from pydantic import Field

class MyGameState(GameStateBase):
    """State model for your game."""
    # Add your game-specific state fields here
    pass

class MyGameConfig(GameConfig):
    """Configuration model for your game.""" 
    # Add your game-specific config fields here
    pass

class MyGamePlugin(GamePlugin):
    """Plugin implementation for your game."""
    
    def get_game_type(self) -> str:
        return "my_game"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="My Game",
            description="Description of your game",
            category=GameCategory.DEMO,
            difficulty=DifficultyLevel.MEDIUM,
            features=[GameFeature.SINGLE_PLAYER],
            version="1.0.0",
            author="Your Name"
        )
    
    def get_config_model(self) -> Type[GameConfig]:
        return MyGameConfig
    
    def get_state_model(self) -> Type[GameStateBase]:
        return MyGameState
    
    def create_initial_state(self, game_id: str, config: GameConfig) -> GameStateBase:
        return MyGameState(
            game_id=game_id,
            game_type=self.get_game_type()
        )

# Plugin factory function
def create_plugin() -> GamePlugin:
    return MyGamePlugin()
'''