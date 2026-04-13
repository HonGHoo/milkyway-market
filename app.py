from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db, get_item_history, get_all_items, get_latest_snapshot, get_price_changes
from collector import fetch_and_save

app = Flask(__name__, static_folder="static")


# ========== 页面 ==========

@app.route("/")
def index():
    return render_template("index.html")


# ========== API ==========

@app.route("/api/items")
def api_items():
    """获取所有物品列表"""
    return jsonify(get_all_items())


@app.route("/api/history")
def api_history():
    """获取某物品历史价格 ?item=/items/xxx&level=0&limit=720"""
    item = request.args.get("item", "")
    level = int(request.args.get("level", 0))
    limit = int(request.args.get("limit", 720))
    return jsonify(get_item_history(item, level, limit))


@app.route("/api/latest")
def api_latest():
    """获取最新快照"""
    timestamp, data = get_latest_snapshot()
    return jsonify({"timestamp": timestamp, "data": data})


@app.route("/api/changes")
def api_changes():
    """获取涨跌幅数据"""
    return jsonify(get_price_changes())


@app.route("/api/collect")
def api_collect():
    """手动触发一次数据采集"""
    success = fetch_and_save()
    return jsonify({"success": success})


# ========== 启动 ==========

if __name__ == "__main__":
    init_db()

    # 启动时立即采集一次
    print("[app] running initial data collection...")
    fetch_and_save()

    # 每小时自动采集
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_save, "interval", hours=1)
    scheduler.start()
    print("[app] scheduler started, collecting every 1 hour")

    app.run(host="0.0.0.0", port=5000, debug=False)
