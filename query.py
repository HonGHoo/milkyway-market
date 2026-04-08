"""
Milky Way Idle Marketplace - 24h/7d volume query tool

Usage:
  1. First run: git clone your repo, or git pull to update data
  2. Double click query.bat to launch
  3. Enter item name to search
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_snapshots(hours):
    """Load all snapshots within the last N hours."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    snapshots = []

    if not DATA_DIR.exists():
        print(f"[Error] data folder not found: {DATA_DIR}")
        print("Please run: git pull")
        return []

    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            # filename: 2026-04-02_13-00.json
            name = f.stem
            ts = datetime.strptime(name, "%Y-%m-%d_%H-%M").replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                snapshots.append({"time": ts, "data": data.get("marketData", {})})
        except (ValueError, json.JSONDecodeError):
            continue

    return snapshots


def find_items(keyword, snapshots):
    """Find item names matching keyword."""
    if not snapshots:
        return []
    all_items = set()
    for s in snapshots:
        all_items.update(s["data"].keys())
    keyword_lower = keyword.lower()
    return sorted([name for name in all_items if keyword_lower in name.lower()])


def calc_volume_change(item_key, snapshots):
    """Calculate volume change between first and last snapshot."""
    first = None
    last = None

    for s in snapshots:
        if item_key in s["data"]:
            item = s["data"][item_key]
            total_v = sum(tier.get("v", 0) for tier in item.values() if isinstance(tier, dict))
            if first is None:
                first = total_v
            last = total_v

    if first is not None and last is not None:
        return last - first
    return None


def show_current_price(item_key, snapshots):
    """Show current price info from latest snapshot."""
    for s in reversed(snapshots):
        if item_key in s["data"]:
            item = s["data"][item_key]
            print(f"\n  Current prices (latest snapshot):")
            for tier, info in sorted(item.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                if not isinstance(info, dict):
                    continue
                a = info.get("a", "N/A")
                b = info.get("b", "N/A")
                p = info.get("p", "N/A")
                v = info.get("v", "N/A")
                if b == -1:
                    b = "No bid"
                print(f"    Tier {tier}: Ask={a}  Bid={b}  Price={p}  Volume={v}")
            return


def main():
    print("=" * 50)
    print("  Milky Way Idle - Market Query Tool")
    print("=" * 50)

    # Load all available data (up to 7 days)
    print("\nLoading data...")
    snapshots_7d = load_snapshots(168)
    snapshots_24h = load_snapshots(24)

    if not snapshots_7d:
        print("No data found. Make sure you have pulled the latest data.")
        input("\nPress Enter to exit...")
        return

    print(f"  Loaded: {len(snapshots_24h)} snapshots (24h), {len(snapshots_7d)} snapshots (7d)")

    while True:
        print("\n" + "-" * 50)
        keyword = input("\nEnter item name to search (or 'quit' to exit): ").strip()
        if keyword.lower() in ("quit", "exit", "q"):
            break
        if not keyword:
            continue

        matches = find_items(keyword, snapshots_7d)
        if not matches:
            print(f"  No items found matching '{keyword}'")
            continue

        if len(matches) > 20:
            print(f"  Found {len(matches)} items, showing first 20:")
            matches = matches[:20]
        elif len(matches) > 1:
            print(f"  Found {len(matches)} items:")

        for i, name in enumerate(matches):
            print(f"    [{i + 1}] {name}")

        if len(matches) == 1:
            choice = 0
        else:
            try:
                choice = int(input("\nSelect number: ")) - 1
            except (ValueError, EOFError):
                continue

        if 0 <= choice < len(matches):
            item_key = matches[choice]
            print(f"\n  === {item_key} ===")

            show_current_price(item_key, snapshots_7d)

            vol_24h = calc_volume_change(item_key, snapshots_24h)
            vol_7d = calc_volume_change(item_key, snapshots_7d)

            print(f"\n  Volume traded (24h): {vol_24h if vol_24h is not None else 'Not enough data'}")
            print(f"  Volume traded (7d):  {vol_7d if vol_7d is not None else 'Not enough data'}")

    print("\nGoodbye!")


if __name__ == "__main__":
    main()
