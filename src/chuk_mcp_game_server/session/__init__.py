# chuk_mcp_game_server/session/__init__.py
"""
Session Management Package
==========================

Comprehensive session management system for the MCP game framework.
Provides session lifecycle management, filtering, statistics, and cleanup operations.

Public API:
    Core Classes:
        - GameSession: Individual game session with validation and lifecycle management
        - GameSessionManager: Manages multiple sessions with advanced features
    
    Models:
        - SessionCreationRequest: Request model for creating sessions
        - SessionFilter: Advanced filtering criteria for session queries
        - SessionStats: Comprehensive session statistics
        - CleanupCriteria: Criteria for session cleanup operations
        - CleanupResult: Result of cleanup operations
        - SessionBulkOperation: Bulk operation definitions
        - SessionBulkResult: Results of bulk operations
    
    Enums:
        - SessionStatus: Session status enumeration
        - OperationType: Types of operations on sessions
        - FilterOperator: Filter operators for queries

Example Usage:
    ```python
    from chuk_mcp_game_server.session import (
        GameSessionManager, SessionCreationRequest, SessionFilter
    )
    
    # Create session manager
    manager = GameSessionManager(plugin_registry)
    
    # Create a new session
    request = SessionCreationRequest(
        game_type="chess",
        tags=["competitive", "rated"],
        config={"time_limit": 1800}
    )
    result = await manager.create_session(request)
    
    # Filter sessions
    filter_criteria = SessionFilter(
        game_type="chess",
        tags=["competitive"],
        include_completed=False
    )
    sessions = await manager.list_sessions(filter_criteria)
    
    # Cleanup old sessions
    cleanup_criteria = CleanupCriteria(
        max_age_hours=24,
        max_idle_hours=6,
        keep_completed=True
    )
    result = await manager.cleanup_sessions(cleanup_criteria)
    ```
"""

# Core session management classes
from .game_session import GameSession
from .game_session_manager import GameSessionManager

# Session models and data structures
from .models import (
    # Request/Response models
    SessionCreationRequest,
    SessionListResponse,
    SessionUpdateRequest,
    
    # Session information models
    GameSessionInfo,
    SessionSummary,
    
    # Statistics models
    SessionStats,
    SessionTypeStats,
    
    # Filter and query models
    SessionFilter,
    SessionSortOptions,
    SessionQuery,
    SessionQueryResult,
    
    # Operation models
    SessionOperation,
    SessionBulkOperation,
    SessionBulkResult,
    
    # Cleanup models
    CleanupCriteria,
    CleanupResult,
    
    # Health monitoring
    SessionManagerHealth,
    
    # Enums
    SessionStatus,
    OperationType,
    FilterOperator,
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
    # Core classes
    "GameSession",
    "GameSessionManager",
    
    # Request/Response models
    "SessionCreationRequest",
    "SessionListResponse", 
    "SessionUpdateRequest",
    
    # Information models
    "GameSessionInfo",
    "SessionSummary",
    
    # Statistics
    "SessionStats",
    "SessionTypeStats",
    
    # Filtering and querying
    "SessionFilter",
    "SessionSortOptions",
    "SessionQuery", 
    "SessionQueryResult",
    
    # Operations
    "SessionOperation",
    "SessionBulkOperation",
    "SessionBulkResult",
    
    # Cleanup
    "CleanupCriteria",
    "CleanupResult",
    
    # Health monitoring
    "SessionManagerHealth",
    
    # Enums
    "SessionStatus",
    "OperationType", 
    "FilterOperator",
]

# Convenience imports for common patterns
def create_session_manager(plugin_registry=None, **config):
    """
    Create a configured session manager.
    
    Args:
        plugin_registry: Plugin registry instance
        **config: Configuration options (max_sessions, default_timeout_hours, etc.)
    
    Returns:
        GameSessionManager: Configured session manager
    """
    manager = GameSessionManager(plugin_registry)
    if config:
        manager.configure(**config)
    return manager


def create_basic_filter(game_type=None, tags=None, include_completed=True, 
                       max_age_hours=None, active_only=False):
    """
    Create a basic session filter with common options.
    
    Args:
        game_type: Filter by specific game type
        tags: Filter by tags (OR logic)
        include_completed: Whether to include completed sessions
        max_age_hours: Maximum session age in hours
        active_only: If True, only return the active session
    
    Returns:
        SessionFilter: Configured filter
    """
    return SessionFilter(
        game_type=game_type,
        tags=tags or [],
        include_completed=include_completed,
        max_age_hours=max_age_hours,
        is_active_session=True if active_only else None
    )


def create_cleanup_criteria(max_age_hours=24, max_idle_hours=12, 
                           keep_completed=True, keep_active=True, dry_run=False):
    """
    Create cleanup criteria with sensible defaults.
    
    Args:
        max_age_hours: Maximum session age before cleanup
        max_idle_hours: Maximum idle time before cleanup  
        keep_completed: Whether to preserve completed sessions
        keep_active: Whether to preserve the active session
        dry_run: If True, don't actually delete sessions
    
    Returns:
        CleanupCriteria: Configured cleanup criteria
    """
    return CleanupCriteria(
        max_age_hours=max_age_hours,
        max_idle_hours=max_idle_hours,
        keep_completed=keep_completed,
        keep_active=keep_active,
        dry_run=dry_run
    )


# Package-level constants
DEFAULT_MAX_SESSIONS = 100
DEFAULT_SESSION_TIMEOUT_HOURS = 24
DEFAULT_IDLE_TIMEOUT_HOURS = 12

# Package information
PACKAGE_INFO = {
    "name": "chuk_mcp_game_server.session",
    "version": __version__,
    "description": "Session management system for MCP game framework",
    "features": [
        "Individual session lifecycle management",
        "Multi-session management with advanced filtering",
        "Bulk operations (delete, tag, etc.)",
        "Automatic cleanup with configurable criteria", 
        "Comprehensive statistics and health monitoring",
        "Type-safe Pydantic models throughout",
        "Async/await support for all operations",
        "Extensive validation and error handling"
    ],
    "dependencies": [
        "pydantic>=1.8",
        "datetime",
        "typing",
        "logging"
    ]
}

# Helper function for module information
def get_package_info():
    """Get information about this package."""
    return PACKAGE_INFO.copy()


def get_version():
    """Get package version."""
    return __version__