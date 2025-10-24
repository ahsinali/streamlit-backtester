from dataclasses import dataclass
@dataclass
class SimConfig:
    cash: float; fee_bps: float; slip_bps: float; policy: str
