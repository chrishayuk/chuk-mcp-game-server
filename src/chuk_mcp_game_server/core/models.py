# chuk_mcp_game_server/core/models.py
"""
Core Models
===========
Core Pydantic models for the MCP game framework.
Provides base classes, common types, and framework-wide utilities.
Updated to work with separated session architecture and Pydantic v2.
"""

from typing import Dict, Any, List, Optional, Union, Type, Literal
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
import logging

logger = logging.getLogger(__name__)


# ================================================================== Enums

class GameCategory(str, Enum):
    """Game category enumeration."""
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    ACTION = "action"
    BOARD = "board"
    CARD = "card"
    TRIVIA = "trivia"
    SIMULATION = "simulation"
    EDUCATIONAL = "educational"
    DEMO = "demo"


class DifficultyLevel(str, Enum):
    """Difficulty level enumeration."""
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"
    CUSTOM = "custom"


class GameFeature(str, Enum):
    """Game feature enumeration."""
    SINGLE_PLAYER = "single_player"
    MULTI_PLAYER = "multi_player"
    PLANNING_DEMO = "planning_demo"
    AI_OPPONENT = "ai_opponent"
    TURN_BASED = "turn_based"
    REAL_TIME = "real_time"
    OBSTACLES = "obstacles"
    OPTIMAL_SOLUTIONS = "optimal_solutions"
    ASCII_ART = "ascii_art"
    VISUALIZATION = "visualization"
    STATISTICS = "statistics"
    REPLAY = "replay"
    UNDO_REDO = "undo_redo"
    SAVE_LOAD = "save_load"


class ResultStatus(str, Enum):
    """Result status for operations."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ================================================================== Base Models

class GameStateBase(BaseModel):
    """
    Base game state model with common fields and functionality.
    All game-specific states should inherit from this.
    """
    game_id: str = Field(..., description="Unique game identifier")
    game_type: str = Field(..., description="Type of game")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    is_completed: bool = Field(default=False, description="Whether game is finished")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    version: str = Field(default="1.0.0", description="State version for compatibility")
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "validate_assignment": True
    }
    
    @field_validator('game_id')
    @classmethod
    def validate_game_id(cls, v):
        """Validate game ID format."""
        if not v or not v.strip():
            raise ValueError("Game ID cannot be empty")
        return v.strip()
    
    @field_validator('game_type')
    @classmethod
    def validate_game_type(cls, v):
        """Validate game type format."""
        if not v or not v.strip():
            raise ValueError("Game type cannot be empty")
        return v.strip().lower()
    
    def touch(self):
        """Update timestamp for change tracking."""
        self.last_updated = datetime.now()
        logger.debug(f"Touched game state {self.game_id}")
    
    def to_mcp_dict(self) -> Dict[str, Any]:
        """Convert to MCP-compatible dictionary."""
        return self.dict()
    
    def get_age(self) -> float:
        """Get state age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_time_since_update(self) -> float:
        """Get time since last update in seconds."""
        return (datetime.now() - self.last_updated).total_seconds()
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata entry."""
        self.metadata[key] = value
        self.touch()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata entry."""
        return self.metadata.get(key, default)
    
    def remove_metadata(self, key: str) -> bool:
        """Remove metadata entry."""
        if key in self.metadata:
            del self.metadata[key]
            self.touch()
            return True
        return False


