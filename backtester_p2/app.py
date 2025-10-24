import argparse, sys
import os
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

def main():
    parser = argparse.ArgumentParser(description="Manual Backtester — Phase 2 (orders/fills/P&L)")
    parser.add_argument("--csv", type=str, default="backtester_p2/data/sample.csv")
    parser.add_argument("--mode", choices=["auto","gui","cli"], default="cli")
    parser.add_argument("--cash", type=float, default=100000.0)
    parser.add_argument("--fee_bps", type=float, default=1.0)
    parser.add_argument("--slip_bps", type=float, default=2.0)
    parser.add_argument("--policy", choices=["next_open","bar_inclusive"], default="next_open")
    args = parser.parse_args()

    from backtester_p2.io.csv_loader import load_ohlcv
    from backtester_p2.store.manifest import Manifest
    from backtester_p2.sim.config import SimConfig

    df, meta = load_ohlcv(args.csv)
    manifest = Manifest.create("SAMPLE", "D", meta, {"sma":[20,50,200]}, 42)
    cfg = SimConfig(cash=args.cash, fee_bps=args.fee_bps, slip_bps=args.slip_bps, policy=args.policy)

    mode = args.mode
    if mode in ("auto","gui"):
        try:
            from PySide6 import QtWidgets
            from backtester_p2.ui.chart import ChartWindow
            app = QtWidgets.QApplication(sys.argv)
            win = ChartWindow(df, manifest, cfg)
            win.setWindowTitle("Manual Backtester — Phase 2 GUI")
            win.show()
            sys.exit(app.exec())
        except Exception as e:
            if mode == "gui":
                print("GUI requested but failed, falling back to CLI. Error:", e)
            mode = "cli"
    if mode == "cli":
        from backtester_p2.ui.cli import run_cli
        run_cli(df, manifest, cfg)

if __name__ == "__main__":
    main()
