# chuk_mcp_game_server/session/models.py
"""
Session Models
==============

Pydantic models specific to session management.
Updated to work with separated GameSession and GameSessionManager architecture
and migrated to Pydantic v2.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


# ================================================================== Enums

class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    IDLE = "idle"
    STALE = "stale"
    ERROR = "error"


class OperationType(str, Enum):
    """Types of operations that can be performed on sessions."""
    CREATE = "create"
    DELETE = "delete"
    UPDATE = "update"
    TAG = "tag"
    CLEANUP = "cleanup"
    BULK_DELETE = "bulk_delete"
    BULK_TAG = "bulk_tag"


class FilterOperator(str, Enum):
    """Filter operators for advanced queries."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"


# ================================================================== Core Session Models

class GameSessionInfo(BaseModel):
    """Game session information for API responses."""
    session_id: str = Field(..., description="Session identifier")
    game_type: str = Field(..., description="Type of game")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed: datetime = Field(..., description="Last access timestamp")
    tags: List[str] = Field(default_factory=list, description="Session tags")
    is_active: bool = Field(default=False, description="Whether this is the active session")
    is_completed: bool = Field(default=False, description="Whether game is finished")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Current session status")
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "use_enum_values": True
    }
    
    @field_validator('status')
    @classmethod
    def determine_status(cls, v, info):
        """Automatically determine status based on other fields."""
        if info.data and info.data.get('is_completed'):
            return SessionStatus.COMPLETED
        
        # Calculate if session is idle/stale based on last_accessed
        last_accessed = info.data.get('last_accessed') if info.data else None
        if last_accessed:
            idle_hours = (datetime.now() - last_accessed).total_seconds() / 3600
            if idle_hours > 24:  # Stale after 24 hours
                return SessionStatus.STALE
            elif idle_hours > 2:  # Idle after 2 hours
                return SessionStatus.IDLE
        
        return SessionStatus.ACTIVE
    
    @property
    def age_seconds(self) -> float:
        """Get session age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now() - self.last_accessed).total_seconds()
    
    @property
    def age_hours(self) -> float:
        """Get session age in hours."""
        return self.age_seconds / 3600
    
    @property
    def idle_hours(self) -> float:
        """Get idle time in hours."""
        return self.idle_seconds / 3600


class SessionSummary(BaseModel):
    """Compact session summary for lists and overviews."""
    session_id: str = Field(..., description="Session identifier")
    game_type: str = Field(..., description="Type of game")
    status: SessionStatus = Field(..., description="Current status")
    tags: List[str] = Field(default_factory=list, description="Session tags")
    age_hours: float = Field(..., ge=0, description="Session age in hours")
    idle_hours: float = Field(..., ge=0, description="Idle time in hours")
    is_active_session: bool = Field(default=False, description="Whether this is the active session")
    
    model_config = {
        "use_enum_values": True
    }


# ================================================================== Statistics Models

class SessionTypeStats(BaseModel):
    """Statistics for a specific game type."""
    game_type: str = Field(..., description="Game type")
    total_sessions: int = Field(..., ge=0, description="Total sessions of this type")
    active_sessions: int = Field(..., ge=0, description="Active sessions")
    completed_sessions: int = Field(..., ge=0, description="Completed sessions")
    average_age_hours: float = Field(..., ge=0, description="Average session age")
    completion_rate: float = Field(..., ge=0, le=100, description="Completion rate percentage")
    
    @field_validator('completion_rate')
    @classmethod
    def calculate_completion_rate(cls, v, info):
        """Calculate completion rate from completed/total."""
        if info.data:
            total = info.data.get('total_sessions', 0)
            completed = info.data.get('completed_sessions', 0)
            if total == 0:
                return 0.0
            return (completed / total) * 100
        return v or 0.0


class SessionStats(BaseModel):
    """Comprehensive session statistics."""
    total_sessions: int = Field(..., ge=0, description="Total number of sessions")
    active_session: Optional[str] = Field(None, description="Currently active session ID")
    sessions_by_type: Dict[str, int] = Field(..., description="Session count by game type")
    sessions_by_status: Dict[str, int] = Field(..., description="Session count by status")
    completed_games: int = Field(..., ge=0, description="Number of completed games")
    average_session_age_hours: float = Field(..., ge=0, description="Average session age in hours")
    oldest_session_hours: float = Field(..., ge=0, description="Age of oldest session in hours")
    type_stats: List[SessionTypeStats] = Field(default_factory=list, description="Per-type statistics")
    
    model_config = {
        "use_enum_values": True
    }
    
    @field_validator('sessions_by_type')
    @classmethod
    def validate_sessions_by_type(cls, v):
        """Ensure all counts are non-negative."""
        for game_type, count in v.items():
            if count < 0:
                raise ValueError(f"Session count for {game_type} cannot be negative")
        return v
    
    @property
    def active_games(self) -> int:
        """Calculate number of active (non-completed) games."""
        return self.total_sessions - self.completed_games
    
    @property
    def completion_rate(self) -> float:
        """Calculate overall completion rate."""
        if self.total_sessions == 0:
            return 0.0
        return (self.completed_games / self.total_sessions) * 100


# ================================================================== Filter Models

class SessionFilter(BaseModel):
    """Advanced filters for session queries."""
    game_type: Optional[str] = Field(None, description="Filter by game type")
    game_types: List[str] = Field(default_factory=list, description="Filter by multiple game types")
    tags: List[str] = Field(default_factory=list, description="Filter by tags (OR logic)")
    tags_all: List[str] = Field(default_factory=list, description="Filter by tags (AND logic)")
    status: Optional[SessionStatus] = Field(None, description="Filter by status")
    statuses: List[SessionStatus] = Field(default_factory=list, description="Filter by multiple statuses")
    include_completed: bool = Field(default=True, description="Include completed games")
    min_age_hours: Optional[float] = Field(None, ge=0, description="Minimum session age in hours")
    max_age_hours: Optional[float] = Field(None, ge=0, description="Maximum session age in hours")
    min_idle_hours: Optional[float] = Field(None, ge=0, description="Minimum idle time in hours")
    max_idle_hours: Optional[float] = Field(None, ge=0, description="Maximum idle time in hours")
    is_active_session: Optional[bool] = Field(None, description="Filter by active session status")
    created_after: Optional[datetime] = Field(None, description="Created after this timestamp")
    created_before: Optional[datetime] = Field(None, description="Created before this timestamp")
    
    model_config = {
        "use_enum_values": True
    }
    
    @field_validator('max_age_hours')
    @classmethod
    def validate_max_age(cls, v, info):
        """Ensure max_age >= min_age."""
        if info.data:
            min_age = info.data.get('min_age_hours')
            if v is not None and min_age is not None and v < min_age:
                raise ValueError("max_age_hours must be >= min_age_hours")
        return v
    
    @field_validator('max_idle_hours')
    @classmethod
    def validate_max_idle(cls, v, info):
        """Ensure max_idle >= min_idle."""
        if info.data:
            min_idle = info.data.get('min_idle_hours')
            if v is not None and min_idle is not None and v < min_idle:
                raise ValueError("max_idle_hours must be >= min_idle_hours")
        return v
    
    @field_validator('created_before')
    @classmethod
    def validate_created_before(cls, v, info):
        """Ensure created_before >= created_after."""
        if info.data:
            created_after = info.data.get('created_after')
            if v is not None and created_after is not None and v < created_after:
                raise ValueError("created_before must be >= created_after")
        return v


class SessionSortOptions(BaseModel):
    """Sorting options for session lists."""
    field: str = Field(default="last_accessed", description="Field to sort by")
    descending: bool = Field(default=True, description="Sort in descending order")
    
    @field_validator('field')
    @classmethod
    def validate_sort_field(cls, v):
        """Validate sort field options."""
        valid_fields = [
            "session_id", "game_type", "created_at", "last_accessed",
            "age_hours", "idle_hours", "is_completed", "status"
        ]
        if v not in valid_fields:
            raise ValueError(f"Sort field must be one of: {valid_fields}")
        return v


# ================================================================== Request/Response Models

class SessionCreationRequest(BaseModel):
    """Request to create a new session."""
    game_type: str = Field(..., description="Type of game to create")
    session_id: Optional[str] = Field(None, description="Optional custom session ID")
    tags: List[str] = Field(default_factory=list, description="Session tags")
    config: Dict[str, Any] = Field(default_factory=dict, description="Game-specific configuration")
    auto_activate: bool = Field(default=True, description="Set as active session if created")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Clean and validate tags."""
        clean_tags = []
        seen = set()
        for tag in v:
            clean_tag = tag.strip()
            if clean_tag and clean_tag not in seen:
                clean_tags.append(clean_tag)
                seen.add(clean_tag)
        return clean_tags
    
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


