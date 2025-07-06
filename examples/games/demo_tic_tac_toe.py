#!/usr/bin/env python3
# examples/demo_tic_tac_toe.py
"""
Tic-Tac-Toe Game Demo Script
============================

Interactive demonstration of the Tic-Tac-Toe game plugin.
Shows all game functionality including:
- Game creation with different AI difficulty levels
- Interactive gameplay with move validation
- AI opponent with strategic play
- Game analysis and statistics
- ASCII art board visualization
- Win/draw detection

Run with: python demo_tic_tac_toe.py
"""

import asyncio
import random
from typing import List, Tuple, Optional

# Core framework imports
from chuk_mcp_game_server.core.models import (
    GameStateBase, GameConfig, GameInfo, GameCategory, DifficultyLevel, 
    GameFeature, create_success_result, create_error_result
)

# Session management
from chuk_mcp_game_server.session.models import (
    SessionCreationRequest, SessionFilter
)
from chuk_mcp_game_server.session.game_session_manager import GameSessionManager
from chuk_mcp_game_server.plugins.plugin_registry import PluginRegistry

# Import the tic-tac-toe game plugin
try:
    from games.tic_tac_toe import TicTacToePlugin, TicTacToeState, TicTacToeConfig, Player, GameResult
except ImportError:
    print("❌ Could not import tic-tac-toe game plugin")
    print("Make sure games/tic_tac_toe.py is available")
    exit(1)


# ================================================================== Demo Functions

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def print_board_with_coords():
    """Show board coordinate system."""
    print("📍 Board Coordinates:")
    print("   0   1   2")
    print("0    │   │   ")
    print("  ───┼───┼───")
    print("1    │   │   ")
    print("  ───┼───┼───")
    print("2    │   │   ")
    print("\n💡 Enter moves as 'row,col' (e.g., '1,2' for middle-right)")


async def demo_game_creation():
    """Demonstrate creating tic-tac-toe games with different configurations."""
    print_section("Tic-Tac-Toe Game Creation")
    
    # Create plugin registry and session manager
    registry = PluginRegistry()
    registry.register(TicTacToePlugin())
    manager = GameSessionManager(registry)
    
    print_subsection("Game Plugin Information")
    
    plugin = registry.get("tic_tac_toe")
    game_info = plugin.get_game_info()
    
    print(f"🎮 Game: {game_info.name}")
    print(f"📝 Description: {game_info.description}")
    print(f"📂 Category: {game_info.category}")
    print(f"⭐ Difficulty: {game_info.difficulty}")
    print(f"👥 Players: {game_info.min_players}-{game_info.max_players}")
    print(f"🎯 Complexity: {game_info.complexity_score}/10")
    print(f"⏱️ Duration: ~{game_info.estimated_duration_minutes} minutes")
    
    print_subsection("Creating Games with Different AI Levels")
    
    # Create games with different AI difficulties
    game_configs = [
        ("easy", "Human vs Easy AI", {"ai_difficulty": "easy", "player_x_human": True, "player_o_human": False}),
        ("medium", "Human vs Medium AI", {"ai_difficulty": "medium", "player_x_human": True, "player_o_human": False}),
        ("hard", "Human vs Hard AI", {"ai_difficulty": "hard", "player_x_human": True, "player_o_human": False}),
        ("pvp", "Player vs Player", {"player_x_human": True, "player_o_human": True})
    ]
    
    created_games = {}
    
    for game_id, description, config in game_configs:
        print(f"\n🎯 Creating {description}...")
        
        request = SessionCreationRequest(
            game_type="tic_tac_toe",
            session_id=f"ttt_{game_id}_demo",
            tags=["demo", "tic-tac-toe", game_id],
            config=config
        )
        
        result = await manager.create_session(request)
        if result.success:
            session_id = result.data['session_id']
            created_games[game_id] = session_id
            print(f"✅ Created: {session_id}")
            
            # Show game configuration
            session = manager.get_session(session_id)
            if session:
                state = session.state
                print(f"   👤 Player X: {'Human' if state.player_x_human else f'AI ({state.ai_difficulty})'}")
                print(f"   🤖 Player O: {'Human' if state.player_o_human else f'AI ({state.ai_difficulty})'}")
                print(f"   🎲 First player: {state.current_player}")
        else:
            print(f"❌ Failed: {result.error}")
    
    return manager, created_games


