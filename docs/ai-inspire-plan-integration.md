# 小程序成长计划 AI 资源包接入方案 — dizical

> 状态：规划稿（v1），待 dad 拍板后转 sprint
> 实测依据：2026-09-04 MCP 查询 `DescribeEnvPostpayPackage` 实况

## 0.1 dad 决策记录

| 日期 | 决策 | 含义 |
|---|---|---|
| 2026-09-18 | **保留，继续推进**（不走"删/移出"） | 这条共识做到一半的 sprint 后续有空继续；骨架代码留在仓库 `dizical-ai/`，不删。该服务从未 commit，因此没有可保留/可删的分支 —— 现状即"本地骨架"，等下次续做时再决定入库方式（独立仓 / 并入本仓 / 先只提交源码 + 忽略 node_modules）。 |

## 0. 实测结论（先读这个）

| 项 | 值 |
|----|----|
| 环境 | `cloud1-d4gfwyvsk1435e2e4`（个人版，小程序绑定，主力） |
| Token 额度 | `pkg_hunyuan_token_la_inspire_1b` = **1,000,000,000 全部剩余**（10亿） |
| 生图额度 | `pkg_hunyuan_ai_image_la_inspire_100k` = **100,000 全部剩余**（10万张） |
| 有效期 | 均到 **2027-01-18**（剩约 4 个月） |
| 状态 | `Status:0` 正常，额度已自动到账，无需领取 |
| Target | `hunyuan-exp.la-inspire-plan`（成长计划 AI 资源包） |

**结论：额度已躺在 env 上，随时可用。** 只用走"允许来源"（云开发服务端），不会被封。

## 1. 允许来源（红线）

成长计划 AI 资源包（Token + 生图）**仅限以下来源**，否则违规会导致"暂停 AI 资源包使用权限"：
1. 小程序基础库 `wx.cloud.extend.AI`
2. **云开发服务端**：云函数 / 云托管，用 `wx-server-sdk` / `@cloudbase/node-sdk` / `@cloudbase/js-sdk`
3. 云开发控制台

dizical 后端 = **CloudBase 云托管（CloudRun）** → 正好属于来源 2，合规。

## 2. 落地方式：B 路（云托管后端加路由，非云函数）

**为什么 B 优于 A**：dizical 是 Python/FastAPI 后端 + 数据全在云 MySQL，云托管后端已连好数据，加路由即可直接读练习数据拼 prompt；云函数（A）需另配数据链路或回调后端，多一跳且难读复杂业务数据。A 只适合"完全独立、不依赖现有数据的纯工具"，不适用本项目。

## 3. ⚠️ B 路的技术现实（必须先摊开）

dizical 后端是 **Python/FastAPI**，而 CloudBase AI SDK（`@cloudbase/node-sdk` / `wx-server-sdk`）是 **Node.js**，只支持 Node 云函数 / Node 云托管。

**两条化解路径**：

### 路径 3A：新增一个 Node 云托管服务（推荐）
- 在 CloudBase 环境里**新开一个 Node.js 云托管服务**（如 `dizical-ai`），专门跑 AI 能力。
- 它通过 `@cloudbase/node-sdk` 调 `ai.createModel("cloudbase")`，并连云 MySQL 读练习/徽章数据。
- Python 主后端通过内部 HTTP 或事件调它；dizical 外部走 `callContainer` 打到 AI 服务。
- 优点：Node SDK 是官方一等公民，生图模型 `HY-Image-3.0-Plus` 也能用；职责单一（AI 服务），干净解耦。
- 缺点：多一个服务要部署/运维。

### 路径 3B：Node 独立服务旁挂（同镜像 or 独立容器进程）
- 在现有 Docker 镜像里同样装一层 Node，或放在 sibling 目录作为独立容器进程。
- 服务端逻辑可直接复用现有 06 数据模型 env（`~/.dizical/.env` 已有大量变量可复用）。

> 我的推荐：**3A（独立 Node 云托管服务）**。理由见 §7 权衡表。

## 4. 生图 badge — 完整方案（你想要的那份）

dizical 现有一套成熟的"程序化 badge 生成"：
- `badge_workflow.py:/api/badge/ai-draft` → 调 `draft_placeholder`（hermes）产出**英文 enamel pin 描述文本**
- `badge_generator.py` + `badge_portal.py` → 程序化拼底图/文字/金属描边，出 enamel-pin 风格图
- `cos-python-sdk-v5` → 直传 COS 拿永久 URL

**关键判断**：现有是"程序化拼图 + 专属美术风格"。生图模型（`HY-Image-3.0-Plus`）是"扩散式 AI 出图"，默认风 = 混元默认风，**_不是_ dizical 专属 enamel-pin 风格**。

**要做成"新开发一套接入生图模型"，必须靠"图生图（I2I）垫图"+ 精心 prompt** 逼近专属风格。方案：

