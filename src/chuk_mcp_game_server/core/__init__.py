# chuk_mcp_game_server/core/__init__.py
"""
Core Framework Components
=========================

Core components for the MCP game framework.
Provides base models, type definitions, and framework-wide utilities.

Public API:
    Base Models:
        - GameStateBase: Base class for all game states
        - GameConfig: Base game configuration model
        - TimestampedModel: Base model with timestamp tracking
        - ConfigurableModel: Base model allowing custom fields
    
    API Models:
        - ToolResult: Standard MCP tool result with validation
        - GameInfo: Comprehensive game information model
        - ServerInfo: Server information and capabilities
        - FrameworkStats: Framework-wide statistics
    
    Error Models:
        - GameError: Structured game error with details
        - ValidationError: Validation-specific error
        - ConfigurationError: Configuration-specific error
    
    Enums:
        - GameCategory: Game categorization
        - DifficultyLevel: Game difficulty levels
        - GameFeature: Available game features
        - ResultStatus: Operation result statuses
    
    Utility Functions:
        - create_success_result: Helper for successful results
        - create_error_result: Helper for error results
        - create_warning_result: Helper for warning results
        - create_validation_error_result: Helper for validation errors
        - validate_game_id_format: Game ID validation
        - validate_session_id_format: Session ID validation
        - normalize_game_type: Game type normalization
        - normalize_tag: Tag normalization

Example Usage:
    ```python
    from chuk_mcp_game_server.core import (
        GameStateBase, GameConfig, GameInfo, ToolResult,
        GameCategory, DifficultyLevel, create_success_result
    )
    
    # Define a game state
    class ChessState(GameStateBase):
        board: List[List[str]] = Field(default_factory=list)
        current_player: str = "white"
    
    # Define game info
    info = GameInfo(
        name="Chess",
        description="Classic chess game",
        category=GameCategory.BOARD,
        difficulty=DifficultyLevel.MEDIUM
    )
    
    # Create successful result
    result = create_success_result(
        message="Move completed",
        data={"position": "e2-e4"}
    )
    ```
"""

# Core models and base classes
from .models import (
    # Base Models
    GameStateBase,
    GameConfig,
    TimestampedModel,
    ConfigurableModel,
    
    # API Models
    ToolResult,
    GameInfo,
    ServerInfo,
    FrameworkStats,
    
    # Error Models
    GameError,
    ValidationError,
    ConfigurationError,
    
    # Enums
    GameCategory,
    DifficultyLevel,
    GameFeature,
    ResultStatus,
    
    # Utility Functions
    create_success_result,
    create_error_result,
    create_warning_result,
    create_validation_error_result,
    
    # Validation Helpers
    validate_game_id_format,
    validate_session_id_format,
    normalize_game_type,
    normalize_tag,
)

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

# Public API - main classes and functions users will interact with
__all__ = [
    # Base Models
    "GameStateBase",
    "GameConfig", 
    "TimestampedModel",
    "ConfigurableModel",
    
    # API Models
    "ToolResult",
    "GameInfo",
    "ServerInfo",
    "FrameworkStats",
    
    # Error Models
    "GameError",
    "ValidationError",
    "ConfigurationError",
    
    # Enums
    "GameCategory",
    "DifficultyLevel",
    "GameFeature",
    "ResultStatus",
    
    # Utility Functions
    "create_success_result",
    "create_error_result",
    "create_warning_result",
    "create_validation_error_result",
    
    # Validation Helpers
    "validate_game_id_format",
    "validate_session_id_format",
    "normalize_game_type",
    "normalize_tag",
]

# Convenience functions for common patterns
def create_game_info(name: str, description: str, category: GameCategory = GameCategory.DEMO,
                    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
                    features: list = None, **kwargs) -> GameInfo:
    """
    Create a GameInfo instance with sensible defaults.
    
    Args:
        name: Game display name
        description: Game description
        category: Game category (default: DEMO)
        difficulty: Default difficulty (default: MEDIUM)
        features: List of game features
        **kwargs: Additional GameInfo fields
    
    Returns:
        GameInfo: Configured game information
    """
    return GameInfo(
        name=name,
        description=description,
        category=category,
        difficulty=difficulty,
        features=features or [],
        **kwargs
    )


def create_base_config(session_id: str = None, tags: list = None,
                      difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
                      **custom_settings) -> GameConfig:
    """
    Create a basic GameConfig with common settings.
    
    Args:
        session_id: Optional session ID
        tags: Session tags
        difficulty: Game difficulty
        **custom_settings: Additional custom settings
    
    Returns:
        GameConfig: Configured game configuration
    """
    return GameConfig(
        session_id=session_id,
        tags=tags or [],
        difficulty=difficulty,
        custom_settings=custom_settings
    )


def validate_tool_result(result: dict) -> ToolResult:
    """
    Validate and convert a dictionary to a ToolResult.
    
    Args:
        result: Dictionary with result data
    
    Returns:
        ToolResult: Validated tool result
    
    Raises:
        ValueError: If result data is invalid
    """
    try:
        return ToolResult(**result)
    except Exception as e:
        raise ValueError(f"Invalid tool result data: {str(e)}")


# Package-level constants
DEFAULT_GAME_CATEGORY = GameCategory.DEMO
DEFAULT_DIFFICULTY = DifficultyLevel.MEDIUM
DEFAULT_FEATURES = [GameFeature.SINGLE_PLAYER]

# Framework metadata
FRAMEWORK_INFO = {
    "name": "chuk_mcp_game_server.core",
    "version": __version__,
    "description": "Core framework components for MCP game server",
    "features": [
        "Type-safe Pydantic models throughout",
        "Comprehensive validation and error handling",
        "Extensible base classes for games",
        "Standardized API response models",
        "Rich enum definitions for game metadata",
        "Utility functions for common operations",
        "Timestamp tracking and lifecycle management",
        "Custom field support for extensibility"
    ],
    "dependencies": [
        "pydantic>=1.8",
        "datetime",
        "typing",
        "enum",
        "abc",
        "logging"
    ]
}

def get_framework_info():
    """Get information about the core framework."""
    return FRAMEWORK_INFO.copy()

def get_version():
    """Get framework version."""
    return __version__

def get_supported_categories():
    """Get list of supported game categories."""
    return [category.value for category in GameCategory]

def get_supported_difficulties():
    """Get list of supported difficulty levels."""
    return [difficulty.value for difficulty in DifficultyLevel]

def get_supported_features():
    """Get list of supported game features."""
    return [feature.value for feature in GameFeature]