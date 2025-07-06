# games/tic_tac_toe.py
"""
Tic-Tac-Toe Game Plugin
======================

Classic 3x3 tic-tac-toe game with AI opponent and game analysis.
Demonstrates turn-based gameplay, win condition checking, and AI strategies.
"""

from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from pydantic import Field, field_validator
import random

from chuk_mcp_game_server.core import (
    GameStateBase, GameConfig, GameInfo, GameCategory, 
    DifficultyLevel, GameFeature
)
from chuk_mcp_game_server.plugins import GamePlugin


class Player(str, Enum):
    """Player enumeration."""
    X = "X"
    O = "O"
    EMPTY = " "


class GameResult(str, Enum):
    """Game result enumeration."""
    X_WINS = "X_WINS"
    O_WINS = "O_WINS"
    DRAW = "DRAW"
    IN_PROGRESS = "IN_PROGRESS"


class TicTacToeState(GameStateBase):
    """Tic-tac-toe game state."""
    
    # 3x3 board represented as list of lists
    board: List[List[str]] = Field(
        default_factory=lambda: [[Player.EMPTY.value for _ in range(3)] for _ in range(3)],
        description="3x3 game board"
    )
    current_player: str = Field(default=Player.X.value, description="Current player's turn")
    moves_made: int = Field(default=0, description="Number of moves made")
    game_result: str = Field(default=GameResult.IN_PROGRESS.value, description="Current game result")
    winner: Optional[str] = Field(None, description="Winner if game is complete")
    winning_line: List[Tuple[int, int]] = Field(default_factory=list, description="Winning line coordinates")
    player_x_human: bool = Field(default=True, description="Whether player X is human")
    player_o_human: bool = Field(default=False, description="Whether player O is human")
    ai_difficulty: str = Field(default="medium", description="AI difficulty level")
    move_history: List[Dict[str, Any]] = Field(default_factory=list, description="History of moves")
    
    @field_validator('board')
    @classmethod
    def validate_board(cls, v):
        """Validate board structure."""
        if len(v) != 3 or any(len(row) != 3 for row in v):
            raise ValueError("Board must be 3x3")
        
        for row in v:
            for cell in row:
                if cell not in [Player.X.value, Player.O.value, Player.EMPTY.value]:
                    raise ValueError(f"Invalid cell value: {cell}")
        
        return v
    
    def get_board_display(self) -> str:
        """Get ASCII art representation of the board."""
        lines = []
        lines.append("   0   1   2")
        for i, row in enumerate(self.board):
            line = f"{i}  {row[0]} │ {row[1]} │ {row[2]} "
            lines.append(line)
            if i < 2:
                lines.append("  ───┼───┼───")
        
        lines.append(f"\nCurrent player: {self.current_player}")
        lines.append(f"Moves made: {self.moves_made}")
        
        if self.game_result != GameResult.IN_PROGRESS.value:
            if self.winner:
                lines.append(f"🎉 Winner: {self.winner}!")
            else:
                lines.append("🤝 Game is a draw!")
        
        return "\n".join(lines)
    
    def make_move(self, row: int, col: int, player: str = None) -> Dict[str, Any]:
        """Make a move on the board."""
        if player is None:
            player = self.current_player
        
        # Validate move
        if self.is_completed:
            return {"success": False, "error": "Game is already complete"}
        
        if not (0 <= row <= 2 and 0 <= col <= 2):
            return {"success": False, "error": "Invalid coordinates"}
        
        if self.board[row][col] != Player.EMPTY.value:
            return {"success": False, "error": "Cell is already occupied"}
        
        if player != self.current_player:
            return {"success": False, "error": f"It's {self.current_player}'s turn"}
        
        # Make the move
        self.board[row][col] = player
        self.moves_made += 1
        
        # Record move in history
        move_record = {
            "move_number": self.moves_made,
            "player": player,
            "row": row,
            "col": col,
            "timestamp": self.last_updated.isoformat()
        }
        self.move_history.append(move_record)
        
        # Check for win or draw
        result = self._check_game_result()
        
        if result["game_over"]:
            self.game_result = result["result"]
            self.winner = result.get("winner")
            self.winning_line = result.get("winning_line", [])
            self.is_completed = True
        else:
            # Switch players
            self.current_player = Player.O.value if player == Player.X.value else Player.X.value
        
        self.touch()
        
        return {
            "success": True,
            "move": {"row": row, "col": col, "player": player},
            "game_over": result["game_over"],
            "result": self.game_result,
            "winner": self.winner,
            "next_player": self.current_player if not result["game_over"] else None
        }
    
    def get_ai_move(self) -> Optional[Tuple[int, int]]:
        """Get AI move based on difficulty level."""
        empty_cells = [(r, c) for r in range(3) for c in range(3) 
                      if self.board[r][c] == Player.EMPTY.value]
        
        if not empty_cells:
            return None
        
        if self.ai_difficulty == "easy":
            return random.choice(empty_cells)
        
        elif self.ai_difficulty == "medium":
            # 70% optimal, 30% random
            if random.random() < 0.7:
                return self._get_optimal_move() or random.choice(empty_cells)
            else:
                return random.choice(empty_cells)
        
        else:  # hard
            return self._get_optimal_move() or random.choice(empty_cells)
    
    def _get_optimal_move(self) -> Optional[Tuple[int, int]]:
        """Get optimal move using minimax algorithm."""
        def minimax(board, depth, is_maximizing, alpha=-float('inf'), beta=float('inf')):
            result = self._evaluate_board(board)
            
            if result is not None:
                return result
            
            if is_maximizing:
                max_eval = -float('inf')
                for r in range(3):
                    for c in range(3):
                        if board[r][c] == Player.EMPTY.value:
                            board[r][c] = self.current_player
                            eval_score = minimax(board, depth + 1, False, alpha, beta)
                            board[r][c] = Player.EMPTY.value
                            max_eval = max(max_eval, eval_score)
                            alpha = max(alpha, eval_score)
                            if beta <= alpha:
                                break
                return max_eval
            else:
                min_eval = float('inf')
                opponent = Player.O.value if self.current_player == Player.X.value else Player.X.value
                for r in range(3):
                    for c in range(3):
                        if board[r][c] == Player.EMPTY.value:
                            board[r][c] = opponent
                            eval_score = minimax(board, depth + 1, True, alpha, beta)
                            board[r][c] = Player.EMPTY.value
                            min_eval = min(min_eval, eval_score)
                            beta = min(beta, eval_score)
                            if beta <= alpha:
                                break
                return min_eval
        
        best_move = None
        best_value = -float('inf')
        
        # Create a copy of the board for analysis
        board_copy = [row[:] for row in self.board]
        
        for r in range(3):
            for c in range(3):
                if board_copy[r][c] == Player.EMPTY.value:
                    board_copy[r][c] = self.current_player
                    move_value = minimax(board_copy, 0, False)
                    board_copy[r][c] = Player.EMPTY.value
                    
                    if move_value > best_value:
                        best_value = move_value
                        best_move = (r, c)
        
        return best_move
    
    def _evaluate_board(self, board) -> Optional[int]:
        """Evaluate board position for minimax."""
        # Check all winning conditions
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
            if values == [self.current_player] * 3:
                return 10  # AI wins
            elif len(set(values)) == 1 and values[0] != Player.EMPTY.value:
                return -10  # Opponent wins
        
        # Check for draw
        if all(board[r][c] != Player.EMPTY.value for r in range(3) for c in range(3)):
            return 0
        
        return None  # Game continues
    
    def _check_game_result(self) -> Dict[str, Any]:
        """Check if game is over and determine result."""
        # Check all possible winning lines
        lines = [
            # Rows
            [(0,0), (0,1), (0,2)], [(1,0), (1,1), (1,2)], [(2,0), (2,1), (2,2)],
            # Columns
            [(0,0), (1,0), (2,0)], [(0,1), (1,1), (2,1)], [(0,2), (1,2), (2,2)],
            # Diagonals
            [(0,0), (1,1), (2,2)], [(0,2), (1,1), (2,0)]
        ]
        
        for line in lines:
            values = [self.board[r][c] for r, c in line]
            if len(set(values)) == 1 and values[0] != Player.EMPTY.value:
                winner = values[0]
                result = GameResult.X_WINS.value if winner == Player.X.value else GameResult.O_WINS.value
                return {
                    "game_over": True,
                    "result": result,
                    "winner": winner,
                    "winning_line": line
                }
        
        # Check for draw
        if all(self.board[r][c] != Player.EMPTY.value for r in range(3) for c in range(3)):
            return {
                "game_over": True,
                "result": GameResult.DRAW.value,
                "winner": None
            }
        
        return {"game_over": False}
    
    def get_game_analysis(self) -> Dict[str, Any]:
        """Get analysis of the current game."""
        analysis = {
            "moves_analyzed": len(self.move_history),
            "game_length": self.moves_made,
            "players": {
                "X": "Human" if self.player_x_human else f"AI ({self.ai_difficulty})",
                "O": "Human" if self.player_o_human else f"AI ({self.ai_difficulty})"
            }
        }
        
        if self.is_completed:
            analysis["final_result"] = self.game_result
            analysis["winner"] = self.winner
            analysis["game_duration"] = "Quick" if self.moves_made <= 6 else "Extended"
            
            if self.winner:
                analysis["victory_type"] = "Decisive" if len(self.winning_line) == 3 else "Strategic"
        
        return analysis


