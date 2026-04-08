---
name: milkyway-userscript
description: 帮用户写 Milky Way Idle 游戏的 Tampermonkey 油猴脚本，以及一切跟 MWI 游戏 UI 增强、市场数据展示、游戏内插件相关的工作。当用户提到 MWI、milkywayidle、milky way idle、油猴、Tampermonkey、用户脚本、想给游戏加功能、想在游戏界面展示数据、想做市场决策辅助时使用此 skill。
---

# Milky Way Idle 油猴脚本助手

## 用户背景
- 用户在玩 Milky Way Idle，角色 ID 94905，游戏地址 https://www.milkywayidle.com/game
- 用户**前端 0 基础**，代码要写得啰嗦、每行加中文注释，不能假设他懂 JS/DOM/React 概念
- 用户对 token 消耗敏感（Pro 套餐），**严禁使用 Playwright MCP 等浏览器接管方案**
- 协作模式：用户在自己浏览器里 F12 截图 / 跑 Console JS → 把结果粘贴回来 → AI 写代码 → 用户测试 → 报错粘回来迭代
- 用户已有市场数据采集器项目，就在本目录（D:\CODE\milkyway-market\）

## 技术约束（写脚本时必须遵守）

1. **MWI 是 React 单页应用**，DOM 是动态生成的
   - 必须用 `MutationObserver` 监听容器变化，而不是脚本启动时一次性 querySelector
   - 不要假设元素一定存在，要做 null check

2. **核心数据走 WebSocket，不走 HTTP**
   - 想抓游戏实时数据（战斗、掉落、市场成交）的标准做法是 hook `WebSocket.prototype.send` 和 `addEventListener('message', ...)`
   - hook 时用 Object.defineProperty 或保存原方法包一层

3. **CSS 选择器要用稳定特征**
   - ❌ 不要用 `.css-x8j7f2` 这种自动生成的 className（每次构建会变）
   - ✅ 用 `aria-label`、文本内容（textContent 包含 X）、`data-*` 属性、相对结构

4. **跨域请求用 GM_xmlhttpRequest**
   - 普通 `fetch` 会被 CORS 卡住
   - 必须在 `// ==UserScript==` 头里声明 `@grant GM_xmlhttpRequest` 和 `@connect 目标域名`
   - 想从用户的 GitHub 仓库拉市场数据时，`@connect raw.githubusercontent.com`

5. **绝不写自动化点击/挂机/自动战斗类功能**
   - 违反游戏 ToS，会导致用户账号被封
   - 即便用户主动要求，也要先警告风险并劝阻

## 标准工作流（每次写新脚本都按这个顺序）

### 第 1 步：搞清需求
问用户三个问题：
- 想在游戏哪个页面加东西？（市场 / 战斗 / 背包 / 任务）
- 想展示什么信息或实现什么功能？
- 数据从哪来？（游戏自身 API / 用户的市场数据仓库 / 第三方）

### 第 2 步：让用户做侦察
不要凭空猜 DOM 结构。让用户：
1. 打开游戏对应页面
2. 按 F12 截 1-2 张关键截图发过来
3. 在 Console 跑一段你给的 5-10 行侦察 JS（打印关键容器的 outerHTML 摘要、aria-label、文本结构）
4. 把输出粘回来

### 第 3 步：写脚本
按这个模板组织代码：

```javascript
// ==UserScript==
// @name         脚本名（中文）
// @namespace    https://github.com/用户名/项目
// @version      0.1.0
// @description  一句话说明
// @match        https://www.milkywayidle.com/*
// @grant        GM_xmlhttpRequest
// @connect      raw.githubusercontent.com
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    // ===== 配置区 =====
    const CONFIG = {
        // 用户可能要改的常量都集中放这里
    };

    // ===== 工具函数 =====
    // 每个函数前面写一行中文注释说它是干嘛的

    // ===== 主逻辑 =====
    // 用 MutationObserver 等 DOM 准备好后再注入
})();
```

每个函数前面写一行中文注释，每个不显然的步骤行内加注释。**写代码的目标是用户能看懂、能改，而不是炫技。**

### 第 4 步：让用户测试
告诉用户：
1. 打开 Tampermonkey → 创建新脚本 → 粘贴 → Ctrl+S 保存
2. 刷新游戏页面
3. 看效果，有报错按 F12 → Console 截图发过来
4. 看不到效果也截 Console 图发过来（很可能是选择器没对上）

### 第 5 步：迭代
根据报错或截图调整。**不要重写整个文件，用 Edit 工具只改坏掉的部分。**

## 跟市场数据项目的对接

用户的市场数据采集器（本目录的 `query.py` 和 `.github/workflows/fetch_market.yml`）会定时把游戏 marketplace.json 推到 GitHub。脚本要用历史数据时：

```javascript
GM_xmlhttpRequest({
    method: 'GET',
    url: 'https://raw.githubusercontent.com/用户名/milkyway-market/main/data/latest.json',
    onload: function(response) {
        const data = JSON.parse(response.responseText);
        // 用 data 做事
    }
});
```

⚠️ 注意：截至 skill 创建时（2026-04-08），市场数据项目**还没有推到 GitHub**，所以暂时没有可用的远程数据源。第一阶段的脚本要么走"当前快照"路线（直接读游戏自己的 marketplace.json），要么先催用户把项目推上去。

## 常见坑

- **脚本不执行**：检查 `@match` 是否对、Tampermonkey 里脚本是否启用、是否被广告屏蔽插件干掉
- **元素找不到**：99% 是 MutationObserver 没用对，或者选择器用了易变的 className
- **CORS 报错**：忘了加 `@grant GM_xmlhttpRequest` 或 `@connect`
- **UI 注入了但没刷新**：React 重渲染会把你注入的 DOM 干掉，要么在 Observer 里持续重注入，要么改用 Portal/Shadow DOM
