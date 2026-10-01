"""The catalogue of DM games: one entry per game, used by /play and /help."""
from __future__ import annotations

from dataclasses import dataclass

from services.dm_games.board import (
    Connect4, Hangman, HigherLower, MemoryGame, NumberGuess, RockPaperScissors, TicTacToe,
)
from services.dm_games.quiz import (
    Compatibility, EmojiGuess, GuessFavourite, KnowGame, MostLikely, PickOne, ThisOrThat,
    Trivia, TruthOrDare, WordScramble, WouldYouRather,
)
from services.dm_games.session import GameSession


@dataclass(frozen=True)
class GameInfo:
    key: str
    label: str
    blurb: str
    cls: type[GameSession]


GAMES: tuple[GameInfo, ...] = (
    GameInfo("ttt", "⭕ Tic-Tac-Toe", "Classic 3×3, synced across both DMs", TicTacToe),
    GameInfo("connect4", "🔴 Connect 4", "Drop discs, get four in a row", Connect4),
    GameInfo("rps", "✂️ Rock Paper Scissors", "Best of 3, secret picks", RockPaperScissors),
    GameInfo("memory", "🧠 Memory", "Match the emoji pairs", MemoryGame),
    GameInfo("hangman", "🪢 Hangman", "One sets a word, the other guesses", Hangman),
    GameInfo("number", "🔢 Number Guessing", "Find the secret number together", NumberGuess),
    GameInfo("higherlower", "🃏 Higher or Lower", "Build a team streak", HigherLower),
    GameInfo("truthordare", "🎭 Truth or Dare", "Take turns, couple edition", TruthOrDare),
    GameInfo("wyr", "🤍 Would You Rather", "5 dilemmas, see if you agree", WouldYouRather),
    GameInfo("thisorthat", "⚡ This or That", "Rapid-fire preferences", ThisOrThat),
    GameInfo("mostlikely", "🙋 Who's More Likely To…", "Point at each other", MostLikely),
    GameInfo("compat", "💘 Compatibility Quiz", "Get your match percentage", Compatibility),
    GameInfo("knowme", "🔍 Who Knows Who Better?", "Answer, then guess your partner", KnowGame),
    GameInfo("favourite", "💝 Guess My Favourite", "Free-text favourites, guess each other's", GuessFavourite),
    GameInfo("trivia", "🧩 Trivia", "Five questions, higher score wins", Trivia),
    GameInfo("emoji", "😎 Emoji Guessing", "Decode the emoji puzzle first", EmojiGuess),
    GameInfo("word", "🔤 Word Guessing", "Unscramble the word first", WordScramble),
    GameInfo("pickone", "🌙 Pick One for Tonight", "Settle what to do tonight", PickOne),
)

BY_KEY = {g.key: g for g in GAMES}
