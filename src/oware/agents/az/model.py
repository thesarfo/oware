import torch
import torch.nn as nn
import torch.nn.functional as F

AUX_DIM = 3  # store_to_move, store_opponent, ply_normalized
AUX_HIDDEN = 16


class _ResBlock(nn.Module):
  def __init__(self) -> None:
    super().__init__()
    self.net = nn.Sequential(
      nn.Conv2d(64, 64, 3, padding=1),
      nn.BatchNorm2d(64),
      nn.ReLU(),
      nn.Conv2d(64, 64, 3, padding=1),
      nn.BatchNorm2d(64),
    )

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    return F.relu(self.net(x) + x)


class AZNetwork(nn.Module):
  def __init__(self) -> None:
    super().__init__()
    self.body = nn.Sequential(
      nn.Conv2d(1, 64, 3, padding=1),
      nn.BatchNorm2d(64),
      nn.ReLU(),
      _ResBlock(),
      _ResBlock(),
      _ResBlock(),
      _ResBlock(),
    )
    # The board conv sees pit counts only; stores + ply go through a small
    # MLP and concat into both heads — without them the value head literally
    # cannot tell who is ahead in captures.
    self.aux = nn.Sequential(nn.Linear(AUX_DIM, AUX_HIDDEN), nn.ReLU())

    self.pol_conv = nn.Sequential(nn.Conv2d(64, 2, 1), nn.BatchNorm2d(2), nn.ReLU())
    self.pol_fc = nn.Linear(2 * 2 * 6 + AUX_HIDDEN, 6)

    self.val_conv = nn.Sequential(nn.Conv2d(64, 1, 1), nn.BatchNorm2d(1), nn.ReLU())
    self.val_fc = nn.Sequential(
      nn.Linear(1 * 2 * 6 + AUX_HIDDEN, 64), nn.ReLU(), nn.Linear(64, 1), nn.Tanh()
    )

  def forward(
    self, obs_flat: torch.Tensor, mask: torch.Tensor
  ) -> tuple[torch.Tensor, torch.Tensor]:
    # obs_flat: (B, 15) — pits[0..11], my_store, opp_store, ply_norm.
    board = obs_flat[:, :12].reshape(-1, 1, 2, 6)
    aux_in = obs_flat[:, 12:15]
    h = self.body(board)
    aux = self.aux(aux_in)

    logits = self.pol_fc(torch.cat([self.pol_conv(h).flatten(1), aux], dim=-1))
    logits = logits.masked_fill(mask == 0, -1e9)
    log_probs = F.log_softmax(logits, dim=-1)

    value = self.val_fc(torch.cat([self.val_conv(h).flatten(1), aux], dim=-1)).squeeze(
      -1
    )
    return log_probs, value