### 4.1 数据流（生产级，永久保存）
```
小程序/前端 → callContainer → dizical-ai(Node 云托管)
  → 读云 MySQL 取 badge name/zh_story
  → 拼 I2I prompt（含前一个程序化的 enamel-pin 样例图作为 image_urls 垫图）
  → ai.createImageModel("hunyuan-image").generateImage({model:"HY-Image-3.0-Plus...", ...})
  → 生图 URL（24h 有效，必须立即传 COS）
  → 云存储永久 fileID → 前端 wx.cloud 直接可读
```
- 生图**只支持服务端调用**（云函数/云托管）✅ 合规
- 生成 URL **24 小时失效** → 必须 `上传至云存储拿永久 fileID`（cos-sdk 已有）

### 4.2 可选排版合成
- 若想让 badge 底图带文字/元素（当前程序化做的），可在 I2I 产出后，再用 COS 上的图 + 现有 `badge_generator` 文字层叠加合成，兼顾"AI 视觉 + 程序化可控文字"。做与不做由 dad 拍板。

### 4.3 风格逼近策略（I2I 垫图）
- 用现有程序化生成的 1 张 enamel-pin badge（白色底、抛光金边、釉彩填色）作为 `image_urls` 参考图
- prompt 里写清：`emoji-adjacent 3D enamel pin, polished gold borders, glossy enamel fills, vibrant colors, white background`
- `revise:{value:true}` 开启 prompt 改写提升效果
- 型号：文生图 `HY-Image-3.0-Plus-4090-Tob-v1.0`（含尺寸/prompt 改写/thinking）；图生图 `HY-Image-v3.0-I2I-ToB-v1.0.1`
- 尺寸：badge 方形用 `1024x1024`；如需 16:9 报告头图用 `1280x720`

### 4.4 关键参数速查
| 参数 | 说明 |
|----|----|
| prompt | ≤500 字（overview 限制） |
| size | `1024x1024` / `1280x720` / `720x1280` / `1280x1280` |
| revise | `{value:true}` 开启（+30s 耗时） |
| 超时 | ❗ 生图建议服务端 timeout ≥ 900s（image 10-30s + 网络） |
| 垫图 | `image_urls` / `images`（base64），≤10MB，jpg/jpeg/png，最多 1 张 |

## 5. AI 文本能力（同生于这 10 亿 token）— 待 dad 选，一并规划

- **学情点评**：练习记录 → hy3 生成家长可读的点评/建议
- **周报/月报**：weekly_assignments + 练习数据 → 自动生成周报文字稿
- **曲目/技巧答疑**：孩子或家长问"这曲怎么练" → hy3 回答
- **练习鼓励/趣味化**：打卡数据 → 生成有温度的鼓励语

这些可放在同一个 `dizical-ai` Node 服务里，复用一条链路上线。

## 6. Node SDK 版本 / 调用要点（对接时查）

- `@cloudbase/node-sdk >= 3.16.0`；**生图需 `>= 3.18.3`**；依赖 `@cloudbase/ai >= 2.30.0`（内置 `HY-Image-3.0-Plus` 配置）
- 文本：`ai.createModel("cloudbase")` → `generateText` / `streamText`，`model:"hy3"`
- 生图：`ai.createImageModel("hunyuan-image")` → `generateImage`（仅 Node SDK）
- 初始化：云托管内 `tcb.init({env, timeout})`；独立服务需 `secretId/secretKey`（在 `~/.dizical/.env` 有相关，腾讯云 CAM）
- 额度耗尽处理：生图额度耗尽 → 无法用套餐抵扣，切其他图片提供商；Token 耗尽可升级资源点套餐或换 `deepseek-v4-flash` 等

## 7. 权衡表：路径 3A vs 3B

| | 3A 独立 Node 云托管 | 3B 旁挂 Node 进程 |
|---|---|---|
| 官方支持度 | ✅ Node SDK 一等公民 | 需手动搭 Node |
| 生图模型 | ✅ 原生 | ✅ 同 |
| 数据访问 | 连云 MySQL 或代理 | 需 Proxied |
| 运维 | 多一个服务 | 集成进现有镜像 |
| 解耦 | 干净 | 混在主后端 |
| 推荐 | ⭐ 推荐 | 可选 |

## 8. 待 dad 拍板事项

1. 走 **3A（独立 Node 云托管 `dizical-ai`）** 还是 3B？
2. 生图 badge 是**纯覆盖式**（I2I 全出，替代现有程序化图）还是**混合式**（AI 底图 + 程序化文字叠加）？
3. 是否把"学情点评/周报/答疑"这些 AI 文本能力并入同一次 sprint（一个 `dizical-ai` 服务统一承载）？
4. 微信小程序端调用入口：复用现有 `callContainer`（走 `dizical-ai` 服务）即可？还是单独 `wx.cloud` 直连？

拍板后转 sprint：Obsidian vault sprint 文件夹 + PLAN + 双写（主仓 docs + Obsidian），按 sprint-workflow 走。

## 附：本期已接好的东西

- CloudBase MCP：`cloud1-d4gfwyvsk1435e2e4` READY
- 10 亿 token + 10 万张生图额度：已确认挂账、全剩余、到 2027-01-18