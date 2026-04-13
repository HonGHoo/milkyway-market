// ==UserScript==
// @name         MWI 市场数据叠加
// @namespace    https://github.com/HonGHoo/milkyway-market
// @version      0.3.0
// @description  在市场物品图标上显示24小时成交均价和交易额
// @match        https://www.milkywayidle.com/*
// @grant        GM_xmlhttpRequest
// @connect      raw.githubusercontent.com
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    // ===== 配置区 =====
    var CONFIG = {
        // 24h汇总数据的地址（你的GitHub仓库）
        SUMMARY_URL: 'https://raw.githubusercontent.com/HonGHoo/milkyway-market/main/data/summary_24h.json',
        // 多久刷新一次数据（毫秒），默认10分钟
        REFRESH_INTERVAL: 10 * 60 * 1000
    };

    // ===== 存放市场数据 =====
    var marketDataMap = {};

    // ===== 工具函数 =====

    // 把大数字格式化，比如 1234567 → "1.2M"
    function formatNumber(num) {
        if (num == null || num === 0) return '-';
        if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    // 从SVG的href里提取物品ID
    // "/static/media/items_sprite.xxx.svg#milk" → "milk"
    function extractItemId(svgHref) {
        if (!svgHref) return null;
        var hashIndex = svgHref.indexOf('#');
        if (hashIndex === -1) return null;
        return svgHref.substring(hashIndex + 1);
    }

    // 从一个DOM元素里找到物品ID
    function getItemIdFromElement(el) {
        var useEl = el.querySelector('use');
        if (!useEl) return null;
        return extractItemId(useEl.getAttribute('href'));
    }

    // ===== 数据获取 =====

    function fetchMarketData() {
        GM_xmlhttpRequest({
            method: 'GET',
            url: CONFIG.SUMMARY_URL + '?t=' + Date.now(),
            onload: function(response) {
                try {
                    var summary = JSON.parse(response.responseText);
                    marketDataMap = summary.items || {};
                    console.log('[MWI市场叠加] 数据加载成功，共',
                        Object.keys(marketDataMap).length, '个物品');
                    // 数据加载后刷新所有叠加
                    addVolumeOverlaysToAll();
                    addDetailOverlay();
                } catch (e) {
                    console.error('[MWI市场叠加] 解析数据出错:', e);
                }
            },
            onerror: function(err) {
                console.error('[MWI市场叠加] 请求数据出错:', err);
            }
        });
    }

    // ===== 注入CSS =====

    function injectStyles() {
        var style = document.createElement('style');
        style.textContent = [
            // 物品格子需要相对定位
            '[class*="Item_itemContainer"] {',
            '  position: relative !important;',
            '}',

            // ---- 全局：物品图标底部的成交量标签 ----
            '.mwi-vol-tag {',
            '  position: absolute;',
            '  bottom: -2px;',
            '  left: 50%;',
            '  transform: translateX(-50%);',
            '  background: rgba(0, 0, 0, 0.75);',
            '  color: #00ddbb;',
            '  font-size: 11px;',
            '  line-height: 1;',
            '  padding: 1px 3px;',
            '  pointer-events: none;',
            '  z-index: 10;',
            '  border-radius: 3px;',
            '  font-family: "Consolas", "Monaco", monospace;',
            '  white-space: nowrap;',
            '}',

            // ---- 市场详情页：均价和成交量信息框 ----
            '.mwi-detail-stats {',
            '  display: flex;',
            '  justify-content: center;',
            '  gap: 12px;',
            '  padding: 4px 8px;',
            '  margin: 4px 0;',
            '  background: rgba(0, 20, 50, 0.85);',
            '  border: 1px solid #003380;',
            '  border-radius: 4px;',
            '  font-family: "Consolas", "Monaco", monospace;',
            '  font-size: 13px;',
            '}',
            '.mwi-detail-stats .mwi-stat-item {',
            '  display: flex;',
            '  align-items: center;',
            '  gap: 4px;',
            '}',
            '.mwi-detail-stats .mwi-stat-label {',
            '  color: #8d9095;',
            '}',
            '.mwi-detail-stats .mwi-stat-value-price {',
            '  color: #ffcc00;',
            '  font-weight: bold;',
            '}',
            '.mwi-detail-stats .mwi-stat-value-vol {',
            '  color: #00ddbb;',
            '  font-weight: bold;',
            '}',
            '.mwi-detail-stats .mwi-stat-value-val {',
            '  color: #e5eaf3;',
            '}'
        ].join('\n');
        document.head.appendChild(style);
    }

    // ===== 全局：给物品图标底部加成交量 =====

    function addVolumeTag(itemContainer) {
        // 已经加过就跳过
        if (itemContainer.querySelector('.mwi-vol-tag')) return;

        var itemId = getItemIdFromElement(itemContainer);
        if (!itemId) return;

        var data = marketDataMap[itemId];
        if (!data) return;

        var vol = data.v;
        if (!vol) return;

        // 创建一个小标签显示成交量
        var tag = document.createElement('div');
        tag.className = 'mwi-vol-tag';
        tag.textContent = formatNumber(vol);
        itemContainer.appendChild(tag);
    }

    function addVolumeOverlaysToAll() {
        var containers = document.querySelectorAll('[class*="Item_itemContainer"]');
        containers.forEach(function(container) {
            addVolumeTag(container);
        });
    }

    // ===== 市场详情页：在选中物品的详情区显示均价和成交量 =====

    function addDetailOverlay() {
        // 找到详情区域的容器
        var infoContainer = document.querySelector('[class*="infoContainer"]');
        if (!infoContainer) return;

        // 找到当前选中物品的元素
        var currentItem = infoContainer.querySelector('[class*="currentItem"]');
        if (!currentItem) return;

        // 从选中物品的图标里拿到物品ID
        var itemId = getItemIdFromElement(currentItem);
        if (!itemId) return;

        var data = marketDataMap[itemId];
        if (!data) return;

        // 清除旧的详情叠加（如果有）
        var oldStats = infoContainer.querySelector('.mwi-detail-stats');
        if (oldStats) {
            // 如果已有且是同一物品，不重复创建
            if (oldStats.getAttribute('data-item-id') === itemId) return;
            oldStats.remove();
        }

        // 创建详情信息框
        var statsDiv = document.createElement('div');
        statsDiv.className = 'mwi-detail-stats';
        statsDiv.setAttribute('data-item-id', itemId);

        var avgPrice = data.p;     // 24h加权均价
        var totalVol = data.v;     // 24h总成交量
        var totalVal = data.tv;    // 24h总交易额

        statsDiv.innerHTML =
            // 24h均价
            '<div class="mwi-stat-item">' +
            '  <span class="mwi-stat-label">24h均价</span>' +
            '  <span class="mwi-stat-value-price">' + formatNumber(avgPrice) + '</span>' +
            '</div>' +
            // 24h成交量
            '<div class="mwi-stat-item">' +
            '  <span class="mwi-stat-label">24h量</span>' +
            '  <span class="mwi-stat-value-vol">' + formatNumber(totalVol) + '</span>' +
            '</div>' +
            // 24h交易额
            '<div class="mwi-stat-item">' +
            '  <span class="mwi-stat-label">24h额</span>' +
            '  <span class="mwi-stat-value-val">' + formatNumber(totalVal) + '</span>' +
            '</div>';

        // 插入到 currentItem 下方
        // 找 orderBook 然后插在它前面
        var orderBook = infoContainer.querySelector('[class*="orderBook"]');
        if (orderBook) {
            orderBook.parentNode.insertBefore(statsDiv, orderBook);
        } else {
            // 找不到orderBook就直接放到infoContainer末尾
            infoContainer.appendChild(statsDiv);
        }
    }

    // ===== MutationObserver 监听DOM变化 =====

    function startObserver() {
        // 用来防止频繁刷新的定时器
        var volumeTimer = null;
        var detailTimer = null;

        var observer = new MutationObserver(function(mutations) {
            var hasNewNodes = false;
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length > 0) {
                    for (var j = 0; j < mutations[i].addedNodes.length; j++) {
                        if (mutations[i].addedNodes[j].nodeType === 1) {
                            hasNewNodes = true;
                            break;
                        }
                    }
                }
                if (hasNewNodes) break;
            }

            if (hasNewNodes) {
                // 全局成交量标签 - 稍微延迟，避免频繁触发
                if (volumeTimer) clearTimeout(volumeTimer);
                volumeTimer = setTimeout(addVolumeOverlaysToAll, 100);

                // 市场详情 - 也延迟一下
                if (detailTimer) clearTimeout(detailTimer);
                detailTimer = setTimeout(addDetailOverlay, 100);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('[MWI市场叠加] DOM监听已启动');
    }

    // ===== 启动 =====

    injectStyles();
    fetchMarketData();
    startObserver();

    // 定时刷新数据
    setInterval(function() {
        console.log('[MWI市场叠加] 定时刷新数据...');
        // 清除旧叠加
        document.querySelectorAll('.mwi-vol-tag, .mwi-detail-stats').forEach(function(el) {
            el.remove();
        });
        fetchMarketData();
    }, CONFIG.REFRESH_INTERVAL);

    console.log('[MWI市场叠加] 脚本已启动！');
})();
