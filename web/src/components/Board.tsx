import { BoardView } from "./BoardView";
import { useBoardAnimation } from "../hooks/useBoardAnimation";
import type { GameState } from "../lib/protocol";

interface Props {
  state: GameState;
  onPlay: (pit: number) => void;
  disabled: boolean;
}

export function Board({ state, onPlay, disabled }: Props) {
  const anim = useBoardAnimation(state);
  const view = anim.displayed ?? state;
  const isAnimating = anim.animating;

  return (
    <BoardView
      frame={{
        pits: view.pits,
        stores: view.stores,
        last_move: view.last_move ? { by: view.last_move.by, pit: view.last_move.pit } : null,
      }}
      legalMoves={view.legal_moves}
      onPlay={onPlay}
      disabled={disabled || isAnimating}
      flyingPit={anim.flyingPit}
      flyingTo={anim.flyingTo}
    />
  );
}
