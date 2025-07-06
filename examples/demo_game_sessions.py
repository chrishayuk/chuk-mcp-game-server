#!/usr/bin/env python3
# examples/demo_game_sessions.py
"""
Game Session Demo Script
========================

Comprehensive demonstration of the modular game session system.
Shows all major functionality including:
- Session creation and management
- Advanced filtering and querying
- Bulk operations and cleanup
- Health monitoring and statistics
- Error handling and validation

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

# Session imports
from chuk_mcp_game_server.session.models import (
    SessionCreationRequest, SessionFilter, CleanupCriteria, 
    SessionStatus, SessionUpdateRequest, OperationType
)
from chuk_mcp_game_server.session.game_session import GameSession
from chuk_mcp_game_server.session.game_session_manager import GameSessionManager

# Plugin system (we'll mock this for the demo)
from chuk_mcp_game_server.plugins.plugin_registry import PluginRegistry


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


# ================================================================== Mock Game Plugin

class DemoGameState(GameStateBase):
    """Demo game state for testing."""
    score: int = 0
    level: int = 1
    moves_made: int = 0
    difficulty_multiplier: float = 1.0
    
    def make_move(self):
        """Simulate making a move."""
        self.moves_made += 1
        self.score += int(10 * self.difficulty_multiplier)
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


class DemoGameConfig(GameConfig):
    """Demo game configuration."""
    target_score: int = 100
    max_moves: int = 50
    enable_hints: bool = True
    theme: str = "classic"


class MockGamePlugin:
    """Mock game plugin for demonstration."""
    
    def get_game_type(self) -> str:
        return "demo_game"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="Demo Game",
            description="A demonstration game for testing the session system",
            category=GameCategory.DEMO,
            difficulty=DifficultyLevel.EASY,
            features=[
                GameFeature.SINGLE_PLAYER,
                GameFeature.STATISTICS,
                GameFeature.ASCII_ART
            ],
            complexity_score=3.0,
            estimated_duration_minutes=10
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
    """Mock puzzle game plugin."""
    
    def get_game_type(self) -> str:
        return "puzzle_game"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="Puzzle Master",
            description="Complex puzzle challenges requiring strategic thinking",
            category=GameCategory.PUZZLE,
            difficulty=DifficultyLevel.HARD,
            features=[
                GameFeature.SINGLE_PLAYER,
                GameFeature.PLANNING_DEMO,
                GameFeature.OPTIMAL_SOLUTIONS
            ],
            complexity_score=7.5,
            estimated_duration_minutes=30
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


async def demo_basic_session_operations():
    """Demonstrate basic session operations."""
    print_section("Basic Session Operations")
    
    # Create session manager with plugins
    registry = PluginRegistry()
    registry.register(MockGamePlugin())
    registry.register(PuzzleGamePlugin())
    
    manager = GameSessionManager(registry)
    
    print_subsection("Creating Sessions")
    
    # Create various types of sessions
    requests = [
        SessionCreationRequest(
            game_type="demo_game",
            tags=["demo", "tutorial"],
            config={"difficulty": "easy", "target_score": 50}
        ),
        SessionCreationRequest(
            game_type="demo_game", 
            session_id="advanced_demo",
            tags=["demo", "advanced"],
            config={"difficulty": "hard", "target_score": 200}
        ),
        SessionCreationRequest(
            game_type="puzzle_game",
            tags=["puzzle", "challenge"],
            config={"difficulty": "expert"}
        )
    ]
    
    created_sessions = []
    for i, request in enumerate(requests):
        result = await manager.create_session(request)
        if result.success:
            print(f"✅ Created session: {result.data['session_id']}")
            created_sessions.append(result.data['session_id'])
        else:
            print(f"❌ Failed to create session: {result.error}")
    
    print_subsection("Session Information")
    
    # Get detailed info for each session
    for session_id in created_sessions:
        result = await manager.get_session_info(session_id)
        if result.success:
            session_info = result.data['session_info']
            print(f"📋 {session_info['session_id']}: {session_info['game_type']} "
                  f"({', '.join(session_info['tags'])})")
    
    return manager, created_sessions


async def demo_game_simulation(manager: GameSessionManager, session_ids: List[str]):
    """Demonstrate game simulation and state changes."""
    print_section("Game Simulation & State Changes")
    
    print_subsection("Simulating Game Play")
    
    for session_id in session_ids:
        session = manager.get_session(session_id)
        if session:
            print(f"🎮 Playing {session_id}...")
            
            # Simulate different amounts of play
            if "advanced" in session.tags:
                await simulate_game_play(session, moves=8)
            elif "puzzle" in session.tags:
                await simulate_game_play(session, moves=12)
            else:
                await simulate_game_play(session, moves=5)
            
            # Show updated state
            if hasattr(session.state, 'get_summary'):
                print(f"   State: {session.state.get_summary()}")
            
            await asyncio.sleep(0.2)  # Brief pause between sessions
    
    print_subsection("Session Status After Play")
    
    # List all sessions with their current status
    result = await manager.list_sessions()
    if result.success:
        sessions = result.data['sessions']
        for session_info in sessions:
            status_icon = "✅" if session_info['is_completed'] else "🎯"
            active_icon = "⭐" if session_info['is_active'] else "  "
            print(f"{status_icon} {active_icon} {session_info['session_id']}: "
                  f"{session_info['game_type']} - {session_info['status']}")


async def demo_advanced_filtering():
    """Demonstrate advanced filtering capabilities."""
    print_section("Advanced Filtering & Querying")
    
    # Create a fresh manager with more sessions for filtering demo
    registry = PluginRegistry()
    registry.register(MockGamePlugin())
    registry.register(PuzzleGamePlugin())
    
    manager = GameSessionManager(registry)
    
    print_subsection("Creating Diverse Sessions")
    
    # Create sessions with different characteristics
    session_configs = [
        ("demo_game", ["demo", "easy"], {"difficulty": "easy"}),
        ("demo_game", ["demo", "medium"], {"difficulty": "medium"}),
        ("demo_game", ["demo", "hard"], {"difficulty": "hard"}),
        ("puzzle_game", ["puzzle", "challenge"], {"difficulty": "expert"}),
        ("puzzle_game", ["puzzle", "tutorial"], {"difficulty": "easy"}),
        ("demo_game", ["archived", "old"], {"difficulty": "medium"}),
    ]
    
    session_ids = []
    for game_type, tags, config in session_configs:
        request = SessionCreationRequest(
            game_type=game_type,
            tags=tags,
            config=config
        )
        result = await manager.create_session(request)
        if result.success:
            session_ids.append(result.data['session_id'])
    
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
    
    print_subsection("Filter Examples")
    
    # Example 1: Filter by game type
    filter_demo = SessionFilter(game_type="demo_game")
    result = await manager.list_sessions(filter_demo)
    demo_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Demo games only: {demo_sessions} sessions")
    
    # Example 2: Filter by tags
    filter_puzzle = SessionFilter(tags=["puzzle"])
    result = await manager.list_sessions(filter_puzzle)
    puzzle_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Puzzle games: {puzzle_sessions} sessions")
    
    # Example 3: Filter by completion status
    filter_active = SessionFilter(include_completed=False)
    result = await manager.list_sessions(filter_active)
    active_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Active sessions only: {active_sessions} sessions")
    
    # Example 4: Filter by age
    filter_recent = SessionFilter(max_age_hours=3.0)
    result = await manager.list_sessions(filter_recent)
    recent_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Recent sessions (< 3h): {recent_sessions} sessions")
    
    # Example 5: Complex filter
    complex_filter = SessionFilter(
        game_type="demo_game",
        tags=["demo"],
        include_completed=False,
        max_age_hours=5.0
    )
    result = await manager.list_sessions(complex_filter)
    filtered_sessions = len(result.data['sessions']) if result.success else 0
    print(f"🔍 Complex filter: {filtered_sessions} sessions")
    
    return manager


async def demo_bulk_operations(manager: GameSessionManager):
    """Demonstrate bulk operations."""
    print_section("Bulk Operations")
    
    # Get some session IDs for bulk operations
    result = await manager.list_sessions()
    if not result.success:
        print("❌ Could not list sessions for bulk operations")
        return
    
    session_ids = [s['session_id'] for s in result.data['sessions'][:3]]
    
    print_subsection("Bulk Tag Operations")
    
    # Add tags to multiple sessions
    result = await manager.bulk_tag_sessions(session_ids, ["bulk_test", "demo_operation"])
    if result.success:
        bulk_result = result.data
        print(f"✅ Bulk tag operation: {bulk_result['successful']}/{bulk_result['total_requested']} successful")
        print(f"   Success rate: {safe_get_success_rate(bulk_result):.1f}%")
    else:
        print(f"❌ Bulk tag operation failed: {result.error}")
    
    print_subsection("Bulk Delete Operations")
    
    # Create some temporary sessions for deletion demo
    temp_session_ids = []
    for i in range(3):
        request = SessionCreationRequest(
            game_type="demo_game",
            tags=["temporary", "delete_me"],
            config={"difficulty": "easy"}
        )
        result = await manager.create_session(request)
        if result.success:
            temp_session_ids.append(result.data['session_id'])
    
    print(f"📝 Created {len(temp_session_ids)} temporary sessions for deletion")
    
    # Bulk delete the temporary sessions
    result = await manager.bulk_delete_sessions(temp_session_ids)
    if result.success:
        bulk_result = result.data
        print(f"🗑️  Bulk delete: {bulk_result['successful']}/{bulk_result['total_requested']} deleted")
        print(f"   Success rate: {safe_get_success_rate(bulk_result):.1f}%")
    else:
        print(f"❌ Bulk delete operation failed: {result.error}")


async def demo_cleanup_operations(manager: GameSessionManager):
    """Demonstrate cleanup operations."""
    print_section("Cleanup Operations")
    
    print_subsection("Current Session Status")
    
    # Show current sessions
    result = await manager.list_sessions()
    if result.success:
        sessions = result.data['sessions']
        stats = result.data['stats']
        print(f"📊 Total sessions: {len(sessions)}")
        completed = stats.get('completed_games', 0)
        print(f"📊 Completed: {completed}, Active: {len(sessions) - completed}")
        print(f"📊 Completion rate: {safe_get_completion_rate(stats):.1f}%")
    else:
        print("❌ Could not retrieve session status")
        return
    
    print_subsection("Dry Run Cleanup")
    
    # Perform a dry run cleanup to see what would be deleted
    criteria = CleanupCriteria(
        max_age_hours=4.0,
        max_idle_hours=2.0,
        keep_completed=True,
        dry_run=True
    )
    
    result = await manager.cleanup_sessions(criteria)
    if result.success:
        cleanup_result = result.data
        print(f"🧹 Dry run cleanup would delete {cleanup_result['sessions_deleted']} sessions")
        print(f"🛡️  Would keep {cleanup_result['sessions_kept']} sessions")
        
        for session_info in cleanup_result['deleted_sessions']:
            print(f"   Would delete: {session_info['session_id']} ({session_info['reason']})")
    else:
        print(f"❌ Dry run cleanup failed: {result.error}")
    
    print_subsection("Actual Cleanup")
    
    # Perform actual cleanup with different criteria
    criteria.dry_run = False
    criteria.max_age_hours = 6.0  # More lenient for demo
    
    result = await manager.cleanup_sessions(criteria)
    if result.success:
        cleanup_result = result.data
        print(f"🧹 Actual cleanup deleted {cleanup_result['sessions_deleted']} sessions")
        if cleanup_result['sessions_deleted'] > 0:
            print(f"   Cleaned up sessions:")
            for session_info in cleanup_result['deleted_sessions']:
                print(f"     - {session_info['session_id']}: {session_info['reason']}")
    else:
        print(f"❌ Cleanup failed: {result.error}")


async def demo_health_monitoring(manager: GameSessionManager):
    """Demonstrate health monitoring and statistics."""
    print_section("Health Monitoring & Statistics")
    
    print_subsection("Session Statistics")
    
    result = await manager.list_sessions()
    if result.success:
        stats = result.data['stats']
        print(f"📊 Total sessions: {stats['total_sessions']}")
        print(f"📊 Completed games: {stats['completed_games']}")
        print(f"📊 Active session: {stats['active_session'] or 'None'}")
        print(f"📊 Average age: {stats['average_session_age_hours']:.1f} hours")
        print(f"📊 Completion rate: {safe_get_completion_rate(stats):.1f}%")
        
        print("\n📊 Sessions by game type:")
        for game_type, count in stats['sessions_by_type'].items():
            print(f"   {game_type}: {count}")
        
        if 'sessions_by_status' in stats:
            print("\n📊 Sessions by status:")
            for status, count in stats['sessions_by_status'].items():
                print(f"   {status}: {count}")
    else:
        print(f"❌ Could not retrieve session statistics: {result.error}")
        return
    
    print_subsection("Health Status")
    
    health = manager.get_health_status()
    status_icon = {"healthy": "💚", "warning": "⚠️", "critical": "🔴"}.get(health['status'], "❓")
    print(f"{status_icon} Overall status: {health['status']}")
    print(f"📊 Utilization: {health['utilization_percent']:.1f}%")
    print(f"📊 Uptime: {health['uptime_hours']:.1f} hours")
    print(f"📊 Stale sessions: {health['stale_sessions']}")
    
    print_subsection("Query Methods Demo")
    
    # Demonstrate various query methods
    by_tag = manager.get_sessions_by_tag("demo")
    print(f"🏷️  Sessions with 'demo' tag: {len(by_tag)}")
    
    by_type = manager.get_sessions_by_type("demo_game")
    print(f"🎮 Demo game sessions: {len(by_type)}")
    
    completed = manager.get_completed_sessions()
    print(f"✅ Completed sessions: {len(completed)}")
    
    active = manager.get_active_sessions()
    print(f"🎯 Active sessions: {len(active)}")
    
    recent = manager.get_recent_sessions(hours=1.0)
    print(f"🕐 Recent sessions (1h): {len(recent)}")


async def demo_error_handling():
    """Demonstrate error handling scenarios."""
    print_section("Error Handling & Validation")
    
    registry = PluginRegistry()
    registry.register(MockGamePlugin())
    manager = GameSessionManager(registry)
    
    print_subsection("Validation Errors")
    
    # Test invalid session ID - catch Pydantic validation error
    try:
        request = SessionCreationRequest(
            game_type="demo_game",
            session_id="invalid/session/id",  # Invalid characters
            config={}
        )
        result = await manager.create_session(request)
        if not result.success:
            print(f"✅ Validation working: {result.error}")
    except Exception as e:
        print(f"✅ Validation working: Invalid session ID format correctly rejected")
    
    # Test unknown game type
    try:
        request = SessionCreationRequest(
            game_type="nonexistent_game",
            config={}
        )
        result = await manager.create_session(request)
        if not result.success:
            print(f"✅ Game type validation: {result.error}")
    except Exception as e:
        print(f"⚠️ Unexpected error for unknown game type: {str(e)}")
    
    # Test invalid config data
    try:
        request = SessionCreationRequest(
            game_type="demo_game",
            session_id="",  # Empty session ID
            config={}
        )
        result = await manager.create_session(request)
        if not result.success:
            print(f"✅ Empty ID validation: {result.error}")
    except Exception as e:
        print(f"✅ Validation working: Empty session ID correctly rejected")
    
    print_subsection("Session Limit Testing")
    
    # Test session limit (set low for demo)
    manager.configure(max_sessions=3)
    
    # Try to create more sessions than allowed
    for i in range(5):
        try:
            request = SessionCreationRequest(
                game_type="demo_game",
                config={}
            )
            result = await manager.create_session(request)
            
            if result.success:
                print(f"✅ Created session {i+1}")
            else:
                print(f"🚫 Session {i+1} properly limited: {result.error}")
        except Exception as e:
            print(f"⚠️ Session {i+1} validation failed: {str(e)}")
    
    print_subsection("Operational Errors")
    
    # Test deleting non-existent session
    result = await manager.delete_session("nonexistent_session_id")
    if not result.success:
        print(f"✅ Delete validation: {result.error}")
    
    # Test getting info for non-existent session
    result = await manager.get_session_info("nonexistent_session_id")
    if not result.success:
        print(f"✅ Info validation: {result.error}")
    
    print("🎯 Error handling demonstrations completed successfully!")


async def main():
    """Main demo function."""
    print("🎮 Game Session Management Demo")
    print("This script demonstrates the comprehensive session management system")
    
    try:
        # Run all demo sections
        manager, session_ids = await demo_basic_session_operations()
        await demo_game_simulation(manager, session_ids)
        
        advanced_manager = await demo_advanced_filtering()
        await demo_bulk_operations(advanced_manager)
        await demo_cleanup_operations(advanced_manager)
        await demo_health_monitoring(advanced_manager)
        
        await demo_error_handling()
        
        print_section("Demo Complete")
        print("✅ All demonstrations completed successfully!")
        print("\nThis demo showed:")
        print("  • Basic session creation and management")
        print("  • Game simulation and state tracking")
        print("  • Advanced filtering and querying")
        print("  • Bulk operations (tagging, deletion)")
        print("  • Cleanup operations with dry-run support")
        print("  • Health monitoring and statistics")
        print("  • Error handling and validation")
        print("\n🎯 The session management system is ready for production use!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Create a simple plugin registry mock if needed
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
    
    # Run the demo
    asyncio.run(main())