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
        "Comprehensive error handling"
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