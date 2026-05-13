from typing import Any, Literal

from pydantic import BaseModel, Field

Side = Literal["south", "north"]
EndReason = Literal["majority", "must_feed", "no_progress", "resign", "disconnect"]


class ClientNewGame(BaseModel):
  type: Literal["new_game"]
  agent_id: str
  human_plays: Side = "south"
  seed: int | None = None


class ClientMove(BaseModel):
  type: Literal["move"]
  game_id: str
  pit: int = Field(ge=0, le=5)


class ClientResign(BaseModel):
  type: Literal["resign"]
  game_id: str


class ClientPing(BaseModel):
  type: Literal["ping"]
  t: int


ClientMessage = ClientNewGame | ClientMove | ClientResign | ClientPing


class Stores(BaseModel):
  south: int
  north: int


class LastMove(BaseModel):
  by: Side
  pit: int
  captured: int


class GameState(BaseModel):
  type: Literal["state"] = "state"
  game_id: str
  pits: list[int]
  stores: Stores
  to_move: Side
  ply: int
  legal_moves: list[int]
  last_move: LastMove | None


class AgentBrief(BaseModel):
  id: str
  name: str


class GameStarted(BaseModel):
  type: Literal["game_started"] = "game_started"
  game_id: str
  agent: AgentBrief
  state: GameState


class AgentThinking(BaseModel):
  type: Literal["agent_thinking"] = "agent_thinking"
  game_id: str
  since: int


class AgentMove(BaseModel):
  type: Literal["agent_move"] = "agent_move"
  game_id: str
  pit: int
  thought_ms: int
  extras: dict[str, Any] = Field(default_factory=dict)


class GameOver(BaseModel):
  type: Literal["game_over"] = "game_over"
  game_id: str
  winner: Literal["south", "north", "draw"]
  reason: EndReason
  final_stores: Stores
  history: list[dict] = Field(default_factory=list)


class GameAnalysis(BaseModel):
  type: Literal["game_analysis"] = "game_analysis"
  game_id: str
  history: list[dict]


class ErrorMessage(BaseModel):
  type: Literal["error"] = "error"
  code: str
  message: str


class PongMessage(BaseModel):
  type: Literal["pong"] = "pong"
  t: int
