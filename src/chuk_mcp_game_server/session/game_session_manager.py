# chuk_mcp_game_server/session/game_session_manager.py
"""
Game Session Manager - Enhanced (COMPLETELY FIXED)
==================================================

Enhanced session manager with event system, improved ID generation, and better enum handling.
Manages multiple game sessions with Pydantic validation and type safety.
Handles session lifecycle, state persistence, statistics, and cleanup operations.

FIXED ISSUES:
- Event emission enum handling (no more 'str' object has no attribute 'value' errors)
- Proper type conversion before event emission
- Enhanced error handling and validation
- All enum operations now use safe string conversion
"""

import logging
import uuid
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# core models
from ..core.models import ToolResult, create_success_result, create_error_result

# enhanced session models and game session
from .models import (
    SessionStats, SessionFilter, CleanupCriteria, CleanupResult,
    SessionCreationRequest, SessionListResponse, SessionBulkOperation, 
    SessionBulkResult, SessionOperation, SessionEvent, EventType, EventHandler,
    safe_enum_to_string  # Import the safe conversion function
)
from .game_session import GameSession

# plugins
from ..plugins import PluginRegistry

# logger
logger = logging.getLogger(__name__)


class GameSessionManager:
    """
    Enhanced session manager with bulletproof event system.
    
    Features:
    - Event-driven architecture with customizable handlers
    - Improved session ID generation  
    - Bulletproof enum handling and serialization
    - Enhanced error handling and validation
    - Performance tracking and monitoring
    
    Provides session lifecycle management, filtering, statistics,
    cleanup operations, and bulk operations.
    """
    
    def __init__(self, plugin_registry: PluginRegistry = None, event_handler: EventHandler = None):
        self.sessions: Dict[str, GameSession] = {}
        self.plugin_registry = plugin_registry or PluginRegistry()
        self.event_handler = event_handler
        self.active_session_id: Optional[str] = None
        self.start_time = datetime.now()
        
        # Configuration
        self._max_sessions = 100
        self._default_session_timeout_hours = 24
        self._default_idle_timeout_hours = 12
        
        # Event tracking
        self._events_today = 0
        self._last_event_date = datetime.now().date()
        
        logger.info("Enhanced game session manager initialized")
    
    # ================================================================== Event System (BULLETPROOF)
    
    async def _emit_event(self, event_type, session_id: str = None, 
                         correlation_id: str = None, **details):
        """Emit a session event with bulletproof enum handling."""
        try:
            # Reset daily counter if needed
            today = datetime.now().date()
            if today != self._last_event_date:
                self._events_today = 0
                self._last_event_date = today
            
            self._events_today += 1
            
            # BULLETPROOF enum handling - use the safe conversion function
            event_type_str = safe_enum_to_string(event_type)
            
            # Create event with guaranteed string value
            event = SessionEvent(
                event_type=event_type_str,
                session_id=session_id,
                correlation_id=correlation_id,
                details=details
            )
            
            if self.event_handler:
                await self.event_handler(event)
            
            logger.debug(f"Event emitted: {event.to_log_message()}")
            
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
            # Don't re-raise to prevent cascade failures
    
    def set_event_handler(self, handler: EventHandler):
        """Set the event handler for session events."""
        self.event_handler = handler
        logger.info("Event handler updated")
    
    # ================================================================== Configuration
    
    def configure(self, 
                 max_sessions: int = None,
                 default_timeout_hours: int = None,
                 default_idle_hours: int = None):
        """Configure session manager settings."""
        if max_sessions is not None:
            self._max_sessions = max(1, max_sessions)
        if default_timeout_hours is not None:
            self._default_session_timeout_hours = max(1, default_timeout_hours)
        if default_idle_hours is not None:
            self._default_idle_timeout_hours = max(1, default_idle_hours)
        
        logger.info(f"Session manager configured: max_sessions={self._max_sessions}, "
                   f"timeout={self._default_session_timeout_hours}h, "
                   f"idle={self._default_idle_timeout_hours}h")
    
    # ================================================================== Enhanced Session ID Generation
    
    def _generate_session_id(self, game_type: str) -> str:
        """Generate a more readable and unique session ID."""
        # Enhanced format: game-MMDDHHMMM-xxxxxx
        now = datetime.now()
        date_part = now.strftime("%m%d")  # MMDD
        time_part = now.strftime("%H%M")  # HHMM
        short_uuid = uuid.uuid4().hex[:6]  # 6-char hash
        
        base_id = f"{game_type}-{date_part}{time_part}-{short_uuid}"
        
        # Ensure uniqueness (very unlikely collision, but safety first)
        counter = 0
        session_id = base_id
        while session_id in self.sessions:
            counter += 1
            session_id = f"{base_id}-{counter}"
        
        return session_id
    
    # ================================================================== Enhanced Session Creation
    
    async def create_session(self, request: SessionCreationRequest) -> ToolResult:
        """Create a new game session with enhanced validation and events."""
        try:
            # Check session limit
            if len(self.sessions) >= self._max_sessions:
                await self._emit_event(
                    EventType.ERROR_OCCURRED,
                    correlation_id=getattr(request, 'correlation_id', None),
                    error="session_limit_reached",
                    max_sessions=self._max_sessions
                )
                return create_error_result(
                    f"Maximum number of sessions ({self._max_sessions}) reached"
                )
            
            # Get and validate plugin
            try:
                plugin = self.plugin_registry.get(request.game_type)
            except ValueError as e:
                await self._emit_event(
                    EventType.ERROR_OCCURRED,
                    correlation_id=getattr(request, 'correlation_id', None),
                    error="invalid_game_type",
                    game_type=request.game_type
                )
                return create_error_result(str(e))
            
            # Validate game configuration
            try:
                full_config = {
                    "session_id": request.session_id,
                    "tags": request.tags,
                    **request.config
                }
                validated_config = plugin.validate_config(full_config)
            except Exception as e:
                await self._emit_event(
                    EventType.ERROR_OCCURRED,
                    correlation_id=getattr(request, 'correlation_id', None),
                    error="config_validation_failed",
                    game_type=request.game_type,
                    config=request.config
                )
                return create_error_result(f"Configuration validation failed: {str(e)}")
            
            # Generate session ID if not provided (enhanced format)
            session_id = request.session_id or self._generate_session_id(request.game_type)
            
            if session_id in self.sessions:
                await self._emit_event(
                    EventType.ERROR_OCCURRED,
                    session_id=session_id,
                    correlation_id=getattr(request, 'correlation_id', None),
                    error="session_exists"
                )
                return create_error_result(f"Session {session_id} already exists")
            
            # Create initial game state
            try:
                state = plugin.create_initial_state(session_id, validated_config)
            except Exception as e:
                logger.error(f"Error creating initial state for {request.game_type}: {e}")
                await self._emit_event(
                    EventType.ERROR_OCCURRED,
                    session_id=session_id,
                    correlation_id=getattr(request, 'correlation_id', None),
                    error="state_creation_failed",
                    game_type=request.game_type
                )
                return create_error_result(f"Failed to create game state: {str(e)}")
            
            # Create session
            session = GameSession(
                session_id=session_id,
                game_type=request.game_type,
                state=state,
                tags=request.tags
            )
            
            self.sessions[session_id] = session
            
            # Set as active if requested and no active session exists
            if request.auto_activate and self.active_session_id is None:
                self.active_session_id = session_id
            
            # Emit creation event if enabled
            if getattr(request, 'emit_events', True):
                await self._emit_event(
                    EventType.SESSION_CREATED,
                    session_id=session_id,
                    correlation_id=getattr(request, 'correlation_id', None),
                    game_type=request.game_type,
                    tags=request.tags,
                    auto_activated=request.auto_activate and self.active_session_id == session_id,
                    message=f"Created {request.game_type} session"
                )
            
            logger.info(f"Created {request.game_type} session: {session_id}")
            
            return create_success_result(
                message=f"Created {request.game_type} session: {session_id}",
                data={
                    "session_id": session_id,
                    "session_info": session.to_info(is_active_session=(session_id == self.active_session_id)).model_dump(),
                    "game_state": session.get_state_snapshot()
                }
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}")
            await self._emit_event(
                EventType.ERROR_OCCURRED,
                correlation_id=getattr(request, 'correlation_id', None),
                error="unexpected_error",
                exception=str(e)
            )
            return create_error_result(f"Internal error: {str(e)}")
    
    # ================================================================== Session Access
    
    def get_session(self, session_id: str = None) -> Optional[GameSession]:
        """Get session by ID or active session."""
        if session_id is None:
            session_id = self.active_session_id
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.touch()
            return session
        
        return None
    
    async def get_session_info(self, session_id: str = None) -> ToolResult:
        """Get detailed session information."""
        try:
            session = self.get_session(session_id)
            if not session:
                return create_error_result("Session not found")
            
            is_active = session.session_id == self.active_session_id
            plugin = self.plugin_registry.get(session.game_type)
            
            return create_success_result(
                message="Session info retrieved",
                data={
                    "session_info": session.to_info(is_active_session=is_active).model_dump(),
                    "game_state": session.get_state_snapshot(),
                    "plugin_info": plugin.get_game_info().model_dump(),
                    "session_age_seconds": session.get_age().total_seconds(),
                    "idle_time_seconds": session.get_idle_time().total_seconds(),
                    "config_schema": plugin.get_json_schema(),
                    "session_summary": session.to_summary()
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    # ================================================================== Enhanced Session Listing
    
    async def list_sessions(self, filter_criteria: SessionFilter = None) -> ToolResult:
        """List sessions with enhanced filtering and enum handling."""
        try:
            if filter_criteria is None:
                filter_criteria = SessionFilter()
            
            # Apply filters using the session's built-in filter method
            filtered_sessions = []
            for session in self.sessions.values():
                if session.matches_filter(
                    game_type=filter_criteria.game_type,
                    tags=filter_criteria.tags,
                    include_completed=filter_criteria.include_completed,
                    max_age_hours=filter_criteria.max_age_hours,
                    max_idle_hours=filter_criteria.max_idle_hours
                ):
                    filtered_sessions.append(session)
            
            # Convert to session info and sort
            session_infos = []
            for session in filtered_sessions:
                is_active = session.session_id == self.active_session_id
                info = session.to_info(is_active_session=is_active)
                session_infos.append(info)
            
            # Sort by last accessed (most recent first)
            session_infos.sort(key=lambda s: s.last_accessed, reverse=True)
            
            # Generate enhanced statistics
            stats = self._calculate_enhanced_stats()
            
            response = SessionListResponse(
                sessions=session_infos,
                total_count=len(self.sessions),
                filtered_count=len(session_infos),
                stats=stats,
                filter_applied=filter_criteria
            )
            
            return create_success_result(
                message=f"Found {len(session_infos)} sessions (of {len(self.sessions)} total)",
                data=response.model_dump()
            )
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    # ================================================================== Enhanced Session Management
    
    async def delete_session(self, session_id: str, emit_events: bool = True) -> ToolResult:
        """Delete a session with event emission."""
        try:
            if session_id not in self.sessions:
                return create_error_result("Session not found")
            
            session = self.sessions[session_id]
            game_type = session.game_type
            del self.sessions[session_id]
            
            # Update active session
            new_active = None
            if self.active_session_id == session_id:
                new_active = self._select_new_active_session()
                self.active_session_id = new_active
            
            # Emit deletion event
            if emit_events:
                await self._emit_event(
                    EventType.SESSION_DELETED,
                    session_id=session_id,
                    game_type=game_type,
                    new_active_session=new_active,
                    remaining_sessions=len(self.sessions),
                    message=f"Deleted {game_type} session"
                )
            
            logger.info(f"Deleted session: {session_id}")
            
            return create_success_result(
                message=f"Session {session_id} deleted",
                data={
                    "deleted_session": session_id,
                    "deleted_game_type": game_type,
                    "new_active_session": new_active,
                    "remaining_sessions": len(self.sessions)
                }
            )
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    async def set_active_session(self, session_id: str, emit_events: bool = True) -> ToolResult:
        """Set the active session with event emission."""
        try:
            if session_id not in self.sessions:
                return create_error_result("Session not found")
            
            old_active = self.active_session_id
            self.active_session_id = session_id
            
            # Touch the session
            self.sessions[session_id].touch()
            
            # Emit activation event
            if emit_events:
                await self._emit_event(
                    EventType.SESSION_ACTIVATED,
                    session_id=session_id,
                    previous_active=old_active,
                    message=f"Session {session_id} activated"
                )
            
            return create_success_result(
                message=f"Session {session_id} is now active",
                data={
                    "active_session": session_id,
                    "previous_active": old_active
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting active session: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    async def update_session_tags(self, session_id: str, tags: List[str]) -> ToolResult:
        """Update session tags."""
        try:
            session = self.get_session(session_id)
            if not session:
                return create_error_result("Session not found")
            
            # Update tags using the session's validation
            old_tags = session.tags.copy()
            session.tags = tags  # Pydantic will validate
            session.touch()
            
            return create_success_result(
                message=f"Updated tags for session {session_id}",
                data={
                    "session_id": session_id,
                    "old_tags": old_tags,
                    "new_tags": session.tags
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating session tags: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    # ================================================================== Enhanced Bulk Operations
    
    async def bulk_delete_sessions(self, session_ids: List[str], emit_events: bool = True) -> ToolResult:
        """Delete multiple sessions with enhanced event tracking."""
        start_time = time.time()
        event_id = str(uuid.uuid4()) if emit_events else None
        
        try:
            results = []
            successful = 0
            
            for session_id in session_ids:
                if session_id in self.sessions:
                    session = self.sessions[session_id]
                    del self.sessions[session_id]
                    
                    # Update active session if needed
                    if self.active_session_id == session_id:
                        self.active_session_id = self._select_new_active_session()
                    
                    results.append(SessionOperation(
                        operation_type="bulk_delete",  # Use string directly
                        session_id=session_id,
                        success=True,
                        message=f"Deleted {session.game_type} session",
                        details={"game_type": session.game_type},
                        event_id=event_id
                    ))
                    successful += 1
                    
                else:
                    results.append(SessionOperation(
                        operation_type="bulk_delete",  # Use string directly
                        session_id=session_id,
                        success=False,
                        message="Session not found",
                        event_id=event_id
                    ))
            
            duration_ms = (time.time() - start_time) * 1000
            
            bulk_result = SessionBulkResult(
                operation="bulk_delete",  # Use string directly
                total_requested=len(session_ids),
                successful=successful,
                failed=len(session_ids) - successful,
                results=results,
                duration_ms=duration_ms,
                event_id=event_id
            )
            
            # Emit bulk operation event
            if emit_events:
                await self._emit_event(
                    EventType.BULK_OPERATION,
                    operation="bulk_delete",
                    successful=successful,
                    failed=len(session_ids) - successful,
                    total_requested=len(session_ids),
                    duration_ms=duration_ms,
                    message=f"Bulk delete: {successful}/{len(session_ids)} successful"
                )
            
            return create_success_result(
                message=f"Bulk delete completed: {successful}/{len(session_ids)} successful",
                data=bulk_result.model_dump()
            )
            
        except Exception as e:
            logger.error(f"Error in bulk delete: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    async def bulk_tag_sessions(self, session_ids: List[str], tags: List[str]) -> ToolResult:
        """Add tags to multiple sessions."""
        start_time = time.time()
        
        try:
            results = []
            successful = 0
            
            for session_id in session_ids:
                if session_id in self.sessions:
                    try:
                        session = self.sessions[session_id]
                        old_tags = session.tags.copy()
                        
                        # Add new tags (avoiding duplicates)
                        for tag in tags:
                            session.add_tag(tag)
                        
                        results.append(SessionOperation(
                            operation_type="tag",  # Use string directly
                            session_id=session_id,
                            success=True,
                            message=f"Updated tags for {session.game_type} session",
                            details={
                                "old_tags": old_tags,
                                "new_tags": session.tags,
                                "added_tags": tags
                            }
                        ))
                        successful += 1
                        
                    except Exception as e:
                        results.append(SessionOperation(
                            operation_type="tag",  # Use string directly
                            session_id=session_id,
                            success=False,
                            message=f"Failed to update tags: {str(e)}"
                        ))
                else:
                    results.append(SessionOperation(
                        operation_type="tag",  # Use string directly
                        session_id=session_id,
                        success=False,
                        message="Session not found"
                    ))
            
            duration_ms = (time.time() - start_time) * 1000
            
            bulk_result = SessionBulkResult(
                operation="tag",  # Use string directly
                total_requested=len(session_ids),
                successful=successful,
                failed=len(session_ids) - successful,
                results=results,
                duration_ms=duration_ms
            )
            
            return create_success_result(
                message=f"Bulk tag operation completed: {successful}/{len(session_ids)} successful",
                data=bulk_result.model_dump()
            )
            
        except Exception as e:
            logger.error(f"Error in bulk tag operation: {e}")
            return create_error_result(f"Internal error: {str(e)}")
    
    # ================================================================== Enhanced Cleanup
    
    async def cleanup_sessions(self, criteria: CleanupCriteria = None) -> ToolResult:
        """Clean up sessions based on age and idle time."""
        start_time = time.time()
        
        try:
            if criteria is None:
                criteria = CleanupCriteria()
            
            sessions_to_delete = []
            
            for session_id, session in self.sessions.items():
                should_delete = False
                reason = ""
                
                # Don't delete active session if keep_active is True
                if criteria.keep_active and session_id == self.active_session_id:
                    continue
                
                # Check age
                if session.is_older_than(criteria.max_age_hours):
                    should_delete = True
                    reason = f"too old ({session.get_age_hours():.1f}h > {criteria.max_age_hours}h)"
                
                # Check idle time (skip completed games if keep_completed is True)
                elif not (session.is_completed() and criteria.keep_completed):
                    if session.is_idle_longer_than(criteria.max_idle_hours):
                        should_delete = True
                        reason = f"idle too long ({session.get_idle_hours():.1f}h > {criteria.max_idle_hours}h)"
                
                if should_delete:
                    sessions_to_delete.append({
                        "session_id": session_id,
                        "game_type": session.game_type,
                        "reason": reason,
                        "age_hours": session.get_age_hours(),
                        "idle_hours": session.get_idle_hours(),
                        "is_completed": session.is_completed(),
                        "tags": session.tags
                    })
            
            # Delete sessions (unless dry run)
            deleted_count = 0
            if not criteria.dry_run:
                for session_info in sessions_to_delete:
                    session_id = session_info["session_id"]
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                        deleted_count += 1
                        logger.info(f"Cleaned up session {session_id}: {session_info['reason']}")
                
                # Update active session if it was deleted
                if self.active_session_id not in self.sessions:
                    self.active_session_id = self._select_new_active_session()
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = CleanupResult(
                sessions_deleted=deleted_count,
                sessions_kept=len(self.sessions),
                deleted_sessions=sessions_to_delete,
                cleanup_criteria=criteria,
                dry_run=criteria.dry_run,
                duration_ms=duration_ms
            )
            
            action = "Would delete" if criteria.dry_run else "Deleted"
            return create_success_result(
                message=f"{action} {len(sessions_to_delete)} sessions",
                data=result.model_dump()
            )
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return create_error_result(f"Cleanup failed: {str(e)}")
    
    # ================================================================== Enhanced Statistics
    
    def _calculate_enhanced_stats(self) -> SessionStats:
        """Calculate comprehensive session statistics with enhanced data."""
        if not self.sessions:
            return SessionStats(
                total_sessions=0,
                active_session=None,
                sessions_by_type={},
                sessions_by_status={},
                completed_games=0,
                average_session_age_hours=0.0,
                oldest_session_hours=0.0,
                events_today=self._events_today
            )
        
        sessions_by_type = {}
        sessions_by_status = {}
        completed_count = 0
        total_age_hours = 0.0
        oldest_age_hours = 0.0
        
        for session in self.sessions.values():
            # Count by type
            game_type = session.game_type
            sessions_by_type[game_type] = sessions_by_type.get(game_type, 0) + 1
            
            # Determine status more accurately
            if session.is_completed():
                status = "completed"
                completed_count += 1
            elif session.is_stale():
                status = "stale"
            elif session.get_idle_hours() > 2:
                status = "idle"
            else:
                status = "active"
            
            sessions_by_status[status] = sessions_by_status.get(status, 0) + 1
            
            # Calculate ages
            age_hours = session.get_age_hours()
            total_age_hours += age_hours
            oldest_age_hours = max(oldest_age_hours, age_hours)
        
        average_age_hours = total_age_hours / len(self.sessions)
        
        return SessionStats(
            total_sessions=len(self.sessions),
            active_session=self.active_session_id,
            sessions_by_type=sessions_by_type,
            sessions_by_status=sessions_by_status,
            completed_games=completed_count,
            average_session_age_hours=average_age_hours,
            oldest_session_hours=oldest_age_hours,
            events_today=self._events_today
        )
    
    # Legacy method for backward compatibility
    def _calculate_stats(self) -> SessionStats:
        """Legacy method - calls enhanced stats."""
        return self._calculate_enhanced_stats()
    
    # ================================================================== Utility Methods
    
    def _select_new_active_session(self) -> Optional[str]:
        """Select a new active session (most recently accessed)."""
        if not self.sessions:
            return None
        
        # Sort by last accessed time (most recent first)
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda item: item[1].last_accessed,
            reverse=True
        )
        
        return sorted_sessions[0][0]
    
    # ================================================================== Query Methods
    
    def get_sessions_by_tag(self, tag: str) -> List[GameSession]:
        """Get all sessions with a specific tag."""
        return [session for session in self.sessions.values() if session.has_tag(tag)]
    
    def get_sessions_by_type(self, game_type: str) -> List[GameSession]:
        """Get all sessions of a specific game type."""
        return [session for session in self.sessions.values() if session.game_type == game_type]
    
    def get_completed_sessions(self) -> List[GameSession]:
        """Get all completed sessions."""
        return [session for session in self.sessions.values() if session.is_completed()]
    
    def get_active_sessions(self) -> List[GameSession]:
        """Get all non-completed sessions."""
        return [session for session in self.sessions.values() if session.is_active()]
    
    def get_recent_sessions(self, hours: float = 1.0) -> List[GameSession]:
        """Get sessions accessed within the specified hours."""
        return [session for session in self.sessions.values() if session.is_recent(hours)]
    
    def get_stale_sessions(self, hours: float = 24.0) -> List[GameSession]:
        """Get stale sessions (old and not recently accessed)."""
        return [session for session in self.sessions.values() if session.is_stale(hours)]
    
    # ================================================================== Enhanced Health & Monitoring
    
    def get_health_status(self) -> dict:
        """Get enhanced health status with event tracking."""
        stats = self._calculate_enhanced_stats()
        
        return {
            "status": "healthy" if len(self.sessions) < self._max_sessions * 0.9 else "warning",
            "total_sessions": stats.total_sessions,
            "max_sessions": self._max_sessions,
            "utilization_percent": (stats.total_sessions / self._max_sessions) * 100,
            "active_session": self.active_session_id,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "oldest_session_hours": stats.oldest_session_hours,
            "stale_sessions": len(self.get_stale_sessions()),
            "events_today": self._events_today,
            "event_handler_active": self.event_handler is not None
        }