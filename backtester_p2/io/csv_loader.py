import pandas as pd, xxhash
from datetime import datetime

REQUIRED_COLS = ["Date","Open","High","Low","Close","Volume"]

def load_ohlcv(path: str):
    df = pd.read_csv(path)
    for col in REQUIRED_COLS:
        if col not in df.columns:
            raise ValueError(f"CSV missing {col}")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    h = xxhash.xxh64()
    for col in REQUIRED_COLS:
        h.update(pd.util.hash_pandas_object(df[col], index=False).values.tobytes())
    meta = {"rows": len(df), "checksum": h.hexdigest(), "start": str(df.iloc[0]["Date"]), "end": str(df.iloc[-1]["Date"])}
    return df, meta
