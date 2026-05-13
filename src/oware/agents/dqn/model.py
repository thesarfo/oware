import torch
import torch.nn as nn


class QNetwork(nn.Module):
  def __init__(self, dueling: bool = True) -> None:
    super().__init__()
    self.dueling = dueling
    self.trunk = nn.Sequential(
      nn.Linear(15, 128),
      nn.ReLU(),
      nn.Linear(128, 128),
      nn.ReLU(),
      nn.Linear(128, 128),
      nn.ReLU(),
    )
    if dueling:
      self.value_head = nn.Linear(128, 1)
      self.advantage_head = nn.Linear(128, 6)
    else:
      self.out = nn.Linear(128, 6)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    h = self.trunk(x)
    if self.dueling:
      v = self.value_head(h)
      a = self.advantage_head(h)
      return v + a - a.mean(dim=-1, keepdim=True)
    return self.out(h)
