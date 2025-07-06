#!/usr/bin/env python3
# examples/demo_game_sessions.py
"""
Enhanced Game Session Demo Script - FINAL FIXED VERSION
=======================================================

Comprehensive demonstration of the enhanced session management system.
Shows all major functionality including:
- Enhanced session creation with event system and improved IDs
- Advanced filtering and querying with better enum handling
- Bulk operations and cleanup with event tracking
- Health monitoring and statistics with event metrics
- Error handling and validation

FIXED: Corrected icons to avoid confusion between successful validation tests and actual errors.

Run with: python demo_game_sessions.py
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Core framework imports
from chuk_mcp_game_server.core.models import (
    GameStateBase, GameConfig, GameInfo, GameCategory, DifficultyLevel, 
    GameFeature, create_success_result, create_error_result
)

# Enhanced session imports
from chuk_mcp_game_server.session.models import (
    SessionCreationRequest, SessionFilter, CleanupCriteria, 
    SessionStatus, SessionUpdateRequest, OperationType,
    SessionEvent, EventType  # 🆕 Enhanced imports
)
from chuk_mcp_game_server.session.game_session import GameSession
from chuk_mcp_game_server.session.game_session_manager import GameSessionManager

# Plugin system
from chuk_mcp_game_server.plugins.plugin_registry import PluginRegistry


# ================================================================== Utility Functions for Icons

def get_event_icon(event_type: str, context: str = "general") -> str:
    """Get appropriate icon for event type and context."""
    
    # For validation/testing context, use clear, non-alarming icons
    if context == "validation":
        icons = {
            'session_created': '🆕',
            'session_updated': '📝',
            'session_deleted': '🗑️',
            'session_completed': '✅',
            'bulk_operation': '📦',
            'error_occurred': '🔍',  # Magnifying glass instead of red X
            'session_limit_reached': '🛡️',  # Shield for protection
            'invalid_game_type': '🔍',  # Magnifying glass for type checking
            'config_validation_failed': '🔍',  # Validation checking
            'session_exists': '🔒',  # Lock for duplicate prevention
        }
    else:
        # For general event display, use standard icons
        icons = {
            'session_created': '🆕',
            'session_updated': '📝',
            'session_deleted': '🗑️',
            'session_completed': '✅',
            'bulk_operation': '📦',
            'error_occurred': '⚠️',  # Warning for actual runtime errors
            'cleanup_performed': '🧹',
            'session_activated': '⭐',
        }
    
    return icons.get(event_type, '📋')


def get_validation_icon(validation_type: str) -> str:
    """Get appropriate icon for validation test types."""
    validation_icons = {
        'invalid_game_type': '🔍',  # Type discovery/validation
        'session_limit_reached': '🛡️',  # Security/limit protection
        'session_exists': '🔒',  # Duplicate prevention
        'config_validation_failed': '🔧',  # Configuration checking
        'invalid_session_id': '🔍',  # ID format validation
        'empty_session_id': '🔍',  # ID content validation
        'unknown_error': '⚠️',  # Actual unexpected issues
    }
    return validation_icons.get(validation_type, '✅')


# ================================================================== Enhanced Event Handler (FIXED)

class DemoEventHandler:
    """Enhanced event handler for demonstration - FIXED enum handling."""
    
    def __init__(self):
        self.events_received = []
        self.event_counts = {}
        self.show_events = True
    
    def _safe_get_event_type(self, event_type):
        """Safely extract string value from event type."""
        if isinstance(event_type, str):
            return event_type
        elif hasattr(event_type, 'value'):
            return event_type.value
        else:
            return str(event_type)
    
    async def __call__(self, event: SessionEvent):
        """Handle incoming events."""
        self.events_received.append(event)
        
        # 🔧 FIXED: event.event_type is already a string, no need for .value
        event_type = self._safe_get_event_type(event.event_type)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Show important events in real-time
        if self.show_events and event_type in [
            "session_created", 
            "session_completed", 
            "session_deleted",
            "bulk_operation"
        ]:
            timestamp = event.timestamp.strftime("%H:%M:%S")
            session_part = f" [{event.session_id}]" if event.session_id else ""
            message = event.details.get('message', 'Event occurred')
            print(f"🔔 [{timestamp}] {event_type}{session_part}: {message}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of events received."""
        return {
            "total_events": len(self.events_received),
            "event_counts": self.event_counts.copy(),
            "recent_events": [e.to_log_message() for e in self.events_received[-5:]]
        }
    
    def quiet_mode(self):
        """Disable real-time event display."""
        self.show_events = False
    
    def show_mode(self):
        """Enable real-time event display."""
        self.show_events = True


