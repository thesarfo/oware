import torch
import torch.nn as nn
import torch.nn.functional as F


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
    # Policy head
    self.pol_conv = nn.Sequential(nn.Conv2d(64, 2, 1), nn.BatchNorm2d(2), nn.ReLU())
    self.pol_fc = nn.Linear(2 * 2 * 6, 6)
    # Value head
    self.val_conv = nn.Sequential(nn.Conv2d(64, 1, 1), nn.BatchNorm2d(1), nn.ReLU())
    self.val_fc = nn.Sequential(
      nn.Linear(1 * 2 * 6, 64), nn.ReLU(), nn.Linear(64, 1), nn.Tanh()
    )

  def forward(
    self, obs_flat: torch.Tensor, mask: torch.Tensor
  ) -> tuple[torch.Tensor, torch.Tensor]:
    # obs_flat: (B, 15)  →  board pits (B, 1, 2, 6)
    board = obs_flat[:, :12].reshape(-1, 1, 2, 6)
    h = self.body(board)
    logits = self.pol_fc(self.pol_conv(h).flatten(1))
    logits = logits.masked_fill(mask == 0, -1e9)
    log_probs = F.log_softmax(logits, dim=-1)
    value = self.val_fc(self.val_conv(h).flatten(1)).squeeze(-1)
    return log_probs, value