class TicTacToeConfig(GameConfig):
    """Tic-tac-toe game configuration."""
    player_x_human: bool = Field(default=True, description="Whether player X is human")
    player_o_human: bool = Field(default=False, description="Whether player O is human") 
    ai_difficulty: str = Field(default="medium", description="AI difficulty: easy, medium, hard")
    first_player: str = Field(default="X", description="Which player goes first")
    
    @field_validator('ai_difficulty')
    @classmethod
    def validate_ai_difficulty(cls, v):
        if v not in ["easy", "medium", "hard"]:
            raise ValueError("AI difficulty must be easy, medium, or hard")
        return v
    
    @field_validator('first_player')
    @classmethod
    def validate_first_player(cls, v):
        if v not in ["X", "O"]:
            raise ValueError("First player must be X or O")
        return v


class TicTacToePlugin(GamePlugin):
    """Tic-tac-toe game plugin with AI opponent."""
    
    def get_game_type(self) -> str:
        return "tic_tac_toe"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="Tic-Tac-Toe",
            description="Classic 3x3 tic-tac-toe game with configurable AI opponent. "
                       "Features multiple difficulty levels, move analysis, and game statistics.",
            category=GameCategory.BOARD,
            difficulty=DifficultyLevel.EASY,
            min_players=1,
            max_players=2,
            features=[
                GameFeature.SINGLE_PLAYER,
                GameFeature.MULTI_PLAYER,
                GameFeature.AI_OPPONENT,
                GameFeature.TURN_BASED,
                GameFeature.ASCII_ART,
                GameFeature.STATISTICS,
                GameFeature.UNDO_REDO
            ],
            version="1.0.0",
            author="MCP Game Framework",
            complexity_score=2.0,
            estimated_duration_minutes=5,
            tags=["classic", "strategy", "quick"]
        )
    
    def get_config_model(self):
        return TicTacToeConfig
    
    def get_state_model(self):
        return TicTacToeState
    
    def create_initial_state(self, game_id: str, config: TicTacToeConfig) -> TicTacToeState:
        return TicTacToeState(
            game_id=game_id,
            game_type=self.get_game_type(),
            current_player=config.first_player,
            player_x_human=config.player_x_human,
            player_o_human=config.player_o_human,
            ai_difficulty=config.ai_difficulty
        )


# Plugin factory function
def create_plugin() -> GamePlugin:
    return TicTacToePlugin()