async def demo_interactive_gameplay(manager: GameSessionManager, session_id: str):
    """Demonstrate interactive gameplay."""
    print_section("Interactive Tic-Tac-Toe Gameplay")
    
    session = manager.get_session(session_id)
    if not session:
        print("❌ Session not found")
        return
    
    state: TicTacToeState = session.state
    print(f"🎮 Playing session: {session_id}")
    print(f"👤 You are playing as: {Player.X.value}")
    print(f"🤖 AI difficulty: {state.ai_difficulty}")
    
    print_board_with_coords()
    
    move_count = 0
    max_moves = 9  # Prevent infinite games in demo
    
    while not state.is_completed and move_count < max_moves:
        print(f"\n{'='*40}")
        print(state.get_board_display())
        print(f"{'='*40}")
        
        if state.current_player == Player.X.value:
            # Human player's turn
            print(f"\n🎯 Your turn (Player {state.current_player})!")
            
            # For demo purposes, simulate human moves
            available_moves = [(r, c) for r in range(3) for c in range(3) 
                             if state.board[r][c] == Player.EMPTY.value]
            
            if available_moves:
                # Simulate human input with some strategy
                move = simulate_human_move(state, available_moves)
                row, col = move
                
                print(f"👤 Making move: ({row}, {col})")
                move_result = state.make_move(row, col)
                
                if move_result["success"]:
                    print(f"✅ Move successful!")
                    if move_result["game_over"]:
                        break
                else:
                    print(f"❌ Invalid move: {move_result['error']}")
                    continue
            
        else:
            # AI player's turn
            print(f"\n🤖 AI turn (Player {state.current_player})...")
            
            ai_move = state.get_ai_move()
            if ai_move:
                row, col = ai_move
                print(f"🤖 AI chooses: ({row}, {col})")
                
                move_result = state.make_move(row, col)
                if move_result["success"]:
                    print(f"✅ AI move successful!")
                    if move_result["game_over"]:
                        break
                else:
                    print(f"❌ AI move failed: {move_result['error']}")
            else:
                print("🤖 AI cannot find a move!")
                break
        
        move_count += 1
        await asyncio.sleep(0.5)  # Brief pause for readability
    
    # Show final game state
    print(f"\n{'='*40}")
    print("🏁 GAME OVER!")
    print(state.get_board_display())
    print(f"{'='*40}")
    
    # Show game result
    if state.game_result == GameResult.X_WINS.value:
        print("🎉 Player X (You) wins!")
    elif state.game_result == GameResult.O_WINS.value:
        print("🤖 Player O (AI) wins!")
    elif state.game_result == GameResult.DRAW.value:
        print("🤝 It's a draw!")
    else:
        print("🎮 Game incomplete")
    
    # Show game analysis
    analysis = state.get_game_analysis()
    print(f"\n📊 Game Analysis:")
    print(f"   🎯 Moves played: {analysis['moves_analyzed']}")
    print(f"   ⏱️ Game length: {analysis['game_length']} moves")
    print(f"   👥 Players: {analysis['players']}")
    
    if 'final_result' in analysis:
        print(f"   🏆 Result: {analysis['final_result']}")
        if 'winner' in analysis and analysis['winner']:
            print(f"   🥇 Winner: {analysis['winner']}")


def simulate_human_move(state: TicTacToeState, available_moves: List[Tuple[int, int]]) -> Tuple[int, int]:
    """Simulate a human move with some basic strategy."""
    
    # Check for winning move
    for row, col in available_moves:
        # Temporarily make the move
        state.board[row][col] = Player.X.value
        if check_winner(state.board) == Player.X.value:
            state.board[row][col] = Player.EMPTY.value  # Undo
            return (row, col)
        state.board[row][col] = Player.EMPTY.value  # Undo
    
    # Check for blocking opponent's winning move
    for row, col in available_moves:
        # Temporarily make opponent's move
        state.board[row][col] = Player.O.value
        if check_winner(state.board) == Player.O.value:
            state.board[row][col] = Player.EMPTY.value  # Undo
            return (row, col)
        state.board[row][col] = Player.EMPTY.value  # Undo
    
    # Take center if available
    if (1, 1) in available_moves:
        return (1, 1)
    
    # Take corners
    corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
    available_corners = [move for move in available_moves if move in corners]
    if available_corners:
        return random.choice(available_corners)
    
    # Take any available move
    return random.choice(available_moves)


def check_winner(board: List[List[str]]) -> Optional[str]:
    """Check if there's a winner on the board."""
    lines = [
        # Rows
        [(0,0), (0,1), (0,2)], [(1,0), (1,1), (1,2)], [(2,0), (2,1), (2,2)],
        # Columns
        [(0,0), (1,0), (2,0)], [(0,1), (1,1), (2,1)], [(0,2), (1,2), (2,2)],
        # Diagonals
        [(0,0), (1,1), (2,2)], [(0,2), (1,1), (2,0)]
    ]
    
    for line in lines:
        values = [board[r][c] for r, c in line]
        if len(set(values)) == 1 and values[0] != Player.EMPTY.value:
            return values[0]
    
    return None