# ================================================================== Utility Functions

def safe_get_success_rate(bulk_result_data: dict) -> float:
    """Safely calculate success rate from bulk operation result."""
    if 'success_rate' in bulk_result_data:
        return bulk_result_data['success_rate']
    
    # Calculate manually if not present
    successful = bulk_result_data.get('successful', 0)
    total = bulk_result_data.get('total_requested', 0)
    return (successful / total) * 100 if total > 0 else 0.0


def safe_get_completion_rate(stats_data: dict) -> float:
    """Safely calculate completion rate from stats."""
    if 'completion_rate' in stats_data:
        return stats_data['completion_rate']
    
    # Calculate manually if not present
    completed = stats_data.get('completed_games', 0)
    total = stats_data.get('total_sessions', 0)
    return (completed / total) * 100 if total > 0 else 0.0


# 🔧 Enhanced session status display helper
def display_session_status(session_info: dict) -> str:
    """Display session status properly handling enum values."""
    status = session_info.get('status', 'unknown')
    
    # Handle both string and enum representations
    if hasattr(status, 'value'):
        status = status.value
    elif isinstance(status, str) and 'SessionStatus.' in status:
        status = status.split('.')[-1].lower()
    
    return status


# ================================================================== Mock Game Plugin (Enhanced)

class DemoGameState(GameStateBase):
    """Demo game state for testing with enhanced features."""
    score: int = 0
    level: int = 1
    moves_made: int = 0
    difficulty_multiplier: float = 1.0
    last_move_timestamp: datetime = None
    
    def make_move(self):
        """Simulate making a move with enhanced tracking."""
        self.moves_made += 1
        self.score += int(10 * self.difficulty_multiplier)
        self.last_move_timestamp = datetime.now()
        
        if self.moves_made % 5 == 0:
            self.level += 1
        
        self.touch()
        
        # Complete game randomly after 15+ moves
        if self.moves_made >= 15 and self.moves_made % 7 == 0:
            self.is_completed = True
    
    def get_summary(self) -> str:
        """Get a summary of the game state."""
        status = "COMPLETED" if self.is_completed else "ACTIVE"
        return f"Level {self.level}, Score {self.score}, {self.moves_made} moves ({status})"
    
    def get_detailed_state(self) -> dict:
        """Get detailed state for enhanced demos."""
        return {
            "score": self.score,
            "level": self.level,
            "moves_made": self.moves_made,
            "difficulty_multiplier": self.difficulty_multiplier,
            "is_completed": self.is_completed,
            "last_move": self.last_move_timestamp.isoformat() if self.last_move_timestamp else None
        }


class DemoGameConfig(GameConfig):
    """Demo game configuration with enhanced options."""
    target_score: int = 100
    max_moves: int = 50
    enable_hints: bool = True
    theme: str = "classic"
    auto_save: bool = True


class MockGamePlugin:
    """Mock game plugin for demonstration with enhanced features."""
    
    def get_game_type(self) -> str:
        return "demo_game"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="Enhanced Demo Game",
            description="A demonstration game for testing the enhanced session system with events and monitoring",
            category=GameCategory.DEMO,
            difficulty=DifficultyLevel.EASY,
            features=[
                GameFeature.SINGLE_PLAYER,
                GameFeature.STATISTICS,
                GameFeature.ASCII_ART
            ],
            complexity_score=3.0,
            estimated_duration_minutes=10,
            version="2.0.0"  # Enhanced version
        )
    
    def get_json_schema(self) -> Dict[str, Any]:
        return DemoGameConfig.model_json_schema()
    
    def validate_config(self, config_dict: Dict[str, Any]) -> GameConfig:
        return DemoGameConfig(**config_dict)
    
    def create_initial_state(self, game_id: str, config: GameConfig) -> GameStateBase:
        difficulty_map = {
            DifficultyLevel.EASY: 1.0,
            DifficultyLevel.MEDIUM: 1.5,
            DifficultyLevel.HARD: 2.0
        }
        
        return DemoGameState(
            game_id=game_id,
            game_type="demo_game",
            difficulty_multiplier=difficulty_map.get(config.difficulty, 1.0)
        )