class SessionListResponse(BaseModel):
    """Response for session list operations."""
    sessions: List[GameSessionInfo] = Field(..., description="List of session information")
    summaries: List[SessionSummary] = Field(default_factory=list, description="Compact session summaries")
    total_count: int = Field(..., ge=0, description="Total number of sessions")
    filtered_count: int = Field(..., ge=0, description="Number of sessions after filtering")
    stats: SessionStats = Field(..., description="Session statistics")
    filter_applied: Optional[SessionFilter] = Field(None, description="Filter that was applied")
    sort_applied: Optional[SessionSortOptions] = Field(None, description="Sort that was applied")
    
    @field_validator('filtered_count')
    @classmethod
    def validate_filtered_count(cls, v, info):
        """Ensure filtered count doesn't exceed total."""
        if info.data:
            total = info.data.get('total_count', 0)
            if v > total:
                raise ValueError("filtered_count cannot exceed total_count")
        return v


class SessionUpdateRequest(BaseModel):
    """Request to update session properties."""
    session_id: str = Field(..., description="Session ID to update")
    tags: Optional[List[str]] = Field(None, description="New tags (replaces existing)")
    add_tags: List[str] = Field(default_factory=list, description="Tags to add")
    remove_tags: List[str] = Field(default_factory=list, description="Tags to remove")
    
    @model_validator(mode='after')
    def validate_tag_operations(self):
        """Ensure tag operations don't conflict."""
        tags = self.tags
        add_tags = self.add_tags or []
        remove_tags = self.remove_tags or []
        
        if tags is not None and (add_tags or remove_tags):
            raise ValueError("Cannot specify both 'tags' and 'add_tags'/'remove_tags'")
        
        # Check for conflicts in add/remove
        conflicts = set(add_tags) & set(remove_tags)
        if conflicts:
            raise ValueError(f"Cannot both add and remove tags: {conflicts}")
        
        return self