async def demo_ai_comparison():
    """Demonstrate different AI difficulty levels."""
    print_section("AI Difficulty Comparison")
    
    registry = PluginRegistry()
    registry.register(TicTacToePlugin())
    manager = GameSessionManager(registry)
    
    difficulties = ["easy", "medium", "hard"]
    results = {}
    
    for difficulty in difficulties:
        print_subsection(f"Testing {difficulty.title()} AI")
        
        wins = 0
        draws = 0
        losses = 0
        total_games = 5
        
        for game_num in range(total_games):
            print(f"🎮 Game {game_num + 1}/{total_games} vs {difficulty} AI...")
            
            # Create game
            request = SessionCreationRequest(
                game_type="tic_tac_toe",
                session_id=f"ai_test_{difficulty}_{game_num}",
                config={
                    "ai_difficulty": difficulty,
                    "player_x_human": True,
                    "player_o_human": False,
                    "first_player": "X"
                }
            )
            
            result = await manager.create_session(request)
            if not result.success:
                print(f"❌ Failed to create game: {result.error}")
                continue
            
            session = manager.get_session(result.data['session_id'])
            state: TicTacToeState = session.state
            
            # Simulate a quick game
            move_count = 0
            while not state.is_completed and move_count < 9:
                if state.current_player == Player.X.value:
                    # Simulate human move (random for speed)
                    available = [(r, c) for r in range(3) for c in range(3) 
                               if state.board[r][c] == Player.EMPTY.value]
                    if available:
                        row, col = random.choice(available)
                        state.make_move(row, col)
                else:
                    # AI move
                    ai_move = state.get_ai_move()
                    if ai_move:
                        state.make_move(ai_move[0], ai_move[1])
                    else:
                        break
                
                move_count += 1
            
            # Record result
            if state.game_result == GameResult.X_WINS.value:
                wins += 1
                result_icon = "🎉"
            elif state.game_result == GameResult.O_WINS.value:
                losses += 1
                result_icon = "🤖"
            else:
                draws += 1
                result_icon = "🤝"
            
            print(f"   {result_icon} {state.game_result.replace('_', ' ').title()}")
        
        results[difficulty] = {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "total": total_games
        }
        
        win_rate = (wins / total_games) * 100
        print(f"\n📊 {difficulty.title()} AI Results:")
        print(f"   🎉 Human wins: {wins}/{total_games} ({win_rate:.1f}%)")
        print(f"   🤖 AI wins: {losses}/{total_games} ({(losses/total_games)*100:.1f}%)")
        print(f"   🤝 Draws: {draws}/{total_games} ({(draws/total_games)*100:.1f}%)")
    
    print_subsection("AI Difficulty Summary")
    for difficulty in difficulties:
        stats = results[difficulty]
        human_win_rate = (stats["wins"] / stats["total"]) * 100
        if human_win_rate > 60:
            strength = "🟢 Easy to beat"
        elif human_win_rate > 30:
            strength = "🟡 Moderate challenge"
        else:
            strength = "🔴 Very challenging"
        
        print(f"🤖 {difficulty.title()} AI: {strength} (Human wins: {human_win_rate:.1f}%)")


async def demo_game_analysis():
    """Demonstrate game analysis features."""
    print_section("Game Analysis & Statistics")
    
    registry = PluginRegistry()
    registry.register(TicTacToePlugin())
    manager = GameSessionManager(registry)
    
    print_subsection("Creating Analyzed Game")
    
    # Create a game for analysis
    request = SessionCreationRequest(
        game_type="tic_tac_toe",
        session_id="analysis_demo",
        config={
            "ai_difficulty": "medium",
            "player_x_human": True,
            "player_o_human": False
        }
    )
    
    result = await manager.create_session(request)
    if not result.success:
        print(f"❌ Failed to create game: {result.error}")
        return
    
    session = manager.get_session(result.data['session_id'])
    state: TicTacToeState = session.state
    
    print("🎮 Playing a complete game for analysis...")
    
    # Play a predetermined game sequence for consistent analysis
    moves = [(1, 1), (0, 0), (0, 1), (2, 2), (2, 1)]  # X wins
    
    for i, (row, col) in enumerate(moves):
        player = Player.X.value if i % 2 == 0 else Player.O.value
        print(f"Move {i+1}: Player {player} -> ({row}, {col})")
        
        move_result = state.make_move(row, col, player)
        if not move_result["success"]:
            print(f"❌ Move failed: {move_result['error']}")
            break
        
        if move_result["game_over"]:
            print(f"🏁 Game over! {move_result['result']}")
            break
    
    print("\n" + state.get_board_display())
    
    print_subsection("Detailed Game Analysis")
    
    analysis = state.get_game_analysis()
    
    print(f"📊 Game Statistics:")
    print(f"   🎯 Total moves: {analysis['moves_analyzed']}")
    print(f"   ⏱️ Game length: {analysis['game_length']} moves")
    print(f"   🏆 Final result: {analysis.get('final_result', 'In progress')}")
    
    if 'winner' in analysis and analysis['winner']:
        print(f"   🥇 Winner: Player {analysis['winner']}")
    
    if 'victory_type' in analysis:
        print(f"   🎯 Victory type: {analysis['victory_type']}")
    
    if 'game_duration' in analysis:
        print(f"   ⚡ Duration: {analysis['game_duration']}")
    
    print(f"\n👥 Player Configuration:")
    for player, player_type in analysis['players'].items():
        print(f"   Player {player}: {player_type}")
    
    print_subsection("Move History Analysis")
    
    print(f"📝 Move sequence ({len(state.move_history)} moves):")
    for i, move in enumerate(state.move_history):
        print(f"   {i+1}. Player {move['player']}: ({move['row']}, {move['col']})")