class GameConfig(BaseModel):
    """
    Base game configuration model.
    Games can extend this for their specific configuration needs.
    """
    session_id: Optional[str] = Field(None, description="Optional session ID")
    tags: List[str] = Field(default_factory=list, description="Configuration tags")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="Game difficulty")
    features: List[GameFeature] = Field(default_factory=list, description="Enabled game features")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom game settings")
    
    model_config = {
        "extra": "allow",
        "use_enum_values": True
    }
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Session ID cannot be empty")
            if not all(c.isalnum() or c in '_-' for c in v):
                raise ValueError("Session ID can only contain letters, numbers, underscores, and hyphens")
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Clean and validate tags."""
        if not v:
            return []
        
        clean_tags = []
        seen = set()
        for tag in v:
            if isinstance(tag, str):
                clean_tag = tag.strip().lower()
                if clean_tag and clean_tag not in seen:
                    clean_tags.append(clean_tag)
                    seen.add(clean_tag)
        
        return clean_tags
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v):
        """Ensure no duplicate features."""
        return list(set(v)) if v else []
    
    def has_feature(self, feature: GameFeature) -> bool:
        """Check if a feature is enabled."""
        return feature in self.features
    
    def add_feature(self, feature: GameFeature):
        """Add a feature."""
        if feature not in self.features:
            self.features.append(feature)
    
    def remove_feature(self, feature: GameFeature):
        """Remove a feature."""
        if feature in self.features:
            self.features.remove(feature)


# ================================================================== API Models

class ToolResult(BaseModel):
    """
    Standard MCP tool result with comprehensive validation.
    Used consistently across all framework operations.
    """
    success: bool = Field(..., description="Whether operation succeeded")
    status: ResultStatus = Field(default=ResultStatus.SUCCESS, description="Result status")
    message: Optional[str] = Field(None, description="Human-readable message")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional result data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Result timestamp")
    duration_ms: Optional[float] = Field(None, ge=0, description="Operation duration in milliseconds")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "use_enum_values": True
    }
    
    @model_validator(mode='after')
    def validate_result(self):
        """Validate result consistency."""
        success = self.success
        status = self.status
        error = self.error
        
        # Auto-set status based on success if not explicitly set
        if success and status == ResultStatus.SUCCESS:
            pass  # Consistent
        elif not success and status == ResultStatus.SUCCESS:
            self.status = ResultStatus.ERROR
        
        # Validate error requirements
        if not success and not error:
            raise ValueError("Error message required when success=False")
        if success and error:
            raise ValueError("Cannot have error when success=True")
        
        return self
    
    def __bool__(self):
        """Allow using ToolResult in boolean context."""
        return self.success
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        if warning and warning not in self.warnings:
            self.warnings.append(warning)
    
    def has_warnings(self) -> bool:
        """Check if result has warnings."""
        return len(self.warnings) > 0


class GameInfo(BaseModel):
    """
    Comprehensive game information model.
    Used for game plugin metadata and discovery.
    """
    name: str = Field(..., description="Display name of the game")
    description: str = Field(..., description="Detailed game description")
    short_description: Optional[str] = Field(None, description="Brief game description")
    category: GameCategory = Field(..., description="Game category")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="Default difficulty")
    min_players: int = Field(1, ge=1, le=100, description="Minimum number of players")
    max_players: int = Field(1, ge=1, le=100, description="Maximum number of players")
    features: List[GameFeature] = Field(default_factory=list, description="Supported game features")
    version: str = Field(default="1.0.0", description="Game plugin version")
    author: Optional[str] = Field(None, description="Game plugin author")
    homepage: Optional[str] = Field(None, description="Game homepage URL")
    tags: List[str] = Field(default_factory=list, description="Game tags for discovery")
    estimated_duration_minutes: Optional[int] = Field(None, ge=1, description="Estimated game duration")
    complexity_score: float = Field(default=5.0, ge=1.0, le=10.0, description="Complexity score (1-10)")
    
    model_config = {
        "use_enum_values": True
    }
    
    @field_validator('max_players')
    @classmethod
    def validate_max_players(cls, v, info):
        """Ensure max_players >= min_players."""
        min_players = info.data.get('min_players', 1) if info.data else 1
        if v < min_players:
            raise ValueError("max_players must be >= min_players")
        return v
    
    @field_validator('short_description')
    @classmethod
    def set_short_description(cls, v, info):
        """Auto-generate short description if not provided."""
        if not v and info.data:
            description = info.data.get('description', '')
            if description:
                # Take first sentence or first 100 characters
                first_sentence = description.split('.')[0]
                if len(first_sentence) <= 100:
                    return first_sentence + '.'
                else:
                    return description[:97] + '...'
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Clean and validate tags."""
        clean_tags = []
        seen = set()
        for tag in v:
            if isinstance(tag, str):
                clean_tag = tag.strip().lower()
                if clean_tag and clean_tag not in seen:
                    clean_tags.append(clean_tag)
                    seen.add(clean_tag)
        return clean_tags
    
    def is_multiplayer(self) -> bool:
        """Check if game supports multiple players."""
        return self.max_players > 1
    
    def supports_feature(self, feature: GameFeature) -> bool:
        """Check if game supports a feature."""
        return feature in self.features
    
    def get_complexity_description(self) -> str:
        """Get human-readable complexity description."""
        if self.complexity_score <= 2:
            return "Very Simple"
        elif self.complexity_score <= 4:
            return "Simple"
        elif self.complexity_score <= 6:
            return "Moderate"
        elif self.complexity_score <= 8:
            return "Complex"
        else:
            return "Very Complex"


# ================================================================== Error Models

class GameError(BaseModel):
    """Structured game error with detailed information."""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    context: Optional[Dict[str, Any]] = Field(None, description="Error context information")
    suggestions: List[str] = Field(default_factory=list, description="Suggested fixes")
    
    model_config = {
        "extra": "forbid",
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }


class ValidationError(GameError):
    """Validation error with field-specific information."""
    error_type: Literal["validation_error"] = "validation_error"
    field_errors: List[Dict[str, str]] = Field(default_factory=list, description="Field-specific errors")
    
    def add_field_error(self, field: str, error: str):
        """Add a field-specific error."""
        self.field_errors.append({"field": field, "error": error})


class ConfigurationError(GameError):
    """Configuration error with setting information."""
    error_type: Literal["configuration_error"] = "configuration_error"
    invalid_settings: List[str] = Field(default_factory=list, description="Invalid configuration settings")
    
    def add_invalid_setting(self, setting: str):
        """Add an invalid setting."""
        if setting not in self.invalid_settings:
            self.invalid_settings.append(setting)


# ================================================================== Server Models

