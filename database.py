import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            item_hrid TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 0,
            ask INTEGER,
            bid INTEGER,
            price INTEGER,
            volume INTEGER,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        );

        CREATE INDEX IF NOT EXISTS idx_market_item ON market_data(item_hrid, level);
        CREATE INDEX IF NOT EXISTS idx_market_snapshot ON market_data(snapshot_id);
    """)
    conn.commit()
    conn.close()


def save_snapshot(market_data: dict, timestamp: str = None):
    """保存一次市场快照"""
    if timestamp is None:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    try:
        cursor = conn.execute("INSERT INTO snapshots (timestamp) VALUES (?)", (timestamp,))
        snapshot_id = cursor.lastrowid

        rows = []
        for item_hrid, levels in market_data.items():
            for level_str, data in levels.items():
                rows.append((
                    snapshot_id,
                    item_hrid,
                    int(level_str),
                    data.get("a"),
                    data.get("b"),
                    data.get("p"),
                    data.get("v"),
                ))

        conn.executemany(
            "INSERT INTO market_data (snapshot_id, item_hrid, level, ask, bid, price, volume) VALUES (?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()
        return snapshot_id
    except sqlite3.IntegrityError:
        # 同一时间戳已存在，跳过
        return None
    finally:
        conn.close()


def get_item_history(item_hrid: str, level: int = 0, limit: int = 720):
    """获取某物品的历史价格，默认最近720条（约30天，每小时1条）"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.timestamp, m.ask, m.bid, m.price, m.volume
        FROM market_data m
        JOIN snapshots s ON s.id = m.snapshot_id
        WHERE m.item_hrid = ? AND m.level = ?
        ORDER BY s.timestamp DESC
        LIMIT ?
    """, (item_hrid, level, limit)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_all_items():
    """获取所有有数据的物品列表"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT item_hrid, level FROM market_data ORDER BY item_hrid, level
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_snapshot():
    """获取最新一次快照的所有数据"""
    conn = get_conn()
    snapshot = conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
    if not snapshot:
        conn.close()
        return None, []

    rows = conn.execute("""
        SELECT item_hrid, level, ask, bid, price, volume
        FROM market_data WHERE snapshot_id = ?
        ORDER BY item_hrid, level
    """, (snapshot["id"],)).fetchall()
    conn.close()
    return snapshot["timestamp"], [dict(r) for r in rows]


def get_price_changes():
    """获取最新两次快照的价格变化，用于涨跌幅排行"""
    conn = get_conn()
    snapshots = conn.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 2").fetchall()
    if len(snapshots) < 2:
        conn.close()
        return []

    new_id, old_id = snapshots[0]["id"], snapshots[1]["id"]

    rows = conn.execute("""
        SELECT
            n.item_hrid, n.level,
            n.ask AS new_ask, n.bid AS new_bid, n.price AS new_price, n.volume AS new_volume,
            o.ask AS old_ask, o.bid AS old_bid, o.price AS old_price, o.volume AS old_volume
        FROM market_data n
        JOIN market_data o ON o.item_hrid = n.item_hrid AND o.level = n.level AND o.snapshot_id = ?
        WHERE n.snapshot_id = ?
    """, (old_id, new_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
