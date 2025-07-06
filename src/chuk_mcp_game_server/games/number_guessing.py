# games/number_guessing.py
"""
Number Guessing Game Plugin
==========================

Interactive number guessing game with hints, statistics, and adaptive difficulty.
Demonstrates progressive difficulty, hint systems, and detailed game analytics.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import Field, field_validator
import random
import math

from chuk_mcp_game_server.core import (
    GameStateBase, GameConfig, GameInfo, GameCategory,
    DifficultyLevel, GameFeature
)
from chuk_mcp_game_server.plugins import GamePlugin


class HintType(str, Enum):
    """Types of hints available."""
    HIGHER_LOWER = "higher_lower"
    HOT_COLD = "hot_cold"
    RANGE = "range"
    PARITY = "parity"  # odd/even
    DIGIT_COUNT = "digit_count"


class GamePhase(str, Enum):
    """Game phases."""
    STARTING = "starting"
    GUESSING = "guessing"
    WON = "won"
    LOST = "lost"


class NumberGuessingState(GameStateBase):
    """Number guessing game state."""
    
    target_number: int = Field(..., description="The secret number to guess")
    min_range: int = Field(default=1, description="Minimum possible number")
    max_range: int = Field(default=100, description="Maximum possible number")
    max_attempts: int = Field(default=10, description="Maximum number of guesses allowed")
    attempts_used: int = Field(default=0, description="Number of attempts used")
    guesses: List[int] = Field(default_factory=list, description="List of all guesses made")
    hints_given: List[Dict[str, Any]] = Field(default_factory=list, description="Hints provided to player")
    current_phase: str = Field(default=GamePhase.STARTING.value, description="Current game phase")
    score: int = Field(default=0, description="Player's score")
    hint_penalty: int = Field(default=0, description="Points deducted for hints")
    last_guess: Optional[int] = Field(None, description="Last number guessed")
    best_guess_distance: Optional[int] = Field(None, description="Closest guess distance")
    difficulty_level: str = Field(default="medium", description="Current difficulty level")
    hints_enabled: bool = Field(default=True, description="Whether hints are enabled")
    adaptive_difficulty: bool = Field(default=False, description="Whether difficulty adapts to performance")
    
    def start_game(self):
        """Initialize a new game."""
        self.target_number = random.randint(self.min_range, self.max_range)
        self.current_phase = GamePhase.GUESSING.value
        self.attempts_used = 0
        self.guesses.clear()
        self.hints_given.clear()
        self.score = self._calculate_max_score()
        self.hint_penalty = 0
        self.last_guess = None
        self.best_guess_distance = None
        self.touch()
    
    def make_guess(self, guess: int) -> Dict[str, Any]:
        """Make a guess and return the result."""
        if self.current_phase not in [GamePhase.GUESSING.value, GamePhase.STARTING.value]:
            return {"success": False, "error": "Game is not in progress"}
        
        if self.current_phase == GamePhase.STARTING.value:
            self.start_game()
        
        if not (self.min_range <= guess <= self.max_range):
            return {
                "success": False, 
                "error": f"Guess must be between {self.min_range} and {self.max_range}"
            }
        
        if guess in self.guesses:
            return {"success": False, "error": "You already guessed that number"}
        
        # Record the guess
        self.guesses.append(guess)
        self.last_guess = guess
        self.attempts_used += 1
        
        # Calculate distance from target
        distance = abs(guess - self.target_number)
        if self.best_guess_distance is None or distance < self.best_guess_distance:
            self.best_guess_distance = distance
        
        # Check if guess is correct
        if guess == self.target_number:
            self.current_phase = GamePhase.WON.value
            self.is_completed = True
            final_score = self._calculate_final_score()
            self.touch()
            
            return {
                "success": True,
                "correct": True,
                "message": f"🎉 Congratulations! You guessed the number {self.target_number}!",
                "attempts_used": self.attempts_used,
                "score": final_score,
                "game_over": True,
                "performance": self._get_performance_rating()
            }
        
        # Check if out of attempts
        if self.attempts_used >= self.max_attempts:
            self.current_phase = GamePhase.LOST.value
            self.is_completed = True
            self.touch()
            
            return {
                "success": True,
                "correct": False,
                "message": f"😞 Game over! The number was {self.target_number}.",
                "attempts_used": self.attempts_used,
                "score": 0,
                "game_over": True,
                "target_number": self.target_number
            }
        
        # Generate response for incorrect guess
        response = {
            "success": True,
            "correct": False,
            "guess": guess,
            "attempts_remaining": self.max_attempts - self.attempts_used,
            "distance": distance,
            "message": self._generate_feedback_message(guess, distance),
            "game_over": False
        }
        
        # Add hint if enabled
        if self.hints_enabled:
            hint = self._generate_hint(guess, distance)
            if hint:
                response["hint"] = hint
        
        self.touch()
        return response
    
    def get_hint(self, hint_type: HintType = None) -> Dict[str, Any]:
        """Get a specific type of hint."""
        if not self.hints_enabled:
            return {"success": False, "error": "Hints are disabled for this game"}
        
        if self.current_phase != GamePhase.GUESSING.value:
            return {"success": False, "error": "Game is not in progress"}
        
        # Apply hint penalty
        penalty = 5 if self.difficulty_level == "easy" else 10
        self.hint_penalty += penalty
        self.score = max(0, self.score - penalty)
        
        if hint_type is None:
            hint_type = self._choose_best_hint_type()
        
        hint_text = ""
        hint_data = {"type": hint_type.value, "penalty": penalty}
        
        if hint_type == HintType.HIGHER_LOWER and self.last_guess is not None:
            if self.last_guess < self.target_number:
                hint_text = "📈 Try a higher number"
            else:
                hint_text = "📉 Try a lower number"
        
        elif hint_type == HintType.HOT_COLD:
            if self.last_guess is not None:
                distance = abs(self.last_guess - self.target_number)
                range_size = self.max_range - self.min_range
                
                if distance <= range_size * 0.05:
                    hint_text = "🔥 Very hot! You're extremely close!"
                elif distance <= range_size * 0.1:
                    hint_text = "🌶️ Hot! You're getting close!"
                elif distance <= range_size * 0.25:
                    hint_text = "🌡️ Warm. You're in the right area."
                elif distance <= range_size * 0.5:
                    hint_text = "❄️ Cold. You're quite far off."
                else:
                    hint_text = "🧊 Freezing! You're very far away."
        
        elif hint_type == HintType.RANGE:
            # Give a narrowed range
            range_reduction = 0.3 if self.difficulty_level == "easy" else 0.2
            range_size = self.max_range - self.min_range
            reduction_amount = int(range_size * range_reduction)
            
            new_min = max(self.min_range, self.target_number - reduction_amount)
            new_max = min(self.max_range, self.target_number + reduction_amount)
            
            hint_text = f"🎯 The number is between {new_min} and {new_max}"
        
        elif hint_type == HintType.PARITY:
            if self.target_number % 2 == 0:
                hint_text = "🔢 The number is even"
            else:
                hint_text = "🔢 The number is odd"
        
        elif hint_type == HintType.DIGIT_COUNT:
            digit_count = len(str(self.target_number))
            hint_text = f"🔢 The number has {digit_count} digit{'s' if digit_count > 1 else ''}"
        
        hint_record = {
            "hint_type": hint_type.value,
            "hint_text": hint_text,
            "penalty": penalty,
            "attempts_used": self.attempts_used
        }
        self.hints_given.append(hint_record)
        
        self.touch()
        
        return {
            "success": True,
            "hint": hint_text,
            "penalty": penalty,
            "remaining_score": self.score,
            "hints_used": len(self.hints_given)
        }
    
    def _generate_feedback_message(self, guess: int, distance: int) -> str:
        """Generate encouraging feedback message."""
        if distance == 1:
            return "🎯 So close! You're just 1 away!"
        elif distance <= 5:
            return "🔥 Very close! You're getting hot!"
        elif distance <= 10:
            return "🌶️ Close! You're on the right track!"
        elif distance <= 20:
            return "🌡️ Getting warmer, but still some way to go."
        else:
            return "❄️ Not quite there yet. Keep trying!"
    
    def _generate_hint(self, guess: int, distance: int) -> Optional[str]:
        """Automatically generate an appropriate hint."""
        if len(self.hints_given) >= 3:  # Limit automatic hints
            return None
        
        if distance <= 5:
            return self.get_hint(HintType.HOT_COLD).get("hint")
        elif len(self.guesses) >= 3:
            return self.get_hint(HintType.HIGHER_LOWER).get("hint")
        else:
            return None
    
    def _choose_best_hint_type(self) -> HintType:
        """Choose the most helpful hint type based on game state."""
        if self.last_guess is None:
            return HintType.RANGE
        
        distance = abs(self.last_guess - self.target_number)
        
        if distance <= 10:
            return HintType.HOT_COLD
        elif len(self.guesses) >= 2:
            return HintType.HIGHER_LOWER
        else:
            return HintType.RANGE
    
    def _calculate_max_score(self) -> int:
        """Calculate maximum possible score."""
        base_score = 100
        range_multiplier = max(1, math.log10(self.max_range - self.min_range + 1))
        return int(base_score * range_multiplier)
    
    def _calculate_final_score(self) -> int:
        """Calculate final score based on performance."""
        if self.current_phase != GamePhase.WON.value:
            return 0
        
        max_score = self._calculate_max_score()
        
        # Efficiency bonus (fewer attempts = higher score)
        efficiency_ratio = 1 - (self.attempts_used / self.max_attempts)
        efficiency_bonus = int(max_score * 0.5 * efficiency_ratio)
        
        # Speed bonus (finding it quickly)
        if self.attempts_used <= 3:
            speed_bonus = 50
        elif self.attempts_used <= 5:
            speed_bonus = 25
        else:
            speed_bonus = 0
        
        final_score = max_score + efficiency_bonus + speed_bonus - self.hint_penalty
        return max(0, final_score)
    
    def _get_performance_rating(self) -> str:
        """Get performance rating based on attempts used."""
        efficiency = self.attempts_used / self.max_attempts
        
        if efficiency <= 0.3:
            return "🏆 Excellent! Outstanding guessing skills!"
        elif efficiency <= 0.5:
            return "⭐ Great! Very good performance!"
        elif efficiency <= 0.7:
            return "👍 Good! Solid guessing strategy!"
        else:
            return "👌 Not bad! Room for improvement!"
    
    def get_game_stats(self) -> Dict[str, Any]:
        """Get comprehensive game statistics."""
        stats = {
            "target_number": self.target_number if self.is_completed else "Hidden",
            "attempts_used": self.attempts_used,
            "attempts_remaining": self.max_attempts - self.attempts_used,
            "guesses_made": self.guesses.copy(),
            "hints_used": len(self.hints_given),
            "current_score": self.score,
            "hint_penalty": self.hint_penalty,
            "best_guess_distance": self.best_guess_distance,
            "game_phase": self.current_phase
        }
        
        if self.is_completed:
            stats["final_score"] = self._calculate_final_score()
            stats["performance_rating"] = self._get_performance_rating()
            
            if self.guesses:
                stats["guess_analysis"] = {
                    "closest_guess": min(self.guesses, key=lambda x: abs(x - self.target_number)),
                    "average_distance": sum(abs(g - self.target_number) for g in self.guesses) / len(self.guesses),
                    "improvement_trend": self._analyze_improvement_trend()
                }
        
        return stats
    
    def _analyze_improvement_trend(self) -> str:
        """Analyze if guesses are getting closer over time."""
        if len(self.guesses) < 2:
            return "insufficient_data"
        
        distances = [abs(guess - self.target_number) for guess in self.guesses]
        
        # Check if generally improving
        first_half = distances[:len(distances)//2]
        second_half = distances[len(distances)//2:]
        
        if len(second_half) > 0:
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            if avg_second < avg_first * 0.8:
                return "improving"
            elif avg_second > avg_first * 1.2:
                return "declining"
            else:
                return "stable"
        
        return "stable"
    
    def get_ascii_art_display(self) -> str:
        """Get ASCII art representation of the game state."""
        lines = []
        lines.append("🎯 NUMBER GUESSING GAME 🎯")
        lines.append("=" * 30)
        lines.append(f"Range: {self.min_range} - {self.max_range}")
        lines.append(f"Attempts: {self.attempts_used}/{self.max_attempts}")
        lines.append(f"Score: {self.score}")
        
        if self.guesses:
            lines.append(f"\n📝 Your guesses:")
            for i, guess in enumerate(self.guesses[-5:], 1):  # Show last 5 guesses
                distance = abs(guess - self.target_number) if self.is_completed else "?"
                lines.append(f"  {i}. {guess} (distance: {distance})")
        
        if self.hints_given:
            lines.append(f"\n💡 Hints used: {len(self.hints_given)}")
            if self.hints_given:
                latest_hint = self.hints_given[-1]["hint_text"]
                lines.append(f"  Latest: {latest_hint}")
        
        if self.is_completed:
            if self.current_phase == GamePhase.WON.value:
                lines.append(f"\n🎉 YOU WON! The number was {self.target_number}!")
                lines.append(f"🏆 Final Score: {self._calculate_final_score()}")
            else:
                lines.append(f"\n😞 Game Over! The number was {self.target_number}")
        
        return "\n".join(lines)


class NumberGuessingConfig(GameConfig):
    """Number guessing game configuration."""
    min_range: int = Field(default=1, ge=1, description="Minimum number in range")
    max_range: int = Field(default=100, ge=2, description="Maximum number in range")
    max_attempts: int = Field(default=10, ge=1, le=50, description="Maximum attempts allowed")
    hints_enabled: bool = Field(default=True, description="Whether hints are available")
    adaptive_difficulty: bool = Field(default=False, description="Whether difficulty adapts")
    
    @field_validator('max_range')
    @classmethod
    def validate_range(cls, v, info):
        if info.data and v <= info.data.get('min_range', 1):
            raise ValueError("max_range must be greater than min_range")
        return v


class NumberGuessingPlugin(GamePlugin):
    """Number guessing game plugin with adaptive difficulty and hints."""
    
    def get_game_type(self) -> str:
        return "number_guessing"
    
    def get_game_info(self) -> GameInfo:
        return GameInfo(
            name="Number Guessing Game",
            description="Guess the secret number with intelligent hints and adaptive difficulty. "
                       "Features multiple hint types, performance tracking, and detailed statistics.",
            category=GameCategory.PUZZLE,
            difficulty=DifficultyLevel.EASY,
            min_players=1,
            max_players=1,
            features=[
                GameFeature.SINGLE_PLAYER,
                GameFeature.ASCII_ART,
                GameFeature.STATISTICS,
                GameFeature.PLANNING_DEMO
            ],
            version="1.0.0",
            author="MCP Game Framework",
            complexity_score=3.0,
            estimated_duration_minutes=10,
            tags=["puzzle", "logic", "educational", "hints"]
        )
    
    def get_config_model(self):
        return NumberGuessingConfig
    
    def get_state_model(self):
        return NumberGuessingState
    
    def create_initial_state(self, game_id: str, config: NumberGuessingConfig) -> NumberGuessingState:
        # Adjust max attempts based on range size
        range_size = config.max_range - config.min_range + 1
        suggested_attempts = min(config.max_attempts, max(5, int(math.log2(range_size)) + 3))
        
        return NumberGuessingState(
            game_id=game_id,
            game_type=self.get_game_type(),
            min_range=config.min_range,
            max_range=config.max_range,
            max_attempts=suggested_attempts,
            hints_enabled=config.hints_enabled,
            adaptive_difficulty=config.adaptive_difficulty,
            difficulty_level=config.difficulty.value if hasattr(config, 'difficulty') else "medium"
        )


# Plugin factory function
def create_plugin() -> GamePlugin:
    return NumberGuessingPlugin()