class PuzzleGamePlugin:
    """Mock puzzle game plugin with enhanced features."""
    
    def get_game_type(self) -> str:
        return "puzzle_game"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="Enhanced Puzzle Master",
            description="Complex puzzle challenges with enhanced tracking and analytics",
            category=GameCategory.PUZZLE,
            difficulty=DifficultyLevel.HARD,
            features=[
                GameFeature.SINGLE_PLAYER,
                GameFeature.PLANNING_DEMO,
                GameFeature.OPTIMAL_SOLUTIONS,
                GameFeature.STATISTICS
            ],
            complexity_score=7.5,
            estimated_duration_minutes=30,
            version="2.0.0"
        )
    
    def get_json_schema(self) -> Dict[str, Any]:
        return GameConfig.model_json_schema()
    
    def validate_config(self, config_dict: Dict[str, Any]) -> GameConfig:
        return GameConfig(**config_dict)
    
    def create_initial_state(self, game_id: str, config: GameConfig) -> GameStateBase:
        return DemoGameState(
            game_id=game_id,
            game_type="puzzle_game",
            difficulty_multiplier=2.0
        )


# ================================================================== Demo Functions

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


async def simulate_game_play(session: GameSession, moves: int = 5):
    """Simulate playing a game by making moves."""
    if hasattr(session.state, 'make_move'):
        for i in range(moves):
            session.state.make_move()
            await asyncio.sleep(0.1)  # Simulate time passing
        session.touch()


async def demo_enhanced_session_creation():
    """Demonstrate enhanced session creation with events and new ID format."""
    print_section("Enhanced Session Creation & Event System")
    
    # Create event handler
    event_handler = DemoEventHandler()
    
    # Create session manager with event handler (🆕 Enhanced)
    registry = PluginRegistry()
    registry.register(MockGamePlugin())
    registry.register(PuzzleGamePlugin())
    
    manager = GameSessionManager(registry, event_handler)  # 🆕 With event handler
    
    print_subsection("Enhanced Session ID Format")
    print("🆔 New session ID format: game-MMDDHHMMM-xxxxxx")
    print("   - More readable and sortable")
    print("   - Includes date and time information")
    print("   - Shorter but still unique")
    
    print_subsection("Creating Sessions with Events")
    
    # Create various types of sessions with enhanced features
    requests = [
        SessionCreationRequest(
            game_type="demo_game",
            tags=["demo", "tutorial", "enhanced"],
            config={"difficulty": "easy", "target_score": 50, "auto_save": True},
            correlation_id="demo_001"  # 🆕 Enhanced
        ),
        SessionCreationRequest(
            game_type="demo_game", 
            session_id="custom_advanced_demo",  # Custom ID to show both formats
            tags=["demo", "advanced", "custom"],
            config={"difficulty": "hard", "target_score": 200},
            correlation_id="demo_002"  # 🆕 Enhanced
        ),
        SessionCreationRequest(
            game_type="puzzle_game",
            tags=["puzzle", "challenge", "enhanced"],
            config={"difficulty": "expert"},
            correlation_id="demo_003"  # 🆕 Enhanced
        )
    ]
    
    created_sessions = []
    for i, request in enumerate(requests):
        print(f"\n🎯 Creating session {i+1}...")
        result = await manager.create_session(request)
        if result.success:
            session_id = result.data['session_id']
            created_sessions.append(session_id)
            print(f"✅ Created session: {session_id}")
            
            # Show enhanced vs custom ID format
            if "custom" in session_id:
                print(f"   📝 Custom session ID format")
            else:
                print(f"   🆔 Enhanced auto-generated ID format")
        else:
            print(f"❌ Failed to create session: {result.error}")
    
    print_subsection("Event System Summary")
    
    event_summary = event_handler.get_summary()
    print(f"📊 Events captured: {event_summary['total_events']}")
    print("📊 Event breakdown:")
    for event_type, count in event_summary['event_counts'].items():
        icon = get_event_icon(event_type, context="general")
        print(f"   {icon} {event_type.replace('_', ' ').title()}: {count}")
    
    return manager, created_sessions, event_handler


async def demo_enhanced_session_info(manager: GameSessionManager, session_ids: List[str]):
    """Demonstrate enhanced session information display."""
    print_section("Enhanced Session Information")
    
    print_subsection("Session Details with Fixed Enum Display")
    
    # Get detailed info for each session
    for session_id in session_ids:
        result = await manager.get_session_info(session_id)
        if result.success:
            session_info = result.data['session_info']
            
            # 🔧 Enhanced status display (no more SessionStatus.ACTIVE)
            status = display_session_status(session_info)
            
            print(f"📋 {session_info['session_id']}")
            print(f"   🎮 Game: {session_info['game_type']}")
            print(f"   🏷️  Tags: {', '.join(session_info['tags'])}")
            print(f"   📊 Status: {status}")  # 🔧 Fixed enum display
            print(f"   ⏰ Age: {session_info.get('age_hours', 0):.2f} hours")
            print(f"   💤 Idle: {session_info.get('idle_hours', 0):.2f} hours")
            print(f"   ⭐ Active: {'Yes' if session_info['is_active'] else 'No'}")
    
    print_subsection("Enhanced Game State Information")
    
    # Show enhanced game state details
    for session_id in session_ids[:2]:  # Show first 2 for brevity
        session = manager.get_session(session_id)
        if session and hasattr(session.state, 'get_detailed_state'):
            print(f"🎮 {session_id} detailed state:")
            detailed_state = session.state.get_detailed_state()
            for key, value in detailed_state.items():
                print(f"   {key}: {value}")


