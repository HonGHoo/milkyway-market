import urllib.request
import json
from database import save_snapshot

API_URL = "https://www.milkywayidle.com/game_data/marketplace.json"


def fetch_and_save():
    """从游戏API抓取市场数据并存入数据库"""
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "MWI-Market-Tracker/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        market_data = data.get("marketData") or data
        snapshot_id = save_snapshot(market_data)

        if snapshot_id:
            item_count = sum(len(levels) for levels in market_data.values())
            print(f"[collector] saved snapshot #{snapshot_id}, {item_count} records")
        else:
            print("[collector] skipped (duplicate timestamp)")

        return True
    except Exception as e:
        print(f"[collector] error: {e}")
        return False


if __name__ == "__main__":
    from database import init_db
    init_db()
    fetch_and_save()