async def demo_session_management():
    """Demonstrate session management features for tic-tac-toe games."""
    print_section("Tic-Tac-Toe Session Management")
    
    registry = PluginRegistry()
    registry.register(TicTacToePlugin())
    manager = GameSessionManager(registry)
    
    print_subsection("Creating Multiple Game Sessions")
    
    # Create several tic-tac-toe sessions
    game_types = [
        ("beginner", {"ai_difficulty": "easy", "first_player": "X"}),
        ("intermediate", {"ai_difficulty": "medium", "first_player": "O"}),
        ("expert", {"ai_difficulty": "hard", "first_player": "X"}),
        ("multiplayer", {"player_x_human": True, "player_o_human": True})
    ]
    
    session_ids = []
    for game_name, config in game_types:
        request = SessionCreationRequest(
            game_type="tic_tac_toe",
            session_id=f"ttt_{game_name}",
            tags=["tic-tac-toe", game_name, "demo"],
            config=config
        )
        
        result = await manager.create_session(request)
        if result.success:
            session_ids.append(result.data['session_id'])
            print(f"✅ Created {game_name}: {result.data['session_id']}")
    
    print_subsection("Session Filtering and Queries")
    
    # Filter tic-tac-toe sessions only
    ttt_filter = SessionFilter(game_type="tic_tac_toe")
    result = await manager.list_sessions(ttt_filter)
    
    if result.success:
        sessions = result.data['sessions']
        print(f"🔍 Found {len(sessions)} tic-tac-toe sessions:")
        
        for session_info in sessions:
            print(f"   📋 {session_info['session_id']}")
            print(f"      🏷️ Tags: {', '.join(session_info['tags'])}")
            print(f"      📊 Status: {session_info['status']}")
            print(f"      ⭐ Active: {'Yes' if session_info['is_active'] else 'No'}")
    
    print_subsection("Session Statistics")
    
    result = await manager.list_sessions()
    if result.success:
        stats = result.data['stats']
        print(f"📊 Session Statistics:")
        print(f"   🎮 Total sessions: {stats['total_sessions']}")
        print(f"   ✅ Completed games: {stats['completed_games']}")
        print(f"   📊 Completion rate: {stats.get('completion_rate', 0):.1f}%")
        
        if 'sessions_by_type' in stats:
            for game_type, count in stats['sessions_by_type'].items():
                print(f"   🎲 {game_type}: {count} sessions")


async def main():
    """Main demo function."""
    print("🎮 Tic-Tac-Toe Game Demo")
    print("=" * 50)
    print("This demo showcases the tic-tac-toe game plugin with:")
    print("• Multiple AI difficulty levels")
    print("• Interactive gameplay simulation")
    print("• Game analysis and statistics")
    print("• Session management features")
    print("• ASCII art board visualization")
    
    try:
        # Run all demo sections
        manager, created_games = await demo_game_creation()
        
        # Pick a game to play interactively
        if "medium" in created_games:
            await demo_interactive_gameplay(manager, created_games["medium"])
        
        await demo_ai_comparison()
        await demo_game_analysis()
        await demo_session_management()
        
        print_section("Demo Complete")
        print("✅ Tic-Tac-Toe demo completed successfully!")
        print("\n🎯 Features demonstrated:")
        print("  • 🎮 Game creation with configurable AI")
        print("  • 🤖 Multiple AI difficulty levels")
        print("  • 🎯 Interactive gameplay simulation")
        print("  • 📊 Game analysis and move tracking")
        print("  • 🎨 ASCII art board visualization")
        print("  • 📋 Session management and filtering")
        print("  • 📈 Performance statistics")
        
        print("\n🚀 The tic-tac-toe game is ready for interactive play!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())