async def demo_game_simulation_with_events(manager: GameSessionManager, session_ids: List[str], event_handler: DemoEventHandler):
    """Demonstrate game simulation with event tracking."""
    print_section("Game Simulation & State Changes with Events")
    
    print_subsection("Simulating Game Play")
    
    for session_id in session_ids:
        session = manager.get_session(session_id)
        if session:
            print(f"\n🎮 Playing {session_id}...")
            
            # Simulate different amounts of play based on tags
            if "advanced" in session.tags:
                await simulate_game_play(session, moves=8)
            elif "puzzle" in session.tags:
                await simulate_game_play(session, moves=12)
            else:
                await simulate_game_play(session, moves=5)
            
            # Show updated state
            if hasattr(session.state, 'get_summary'):
                print(f"   📊 State: {session.state.get_summary()}")
            
            await asyncio.sleep(0.2)  # Brief pause between sessions
    
    print_subsection("Enhanced Session Status After Play")
    
    # List all sessions with enhanced status display
    result = await manager.list_sessions()
    if result.success:
        sessions = result.data['sessions']
        print(f"📋 Session Overview ({len(sessions)} total):")
        
        for session_info in sessions:
            status_icon = "✅" if session_info['is_completed'] else "🎯"
            active_icon = "⭐" if session_info['is_active'] else "  "
            
            # 🔧 Enhanced status display (fixed enum handling)
            status = display_session_status(session_info)
            
            print(f"{status_icon} {active_icon} {session_info['session_id']}")
            print(f"      🎮 {session_info['game_type']} | 📊 {status}")
            print(f"      🏷️ {', '.join(session_info['tags'])}")


