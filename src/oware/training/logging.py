from pathlib import Path

from torch.utils.tensorboard import SummaryWriter


class RunLogger:
  def __init__(self, run_dir: Path) -> None:
    self._writer = SummaryWriter(str(run_dir))

  def scalar(self, tag: str, value: float, step: int) -> None:
    self._writer.add_scalar(tag, value, step)

  def scalars(self, prefix: str, values: dict[str, float], step: int) -> None:
    for k, v in values.items():
      self._writer.add_scalar(f"{prefix}/{k}", v, step)

  def text(self, tag: str, text: str, step: int) -> None:
    self._writer.add_text(tag, text, step)

  def close(self) -> None:
    self._writer.close()
