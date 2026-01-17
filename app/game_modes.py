from dataclasses import dataclass
from typing import Optional
from app.config import MODE_CLASSIC, MODE_ENDLESS, MODE_TIMED

@dataclass
class GameSession:
    user_id: int
    mode: str
    score: int = 0
    lives: int = 3
    time_left: Optional[int] = None
    current_question: dict = None
    question_count: int = 0
    emoji_message_id: Optional[int] = None
    
    def is_active(self) -> bool:
        if self.mode == MODE_CLASSIC: return self.lives > 0
        elif self.mode == MODE_ENDLESS: return True
        elif self.mode == MODE_TIMED: return self.time_left is None or self.time_left > 0
        return False

active_games = {}
game_timers = {}