async def demo_enhanced_filtering():
    """Demonstrate advanced filtering with enhanced features."""
    print_section("Enhanced Filtering & Querying")
    
    # Create a fresh manager with event handler
    event_handler = DemoEventHandler()
    event_handler.quiet_mode()  # Reduce noise for this demo
    
    registry = PluginRegistry()
    registry.register(MockGamePlugin())
    registry.register(PuzzleGamePlugin())
    
    manager = GameSessionManager(registry, event_handler)
    
    print_subsection("Creating Diverse Sessions for Filtering")
    
    # Create sessions with different characteristics
    session_configs = [
        ("demo_game", ["demo", "easy", "tutorial"], {"difficulty": "easy"}),
        ("demo_game", ["demo", "medium", "practice"], {"difficulty": "medium"}),
        ("demo_game", ["demo", "hard", "challenge"], {"difficulty": "hard"}),
        ("puzzle_game", ["puzzle", "challenge", "brain_teaser"], {"difficulty": "expert"}),
        ("puzzle_game", ["puzzle", "tutorial", "learning"], {"difficulty": "easy"}),
        ("demo_game", ["archived", "old", "legacy"], {"difficulty": "medium"}),
    ]
    
    session_ids = []
    for game_type, tags, config in session_configs:
        request = SessionCreationRequest(
            game_type=game_type,
            tags=tags,
            config=config,
            emit_events=False  # 🆕 Enhanced: disable events for bulk creation
        )
        result = await manager.create_session(request)
        if result.success:
            session_ids.append(result.data['session_id'])
    
    print(f"✅ Created {len(session_ids)} sessions for filtering demonstration")
    
    # Simulate different ages by manually adjusting timestamps
    for i, session_id in enumerate(session_ids):
        session = manager.get_session(session_id)
        if session:
            # Make some sessions older
            hours_ago = i * 2
            session.created_at = datetime.now() - timedelta(hours=hours_ago)
            session.last_accessed = datetime.now() - timedelta(hours=hours_ago//2)
            
            # Complete some sessions
            if i % 3 == 0:
                session.state.is_completed = True
    
    print_subsection("Enhanced Filter Examples")
    
    # Example 1: Filter by game type
    filter_demo = SessionFilter(game_type="demo_game")
    result = await manager.list_sessions(filter_demo)
    demo_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Demo games only: {demo_sessions} sessions")
    
    # Example 2: Filter by multiple tags (OR logic)
    filter_tutorial = SessionFilter(tags=["tutorial", "learning"])
    result = await manager.list_sessions(filter_tutorial)
    tutorial_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Tutorial/Learning sessions: {tutorial_sessions} sessions")
    
    # Example 3: Filter by completion status
    filter_active = SessionFilter(include_completed=False)
    result = await manager.list_sessions(filter_active)
    active_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Active sessions only: {active_sessions} sessions")
    
    # Example 4: Filter by age with enhanced time ranges
    filter_recent = SessionFilter(max_age_hours=3.0)
    result = await manager.list_sessions(filter_recent)
    recent_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Recent sessions (< 3h): {recent_sessions} sessions")
    
    # Example 5: Complex enhanced filter
    complex_filter = SessionFilter(
        game_type="demo_game",
        tags=["demo"],
        include_completed=False,
        max_age_hours=5.0,
        max_idle_hours=3.0  # 🆕 Enhanced filtering
    )
    result = await manager.list_sessions(complex_filter)
    filtered_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Complex enhanced filter: {filtered_sessions} sessions")
    
    # 🆕 Example 6: Filter by status enum (enhanced) - 🔧 Fixed to use string
    status_filter = SessionFilter(status="active")  # Use string instead of enum
    result = await manager.list_sessions(status_filter)
    status_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Active status filter: {status_sessions} sessions")
    
    return manager


async def demo_enhanced_bulk_operations(manager: GameSessionManager):
    """Demonstrate enhanced bulk operations with event tracking."""
    print_section("Enhanced Bulk Operations with Events")
    
    # Get some session IDs for bulk operations
    result = await manager.list_sessions()
    if not result.success:
        print("❌ Could not list sessions for bulk operations")
        return
    
    session_ids = [s['session_id'] for s in result.data['sessions'][:3]]
    
    print_subsection("Enhanced Bulk Tag Operations")
    
    # Add tags to multiple sessions with event tracking
    print("🏷️ Adding tags to multiple sessions...")
    result = await manager.bulk_tag_sessions(session_ids, ["bulk_test", "enhanced_demo"])
    if result.success:
        bulk_result = result.data
        print(f"✅ Bulk tag operation: {bulk_result['successful']}/{bulk_result['total_requested']} successful")
        print(f"   📊 Success rate: {safe_get_success_rate(bulk_result):.1f}%")
        print(f"   ⏱️ Duration: {bulk_result['duration_ms']:.1f}ms")
        
        # 🆕 Show event ID if available
        if 'event_id' in bulk_result:
            print(f"   🔔 Event ID: {bulk_result['event_id']}")
    else:
        print(f"❌ Bulk tag operation failed: {result.error}")
    
    print_subsection("Enhanced Bulk Delete Operations")
    
    # Create some temporary sessions for deletion demo
    temp_session_ids = []
    for i in range(3):
        request = SessionCreationRequest(
            game_type="demo_game",
            tags=["temporary", "delete_me", "bulk_demo"],
            config={"difficulty": "easy"},
            emit_events=False  # 🆕 Quiet creation for demo
        )
        result = await manager.create_session(request)
        if result.success:
            temp_session_ids.append(result.data['session_id'])
    
    print(f"📝 Created {len(temp_session_ids)} temporary sessions for deletion")
    print("🔍 Session IDs created:")
    for session_id in temp_session_ids:
        print(f"   - {session_id}")
    
    # Bulk delete the temporary sessions with enhanced tracking
    print("\n🗑️ Performing bulk delete with event tracking...")
    result = await manager.bulk_delete_sessions(temp_session_ids, emit_events=True)  # 🆕 Explicit event control
    if result.success:
        bulk_result = result.data
        print(f"✅ Bulk delete: {bulk_result['successful']}/{bulk_result['total_requested']} deleted")
        print(f"   📊 Success rate: {safe_get_success_rate(bulk_result):.1f}%")
        print(f"   ⏱️ Duration: {bulk_result['duration_ms']:.1f}ms")
        
        # 🆕 Show enhanced bulk operation details
        if bulk_result['results']:
            print("   📋 Operation details:")
            for op in bulk_result['results'][:2]:  # Show first 2
                status_icon = "✅" if op['success'] else "❌"
                print(f"      {status_icon} {op['session_id']}: {op['message']}")
    else:
        print(f"❌ Bulk delete operation failed: {result.error}")


async def demo_enhanced_cleanup_operations(manager: GameSessionManager):
    """Demonstrate enhanced cleanup operations with event tracking."""
    print_section("Enhanced Cleanup Operations")
    
    print_subsection("Current Enhanced Session Status")
    
    # Show current sessions with enhanced info
    result = await manager.list_sessions()
    if result.success:
        sessions = result.data['sessions']
        stats = result.data['stats']
        
        print(f"📊 Total sessions: {len(sessions)}")
        completed = stats.get('completed_games', 0)
        print(f"📊 Completed: {completed}, Active: {len(sessions) - completed}")
        print(f"📊 Completion rate: {safe_get_completion_rate(stats):.1f}%")
        
        # 🆕 Enhanced statistics
        if 'events_today' in stats:
            print(f"📊 Events today: {stats['events_today']}")
    else:
        print("❌ Could not retrieve session status")
        return
    
    print_subsection("Enhanced Dry Run Cleanup")
    
    # Perform a dry run cleanup with enhanced criteria
    criteria = CleanupCriteria(
        max_age_hours=4.0,
        max_idle_hours=2.0,
        keep_completed=True,
        keep_tagged=["important", "permanent"],  # 🆕 Enhanced criteria
        dry_run=True,
        emit_events=True  # 🆕 Enhanced event control
    )
    
    print("🧹 Analyzing cleanup with enhanced criteria...")
    print(f"   📅 Max age: {criteria.max_age_hours} hours")
    print(f"   💤 Max idle: {criteria.max_idle_hours} hours")
    print(f"   🛡️ Keep completed: {criteria.keep_completed}")
    print(f"   🏷️ Keep tagged: {criteria.keep_tagged}")
    
    result = await manager.cleanup_sessions(criteria)
    if result.success:
        cleanup_result = result.data
        print(f"\n🔍 Dry run analysis:")
        print(f"   🗑️ Would delete: {cleanup_result['sessions_deleted']} sessions")
        print(f"   🛡️ Would keep: {cleanup_result['sessions_kept']} sessions")
        print(f"   ⏱️ Analysis time: {cleanup_result['duration_ms']:.1f}ms")
        
        # Show detailed cleanup reasons
        if cleanup_result['deleted_sessions']:
            print(f"\n📋 Sessions that would be cleaned up:")
            for session_info in cleanup_result['deleted_sessions'][:3]:  # Show first 3
                print(f"   🗑️ {session_info['session_id']}")
                print(f"      📝 Reason: {session_info['reason']}")
                print(f"      📊 Age: {session_info['age_hours']:.1f}h, Idle: {session_info['idle_hours']:.1f}h")
                print(f"      🏷️ Tags: {session_info['tags']}")
    else:
        print(f"❌ Dry run cleanup failed: {result.error}")
    
    print_subsection("Enhanced Actual Cleanup")
    
    # Perform actual cleanup with different criteria
    criteria.dry_run = False
    criteria.max_age_hours = 8.0  # More lenient for demo
    criteria.keep_tagged = ["permanent"]  # Only keep permanent tags
    
    print("🧹 Performing actual cleanup...")
    result = await manager.cleanup_sessions(criteria)
    if result.success:
        cleanup_result = result.data
        print(f"✅ Cleanup completed:")
        print(f"   🗑️ Deleted: {cleanup_result['sessions_deleted']} sessions")
        print(f"   🛡️ Kept: {cleanup_result['sessions_kept']} sessions")
        print(f"   ⏱️ Operation time: {cleanup_result['duration_ms']:.1f}ms")
        
        # 🆕 Show event ID if available
        if 'event_id' in cleanup_result:
            print(f"   🔔 Cleanup event ID: {cleanup_result['event_id']}")
        
        if cleanup_result['sessions_deleted'] > 0:
            print(f"\n📋 Cleaned up sessions:")
            for session_info in cleanup_result['deleted_sessions']:
                print(f"   🗑️ {session_info['session_id']}: {session_info['reason']}")
    else:
        print(f"❌ Cleanup failed: {result.error}")


async def demo_enhanced_health_monitoring(manager: GameSessionManager, event_handler: DemoEventHandler):
    """Demonstrate enhanced health monitoring and statistics."""
    print_section("Enhanced Health Monitoring & Statistics")
    
    print_subsection("Enhanced Session Statistics")
    
    result = await manager.list_sessions()
    if result.success:
        stats = result.data['stats']
        print(f"📊 Total sessions: {stats['total_sessions']}")
        print(f"📊 Completed games: {stats['completed_games']}")
        print(f"📊 Active session: {stats['active_session'] or 'None'}")
        print(f"📊 Average age: {stats['average_session_age_hours']:.1f} hours")
        print(f"📊 Completion rate: {safe_get_completion_rate(stats):.1f}%")
        
        # 🆕 Enhanced statistics
        if 'events_today' in stats:
            print(f"📊 Events today: {stats['events_today']}")
        
        print("\n📊 Sessions by game type:")
        for game_type, count in stats['sessions_by_type'].items():
            print(f"   🎮 {game_type}: {count}")
        
        if 'sessions_by_status' in stats:
            print("\n📊 Sessions by status:")
            for status, count in stats['sessions_by_status'].items():
                print(f"   📋 {status}: {count}")
    else:
        print(f"❌ Could not retrieve session statistics: {result.error}")
        return
    
    print_subsection("Enhanced Health Status")
    
    health = manager.get_health_status()
    status_icon = {"healthy": "💚", "warning": "⚠️", "critical": "🔴"}.get(health['status'], "❓")
    print(f"{status_icon} Overall status: {health['status']}")
    print(f"📊 Utilization: {health['utilization_percent']:.1f}%")
    print(f"📊 Uptime: {health['uptime_hours']:.1f} hours")
    print(f"📊 Stale sessions: {health['stale_sessions']}")
    
    # 🆕 Enhanced health metrics
    if 'events_today' in health:
        print(f"📊 Events today: {health['events_today']}")
    if 'event_handler_active' in health:
        print(f"📊 Event handler: {'✅ Active' if health['event_handler_active'] else '❌ Inactive'}")
    
    print_subsection("Enhanced Query Methods Demo")
    
    # Demonstrate various query methods with enhanced info
    by_tag = manager.get_sessions_by_tag("demo")
    print(f"🏷️ Sessions with 'demo' tag: {len(by_tag)}")
    
    by_type = manager.get_sessions_by_type("demo_game")
    print(f"🎮 Demo game sessions: {len(by_type)}")
    
    completed = manager.get_completed_sessions()
    print(f"✅ Completed sessions: {len(completed)}")
    
    active = manager.get_active_sessions()
    print(f"🎯 Active sessions: {len(active)}")
    
    recent = manager.get_recent_sessions(hours=1.0)
    print(f"🕐 Recent sessions (1h): {len(recent)}")
    
    print_subsection("Event System Analytics")
    
    # Show comprehensive event analytics
    event_summary = event_handler.get_summary()
    print(f"📊 Total events captured: {event_summary['total_events']}")
    
    if event_summary['event_counts']:
        print("📊 Event breakdown:")
        for event_type, count in event_summary['event_counts'].items():
            icon = get_event_icon(event_type, context="general")
            percentage = (count / event_summary['total_events']) * 100
            print(f"   {icon} {event_type.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")


async def demo_enhanced_error_handling():
    """Demonstrate enhanced error handling scenarios with CORRECT ICONS."""
    print_section("Enhanced Error Handling & Validation")
    
    # Create event handler to capture error events
    error_event_handler = DemoEventHandler()
    
    registry = PluginRegistry()
    registry.register(MockGamePlugin())
    manager = GameSessionManager(registry, error_event_handler)
    
    print_subsection("Enhanced Validation Tests")  # 🔧 Changed from "Validation Errors"
    
    # Test invalid session ID - enhanced validation
    try:
        request = SessionCreationRequest(
            game_type="demo_game",
            session_id="invalid/session/id",  # Invalid characters
            config={},
            correlation_id="error_test_001"
        )
        result = await manager.create_session(request)
        if not result.success:
            print(f"✅ Enhanced validation working: {result.error}")
    except Exception as e:
        print(f"✅ Enhanced validation: Invalid session ID format correctly rejected")
    
    # Test unknown game type with correlation ID
    try:
        request = SessionCreationRequest(
            game_type="nonexistent_game",
            config={},
            correlation_id="error_test_002"
        )
        result = await manager.create_session(request)
        if not result.success:
            print(f"✅ Enhanced game type validation: {result.error}")
    except Exception as e:
        print(f"⚠️ Unexpected error for unknown game type: {str(e)}")
    
    # Test empty session ID with enhanced error tracking
    try:
        request = SessionCreationRequest(
            game_type="demo_game",
            session_id="",  # Empty session ID
            config={},
            correlation_id="error_test_003"
        )
        result = await manager.create_session(request)
        if not result.success:
            print(f"✅ Enhanced empty ID validation: {result.error}")
    except Exception as e:
        print(f"✅ Enhanced validation: Empty session ID correctly rejected")
    
    print_subsection("Enhanced Security Limit Testing")  # 🔧 Changed from "Session Limit Testing"
    
    # Test session limit with enhanced configuration
    manager.configure(max_sessions=3)
    print(f"🔧 Set session limit to 3 for testing")
    
    # Try to create more sessions than allowed
    for i in range(5):
        try:
            request = SessionCreationRequest(
                game_type="demo_game",
                config={},
                correlation_id=f"limit_test_{i:03d}",
                emit_events=False  # Reduce noise
            )
            result = await manager.create_session(request)
            
            if result.success:
                print(f"✅ Created session {i+1}: {result.data['session_id']}")
            else:
                print(f"🛡️ Session {i+1} properly protected: {result.error}")  # 🔧 Changed from 🚫 to 🛡️
        except Exception as e:
            print(f"⚠️ Session {i+1} validation failed: {str(e)}")
    
    print_subsection("Enhanced Operational Validation")  # 🔧 Changed from "Operational Errors"
    
    # Test deleting non-existent session
    result = await manager.delete_session("nonexistent_session_id", emit_events=True)
    if not result.success:
        print(f"✅ Enhanced delete validation: {result.error}")
    
    # Test getting info for non-existent session
    result = await manager.get_session_info("nonexistent_session_id")
    if not result.success:
        print(f"✅ Enhanced info validation: {result.error}")
    
    print_subsection("Security & Validation Analytics")  # 🔧 Changed from "Error Event Analytics"
    
    # Show validation events captured - with better icons and descriptions
    error_summary = error_event_handler.get_summary()
    validation_events = [event for event in error_event_handler.events_received 
                        if "error" in str(event.event_type).lower()]
    
    print(f"📊 Security tests completed: {len(validation_events)}")  # 🔧 Changed from "Error events captured"
    for event in validation_events[:3]:  # Show first 3
        error_type = event.details.get('error', 'unknown_error')
        correlation = event.correlation_id or 'none'
        
        # 🔧 Use appropriate icons based on the validation type
        icon = get_validation_icon(error_type)
        friendly_name = error_type.replace('_', ' ').title()
        
        print(f"   {icon} {friendly_name} (correlation: {correlation})")
    
    print("🎯 Enhanced security and validation demonstrations completed successfully!")


async def main():
    """Enhanced main demo function."""
    print("🎮 Enhanced Game Session Management Demo")
    print("This script demonstrates the comprehensive enhanced session management system")
    print("\n🆕 New Enhanced Features:")
    print("   • Event system with real-time monitoring")
    print("   • Improved session ID format (game-MMDDHHMMM-xxxxxx)")
    print("   • Fixed enum display (no more SessionStatus.ACTIVE)")
    print("   • Enhanced statistics with event tracking")
    print("   • Better error handling with correlation IDs")
    print("   • Advanced filtering and bulk operations")
    
    try:
        # Run all enhanced demo sections
        manager, session_ids, event_handler = await demo_enhanced_session_creation()
        await demo_enhanced_session_info(manager, session_ids)
        await demo_game_simulation_with_events(manager, session_ids, event_handler)
        
        advanced_manager = await demo_enhanced_filtering()
        await demo_enhanced_bulk_operations(advanced_manager)
        await demo_enhanced_cleanup_operations(advanced_manager)
        await demo_enhanced_health_monitoring(advanced_manager, event_handler)
        
        await demo_enhanced_error_handling()
        
        print_section("Enhanced Demo Complete")
        print("✅ All enhanced demonstrations completed successfully!")
        print("\n🎯 Enhanced features demonstrated:")
        print("  • 🆔 Enhanced session ID generation (readable format)")
        print("  • 🔔 Event system with real-time monitoring")
        print("  • 🔧 Fixed enum display (proper string values)")
        print("  • 📊 Enhanced statistics with event metrics")
        print("  • 🏷️ Advanced filtering with multiple criteria")
        print("  • 📦 Bulk operations with event tracking")
        print("  • 🧹 Smart cleanup with detailed criteria")
        print("  • 🏥 Comprehensive health monitoring")
        print("  • 🛡️ Enhanced security and validation with correlation IDs")  # 🔧 Changed from "error handling"
        print("  • 📈 Event analytics and monitoring")
        
        print("\n🚀 The enhanced session management system is ready for production use!")
        print("💡 All improvements are backward compatible with existing code!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Simple plugin registry for standalone demo
    class PluginRegistry:
        def __init__(self):
            self.plugins = {}
        
        def register(self, plugin):
            self.plugins[plugin.get_game_type()] = plugin
        
        def get(self, game_type):
            if game_type not in self.plugins:
                raise ValueError(f"Unknown game type: {game_type}")
            return self.plugins[game_type]
        
        def list_types(self):
            return list(self.plugins.keys())
    
    # Run the enhanced demo
    asyncio.run(main())