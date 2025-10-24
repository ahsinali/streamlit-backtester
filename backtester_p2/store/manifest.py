import json
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Manifest:
    symbol: str; timeframe: str; data_meta: dict; indicator_params: dict; seed: int; created_at: str
    @staticmethod
    def create(symbol, timeframe, data_meta, indicator_params, seed):
        return Manifest(symbol, timeframe, data_meta, indicator_params, seed, datetime.utcnow().isoformat())
    def to_json(self): return json.dumps(asdict(self), indent=2)
def anonymize_frame(df, seed): return df  # stub for now
