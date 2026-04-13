"""
读取最近24小时的快照，生成汇总文件 data/summary_24h.json
GitHub Action 每次采集后自动运行此脚本
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "summary_24h.json"


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # 找到最近24小时内的所有快照文件
    snapshot_files = []
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name == "summary_24h.json":
            continue
        try:
            ts = datetime.strptime(f.stem, "%Y-%m-%d_%H-%M").replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                snapshot_files.append(f)
        except ValueError:
            continue

    if not snapshot_files:
        print("[aggregate] no snapshots found in last 24h")
        return

    print(f"[aggregate] processing {len(snapshot_files)} snapshots")

    # 用来累加每个物品的成交量和交易额
    # key = item_id (不含 /items/ 前缀), value = {v, pv, a, b, p}
    items = {}

    for f in snapshot_files:
        with open(f, "r", encoding="utf-8") as fp:
            raw = json.load(fp)
        market = raw.get("marketData", raw)

        for item_hrid, levels in market.items():
            # 去掉 /items/ 前缀，得到物品ID（和游戏SVG sprite里的ID一致）
            item_id = item_hrid.replace("/items/", "")

            # 只处理 level 0（基础等级）
            if "0" not in levels:
                continue
            info = levels["0"]

            v = info.get("v") or 0
            p = info.get("p") or 0
            a = info.get("a")
            b = info.get("b")

            if item_id not in items:
                items[item_id] = {"v": 0, "pv": 0, "a": a, "b": b, "latest_p": p}

            # 累加成交量和交易额（均价×成交量）
            items[item_id]["v"] += v
            items[item_id]["pv"] += p * v
            # 更新为最新一次快照的 ask/bid/price
            items[item_id]["a"] = a
            items[item_id]["b"] = b
            items[item_id]["latest_p"] = p

    # 生成最终汇总
    summary = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_count": len(snapshot_files),
        "items": {}
    }

    for item_id, data in items.items():
        total_v = data["v"]
        # 加权平均价 = 总交易额 / 总成交量
        avg_p = round(data["pv"] / total_v, 1) if total_v > 0 else data["latest_p"]

        summary["items"][item_id] = {
            "p": avg_p,          # 24h加权均价
            "v": total_v,        # 24h总成交量（件数）
            "tv": data["pv"],    # 24h总交易额（金币）
            "a": data["a"],      # 最新卖价
            "b": data["b"]       # 最新买价
        }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False)

    print(f"[aggregate] wrote {len(summary['items'])} items to {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