class ServerInfo(BaseModel):
    """Comprehensive server information."""
    name: str = Field(..., description="Server name")
    version: str = Field(..., description="Server version")
    framework_version: str = Field(..., description="Framework version")
    start_time: datetime = Field(..., description="Server start time")
    uptime_seconds: float = Field(..., ge=0, description="Server uptime in seconds")
    capabilities: List[str] = Field(..., description="Server capabilities")
    registered_games: Dict[str, GameInfo] = Field(..., description="Available games")
    features: List[str] = Field(..., description="Server features")
    limits: Dict[str, Any] = Field(default_factory=dict, description="Server limits")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment information")
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }
    
    @computed_field
    @property
    def uptime_hours(self) -> float:
        """Get uptime in hours."""
        return self.uptime_seconds / 3600
    
    @computed_field
    @property
    def game_count(self) -> int:
        """Get number of registered games."""
        return len(self.registered_games)


class FrameworkStats(BaseModel):
    """Framework-wide statistics."""
    total_games_registered: int = Field(..., ge=0, description="Total registered games")
    total_sessions_created: int = Field(..., ge=0, description="Total sessions ever created")
    active_sessions: int = Field(..., ge=0, description="Currently active sessions")
    completed_sessions: int = Field(..., ge=0, description="Completed sessions")
    server_uptime_hours: float = Field(..., ge=0, description="Server uptime in hours")
    memory_usage_mb: Optional[float] = Field(None, ge=0, description="Memory usage in MB")
    request_count: int = Field(default=0, ge=0, description="Total requests processed")
    error_count: int = Field(default=0, ge=0, description="Total errors encountered")
    
    @computed_field
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100
    
    @computed_field
    @property
    def completion_rate(self) -> float:
        """Calculate session completion rate."""
        total_sessions = self.active_sessions + self.completed_sessions
        if total_sessions == 0:
            return 0.0
        return (self.completed_sessions / total_sessions) * 100


# ================================================================== Utility Functions

def create_success_result(message: str = None, data: Dict[str, Any] = None, 
                         warnings: List[str] = None) -> ToolResult:
    """Helper to create successful tool results."""
    return ToolResult(
        success=True,
        status=ResultStatus.SUCCESS,
        message=message,
        data=data,
        warnings=warnings or []
    )


def create_error_result(error: str, error_code: str = None, 
                       data: Dict[str, Any] = None) -> ToolResult:
    """Helper to create error tool results."""
    return ToolResult(
        success=False,
        status=ResultStatus.ERROR,
        error=error,
        error_code=error_code,
        data=data
    )


def create_warning_result(message: str, warnings: List[str], 
                         data: Dict[str, Any] = None) -> ToolResult:
    """Helper to create warning tool results."""
    return ToolResult(
        success=True,
        status=ResultStatus.WARNING,
        message=message,
        warnings=warnings,
        data=data
    )


def create_validation_error_result(field_errors: List[Dict[str, str]]) -> ToolResult:
    """Helper to create validation error results."""
    error = ValidationError(
        message="Validation failed",
        field_errors=field_errors
    )
    
    return ToolResult(
        success=False,
        status=ResultStatus.ERROR,
        error="Validation failed",
        error_code="validation_error",
        data=error.dict()
    )


# ================================================================== Type Helpers

class ConfigurableModel(BaseModel):
    """Base class for models that can be configured with custom fields."""
    
    model_config = {
        "extra": "allow",
        "validate_assignment": True
    }
    
    def get_custom_fields(self) -> Dict[str, Any]:
        """Get all custom (non-schema) fields."""
        schema_fields = set(self.__fields__.keys())
        all_fields = set(self.__dict__.keys())
        custom_fields = all_fields - schema_fields
        
        return {field: getattr(self, field) for field in custom_fields}
    
    def set_custom_field(self, name: str, value: Any):
        """Set a custom field."""
        setattr(self, name, value)
    
    def has_custom_field(self, name: str) -> bool:
        """Check if custom field exists."""
        return hasattr(self, name) and name not in self.__fields__


class TimestampedModel(BaseModel):
    """Base class for models that track creation and update times."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }
    
    def touch(self):
        """Update the timestamp."""
        self.updated_at = datetime.now()
    
    def get_age_seconds(self) -> float:
        """Get age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_time_since_update_seconds(self) -> float:
        """Get time since last update in seconds."""
        return (datetime.now() - self.updated_at).total_seconds()


# ================================================================== Validation Helpers

def validate_game_id_format(game_id: str) -> bool:
    """Validate game ID format."""
    if not game_id or not game_id.strip():
        return False
    clean_id = game_id.strip()
    return all(c.isalnum() or c in '_-' for c in clean_id)


def validate_session_id_format(session_id: str) -> bool:
    """Validate session ID format."""
    return validate_game_id_format(session_id)  # Same rules for now


def normalize_game_type(game_type: str) -> str:
    """Normalize game type to standard format."""
    return game_type.strip().lower() if game_type else ""


def normalize_tag(tag: str) -> str:
    """Normalize tag to standard format."""
    return tag.strip().lower() if tag else ""