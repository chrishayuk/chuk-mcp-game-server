# chuk_mcp_game_server/session/game_session.py
"""
Game Session Model
==================

Individual game session model with lifecycle management and validation.
Represents a single game instance with state, metadata, and operations.
Updated for Pydantic v2 compatibility.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator

# core models
from ..core.models import GameStateBase

# session models
from .models import GameSessionInfo

# logger
logger = logging.getLogger(__name__)


class GameSession(BaseModel):
    """
    Individual game session with Pydantic validation.
    
    Represents a single game instance with state management,
    metadata tracking, and lifecycle operations.
    """
    
    session_id: str = Field(..., description="Unique session identifier")
    game_type: str = Field(..., description="Type of game")
    state: GameStateBase = Field(..., description="Current game state")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access timestamp")
    tags: List[str] = Field(default_factory=list, description="Session tags for organization")
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "validate_assignment": True
    }
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        
        # Basic format validation
        clean_id = v.strip()
        if not all(c.isalnum() or c in '_-' for c in clean_id):
            raise ValueError("Session ID can only contain letters, numbers, underscores, and hyphens")
        
        return clean_id
    
    @field_validator('game_type')
    @classmethod
    def validate_game_type(cls, v):
        """Validate game type format."""
        if not v or not v.strip():
            raise ValueError("Game type cannot be empty")
        return v.strip().lower()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Clean and validate tags."""
        if not v:
            return []
        
        # Remove empty tags, strip whitespace, remove duplicates
        clean_tags = []
        seen = set()
        for tag in v:
            if isinstance(tag, str):
                clean_tag = tag.strip()
                if clean_tag and clean_tag not in seen:
                    clean_tags.append(clean_tag)
                    seen.add(clean_tag)
        
        return clean_tags
    
    def __init__(self, **data):
        """Initialize session with proper timestamp handling."""
        # Set created_at if not provided
        if 'created_at' not in data:
            data['created_at'] = datetime.now()
        
        # Set last_accessed to created_at if not provided
        if 'last_accessed' not in data:
            data['last_accessed'] = data['created_at']
        
        super().__init__(**data)
        
        logger.debug(f"Created session {data.get('session_id')} for game type {data.get('game_type')}")
    
    # ================================================================== Lifecycle Methods
    
    def touch(self):
        """Update access time and trigger state timestamp update."""
        self.last_accessed = datetime.now()
        if hasattr(self.state, 'touch'):
            self.state.touch()
        
        logger.debug(f"Touched session {self.session_id}")
    
    def mark_completed(self):
        """Mark the session as completed."""
        if hasattr(self.state, 'is_completed'):
            self.state.is_completed = True
        self.touch()
        
        logger.info(f"Session {self.session_id} marked as completed")
    
    def add_tag(self, tag: str) -> bool:
        """Add a tag to the session."""
        if not tag or not tag.strip():
            return False
        
        clean_tag = tag.strip()
        if clean_tag not in self.tags:
            self.tags.append(clean_tag)
            self.touch()
            logger.debug(f"Added tag '{clean_tag}' to session {self.session_id}")
            return True
        
        return False
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the session."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.touch()
            logger.debug(f"Removed tag '{tag}' from session {self.session_id}")
            return True
        
        return False
    
    def has_tag(self, tag: str) -> bool:
        """Check if session has a specific tag."""
        return tag in self.tags
    
    def has_any_tag(self, tags: List[str]) -> bool:
        """Check if session has any of the specified tags."""
        return any(tag in self.tags for tag in tags)
    
    def has_all_tags(self, tags: List[str]) -> bool:
        """Check if session has all of the specified tags."""
        return all(tag in self.tags for tag in tags)
    
    # ================================================================== Time Calculations
    
    def get_age(self) -> timedelta:
        """Get session age since creation."""
        return datetime.now() - self.created_at
    
    def get_idle_time(self) -> timedelta:
        """Get time since last access."""
        return datetime.now() - self.last_accessed
    
    def get_age_hours(self) -> float:
        """Get session age in hours."""
        return self.get_age().total_seconds() / 3600
    
    def get_idle_hours(self) -> float:
        """Get idle time in hours."""
        return self.get_idle_time().total_seconds() / 3600
    
    def is_older_than(self, hours: float) -> bool:
        """Check if session is older than specified hours."""
        return self.get_age_hours() > hours
    
    def is_idle_longer_than(self, hours: float) -> bool:
        """Check if session has been idle longer than specified hours."""
        return self.get_idle_hours() > hours
    
    # ================================================================== Status Checks
    
    def is_completed(self) -> bool:
        """Check if the game session is completed."""
        return getattr(self.state, 'is_completed', False)
    
    def is_active(self) -> bool:
        """Check if the game session is active (not completed)."""
        return not self.is_completed()
    
    def is_recent(self, hours: float = 1.0) -> bool:
        """Check if session was accessed recently."""
        return self.get_idle_hours() < hours
    
    def is_stale(self, hours: float = 24.0) -> bool:
        """Check if session is stale (old and not accessed recently)."""
        return self.is_older_than(hours) and not self.is_recent()
    
    # ================================================================== Conversion Methods
    
    def to_info(self, is_active_session: bool = False) -> GameSessionInfo:
        """Convert to session info for API responses."""
        return GameSessionInfo(
            session_id=self.session_id,
            game_type=self.game_type,
            created_at=self.created_at,
            last_accessed=self.last_accessed,
            tags=self.tags.copy(),  # Return a copy to prevent mutations
            is_active=is_active_session,
            is_completed=self.is_completed()
        )
    
    def to_dict(self, include_state: bool = True) -> dict:
        """Convert to dictionary with optional state inclusion."""
        data = {
            "session_id": self.session_id,
            "game_type": self.game_type,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "tags": self.tags.copy(),
            "is_completed": self.is_completed(),
            "age_hours": self.get_age_hours(),
            "idle_hours": self.get_idle_hours()
        }
        
        if include_state and hasattr(self.state, 'to_mcp_dict'):
            data["state"] = self.state.to_mcp_dict()
        elif include_state:
            data["state"] = self.state.dict()
        
        return data
    
    def to_summary(self) -> dict:
        """Convert to a compact summary."""
        return {
            "session_id": self.session_id,
            "game_type": self.game_type,
            "tags": self.tags,
            "is_completed": self.is_completed(),
            "age_hours": round(self.get_age_hours(), 2),
            "idle_hours": round(self.get_idle_hours(), 2)
        }
    
    # ================================================================== Comparison Methods
    
    def __eq__(self, other) -> bool:
        """Compare sessions by ID."""
        if not isinstance(other, GameSession):
            return False
        return self.session_id == other.session_id
    
    def __hash__(self) -> int:
        """Hash by session ID."""
        return hash(self.session_id)
    
    def __str__(self) -> str:
        """String representation."""
        status = "completed" if self.is_completed() else "active"
        return f"GameSession({self.session_id}, {self.game_type}, {status})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"GameSession(session_id='{self.session_id}', "
            f"game_type='{self.game_type}', "
            f"is_completed={self.is_completed()}, "
            f"tags={self.tags}, "
            f"age_hours={self.get_age_hours():.2f})"
        )
    
    # ================================================================== State Management
    
    def update_state(self, new_state: GameStateBase):
        """Update the game state and touch the session."""
        self.state = new_state
        self.touch()
        logger.debug(f"Updated state for session {self.session_id}")
    
    def get_state_snapshot(self) -> dict:
        """Get a snapshot of the current state."""
        if hasattr(self.state, 'to_mcp_dict'):
            return self.state.to_mcp_dict()
        return self.state.dict()
    
    # ================================================================== Validation Helpers
    
    @classmethod
    def validate_session_data(cls, data: dict) -> tuple[bool, str]:
        """Validate session data before creation."""
        try:
            # Check required fields
            required_fields = ['session_id', 'game_type', 'state']
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            
            # Validate session ID format
            session_id = data['session_id']
            if not session_id or not session_id.strip():
                return False, "Session ID cannot be empty"
            
            if not all(c.isalnum() or c in '_-' for c in session_id.strip()):
                return False, "Invalid session ID format"
            
            # Validate game type
            game_type = data['game_type']
            if not game_type or not game_type.strip():
                return False, "Game type cannot be empty"
            
            return True, "Valid session data"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    # ================================================================== Utility Methods
    
    def matches_filter(self, 
                      game_type: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      include_completed: bool = True,
                      max_age_hours: Optional[float] = None,
                      max_idle_hours: Optional[float] = None) -> bool:
        """Check if session matches filter criteria."""
        
        # Game type filter
        if game_type and self.game_type != game_type:
            return False
        
        # Completion filter
        if not include_completed and self.is_completed():
            return False
        
        # Tags filter (OR logic - session must have at least one of the specified tags)
        if tags and not self.has_any_tag(tags):
            return False
        
        # Age filter
        if max_age_hours and self.get_age_hours() > max_age_hours:
            return False
        
        # Idle time filter
        if max_idle_hours and self.get_idle_hours() > max_idle_hours:
            return False
        
        return True