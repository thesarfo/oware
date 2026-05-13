import torch
import torch.nn as nn
import torch.nn.functional as F


class PPONetwork(nn.Module):
  def __init__(self) -> None:
    super().__init__()
    self.trunk = nn.Sequential(
      nn.Linear(15, 256),
      nn.ReLU(),
      nn.Linear(256, 256),
      nn.ReLU(),
    )
    self.policy_head = nn.Linear(256, 6)
    self.value_head = nn.Linear(256, 1)

  def forward(
    self, obs: torch.Tensor, mask: torch.Tensor
  ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    h = self.trunk(obs)
    logits = self.policy_head(h)
    logits = logits.masked_fill(mask == 0, -1e9)
    log_probs = F.log_softmax(logits, dim=-1)
    probs = log_probs.exp()
    entropy = -(probs * log_probs).sum(dim=-1)
    value = self.value_head(h).squeeze(-1)
    return log_probs, value, entropy