# ================================================================== Operation Models

class SessionOperation(BaseModel):
    """Record of a session operation."""
    operation_type: OperationType = Field(..., description="Type of operation")
    session_id: str = Field(..., description="Target session ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Operation timestamp")
    success: bool = Field(..., description="Whether operation succeeded")
    message: Optional[str] = Field(None, description="Operation message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional operation details")
    duration_ms: Optional[float] = Field(None, ge=0, description="Operation duration in milliseconds")
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "use_enum_values": True
    }


class SessionBulkOperation(BaseModel):
    """Bulk operation on multiple sessions."""
    operation: OperationType = Field(..., description="Operation type")
    session_ids: List[str] = Field(..., min_items=1, description="Session IDs to operate on")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    parallel: bool = Field(default=False, description="Execute operations in parallel")
    
    @field_validator('session_ids')
    @classmethod
    def validate_session_ids(cls, v):
        """Ensure no duplicate session IDs."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate session IDs not allowed")
        return v


class SessionBulkResult(BaseModel):
    """Result of a bulk operation."""
    operation: OperationType = Field(..., description="Operation that was performed")
    total_requested: int = Field(..., ge=0, description="Total sessions requested")
    successful: int = Field(..., ge=0, description="Number of successful operations")
    failed: int = Field(..., ge=0, description="Number of failed operations")
    results: List[SessionOperation] = Field(..., description="Individual operation results")
    duration_ms: float = Field(..., ge=0, description="Total operation duration in milliseconds")
    
    class Config:
        use_enum_values = True
    
    @field_validator('successful')
    @classmethod
    def validate_successful_count(cls, v, info):
        """Ensure successful + failed = total."""
        if info.data:
            total = info.data.get('total_requested', 0)
            failed = info.data.get('failed', 0)
            if v + failed != total:
                raise ValueError("successful + failed must equal total_requested")
        return v
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requested == 0:
            return 0.0
        return (self.successful / self.total_requested) * 100


# ================================================================== Cleanup Models

class CleanupCriteria(BaseModel):
    """Criteria for session cleanup operations."""
    max_age_hours: float = Field(24.0, gt=0, description="Maximum session age in hours")
    max_idle_hours: float = Field(12.0, gt=0, description="Maximum idle time in hours")
    keep_completed: bool = Field(default=True, description="Whether to keep completed games")
    keep_active: bool = Field(default=True, description="Whether to keep the active session")
    keep_tagged: List[str] = Field(default_factory=list, description="Keep sessions with these tags")
    exclude_game_types: List[str] = Field(default_factory=list, description="Game types to exclude from cleanup")
    dry_run: bool = Field(default=False, description="If true, don't actually delete sessions")
    
    @field_validator('max_idle_hours')
    @classmethod
    def validate_idle_less_than_age(cls, v, info):
        """Ensure idle timeout is reasonable compared to age timeout."""
        if info.data:
            max_age = info.data.get('max_age_hours', 24.0)
            if v > max_age:
                raise ValueError("max_idle_hours should not exceed max_age_hours")
        return v


class CleanupResult(BaseModel):
    """Result of a cleanup operation."""
    sessions_deleted: int = Field(..., ge=0, description="Number of sessions deleted")
    sessions_kept: int = Field(..., ge=0, description="Number of sessions kept")
    deleted_sessions: List[Dict[str, Any]] = Field(..., description="Details of deleted sessions")
    kept_sessions: List[str] = Field(default_factory=list, description="IDs of sessions that were kept")
    cleanup_criteria: CleanupCriteria = Field(..., description="Criteria used for cleanup")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    duration_ms: float = Field(..., ge=0, description="Cleanup operation duration in milliseconds")
    space_freed_estimate: Optional[str] = Field(None, description="Estimated memory/space freed")
    
    @property
    def total_sessions_processed(self) -> int:
        """Total number of sessions processed."""
        return self.sessions_deleted + self.sessions_kept


# ================================================================== Health & Monitoring

class SessionManagerHealth(BaseModel):
    """Health status of the session manager."""
    status: str = Field(..., description="Overall health status")
    total_sessions: int = Field(..., ge=0, description="Current session count")
    max_sessions: int = Field(..., gt=0, description="Maximum allowed sessions")
    utilization_percent: float = Field(..., ge=0, le=100, description="Session capacity utilization")
    active_session: Optional[str] = Field(None, description="Currently active session")
    uptime_hours: float = Field(..., ge=0, description="Manager uptime in hours")
    oldest_session_hours: float = Field(..., ge=0, description="Age of oldest session")
    stale_sessions_count: int = Field(..., ge=0, description="Number of stale sessions")
    memory_pressure: bool = Field(default=False, description="Whether under memory pressure")
    recommendations: List[str] = Field(default_factory=list, description="Health recommendations")
    
    @field_validator('status')
    @classmethod
    def determine_status(cls, v, info):
        """Determine health status based on metrics."""
        if info.data:
            utilization = info.data.get('utilization_percent', 0)
            stale_count = info.data.get('stale_sessions_count', 0)
            memory_pressure = info.data.get('memory_pressure', False)
            
            if memory_pressure or utilization > 95:
                return "critical"
            elif utilization > 80 or stale_count > 10:
                return "warning"
            else:
                return "healthy"
        return v or "healthy"


# ================================================================== Query Models

class SessionQuery(BaseModel):
    """Advanced session query with multiple filters and sorting."""
    filter: SessionFilter = Field(default_factory=SessionFilter, description="Filter criteria")
    sort: SessionSortOptions = Field(default_factory=SessionSortOptions, description="Sort options")
    limit: Optional[int] = Field(None, gt=0, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    include_summaries: bool = Field(default=True, description="Include compact summaries")
    include_full_info: bool = Field(default=False, description="Include full session info")
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        """Ensure reasonable limit."""
        if v is not None and v > 1000:
            raise ValueError("Limit cannot exceed 1000")
        return v


class SessionQueryResult(BaseModel):
    """Result of an advanced session query."""
    sessions: List[Union[SessionSummary, GameSessionInfo]] = Field(..., description="Query results")
    total_matches: int = Field(..., ge=0, description="Total sessions matching filter")
    returned_count: int = Field(..., ge=0, description="Number of sessions returned")
    has_more: bool = Field(..., description="Whether more results are available")
    query: SessionQuery = Field(..., description="Query that was executed")
    execution_time_ms: float = Field(..., ge=0, description="Query execution time")
    
    @property
    def is_complete_result(self) -> bool:
        """Whether this result contains all matching sessions."""
        return not self.has_more