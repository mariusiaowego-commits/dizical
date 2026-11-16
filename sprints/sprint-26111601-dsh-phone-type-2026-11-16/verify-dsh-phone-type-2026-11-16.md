---
type: sprint
sprint: "26111601"
date: 2026-11-16
status: 已完成
---

# 验收 · 手机端字号 v3.53

测量面：`/practice?tab=dsh`，Jinja 渲染挂在 `127.0.0.1:8791`，headless Chrome，`deviceScaleFactor: 1`。不连库，不碰 8765。

## 缩放未改

| 视口 | k | 设计宽 | 横向溢出 |
|---|---|---|---|
| 440×956 | 0.9273 | 440 | 0 |
| 393×852 | 0.8205 | 440 | 0 |
| 390×844 | 0.8136 | 440 | 0 |
| 744×1133 | 0.9570 | 744 | 0 |

## 手机 CSS 字号（三档相同，视觉 = CSS × k）

| 元素 | 改前 | 改后 CSS | 440 视觉 | 390 视觉 |
|---|---|---|---|---|
| 品牌 | 13px | 18px | 16.7 | 14.6 |
| 待选 | 8px | 12px | 11.1 | 9.8 |
| 顶栏药丸 | 11px | 14px | 13.0 | 11.4 |
| 未选择科目 | 11.5px | 16px | 14.8 | 13.0 |
| 快选 | 11.5px | 15px | 13.9 | 12.2 |
| 选择科目 | 9px | 13px | 12.1 | 10.6 |
| 开始 | 15px（v3.52） | 16px | 14.8 | 13.0 |

## iPad 未被带上

744 画布：品牌仍 13.5px，芯片仍 8.5px，`cz-vp440` 为假。Q 卡头仍 15px，B 预设仍 12.5px，D 刻度仍 9px。

## 卡片抽查（440，组合 5）

- A `cz-vp440` 真，开始按钮 16px。
- B `data-vp=440`，预设 15px，拍点标签 13px。
- Q 卡头 18px，要求正文 17px。
- D 科目行 15px，刻度 12px。
- R 四列：本轮组合没有挂上 R 卡，也没有真实 session 行。规则已写入，实测记 `skipped`。

## 测试

`pytest tests/test_practice_dsh.py tests/test_practice_dsh_save.py tests/test_practice_dsh_popout_data.py` → 53 passed。


## 生产

- 部署包 `.cloudrun-deploy` 196M，无 `*.db`。`practice-dsh.html` md5 `c4f766beb001f39edaec543adc3a2465` 与 `main` `c8d8da9` 一致。Dockerfile / .dockerignore / schema_mysql.sql / cloudrun.yaml / requirements.txt 与 HEAD 一致。
- `tcb cloudrun deploy` 选了不灰度。新版本 `dizical-prod-163`，Status `normal`，FlowRatio `100`，CurrentReplicas 1。BuildId `2612858672`，RunId `multi_tenant_1xSmmTKeFn0wAG`。旧版 162 FlowRatio 0。
- `GET /health/live` → 200 `{"status":"alive"}`
- `GET /health/ready` → 200 database ok，lesson_count 37，cos_ok true，badge_store cos。
- `GET /practice-dsh` → 302 `/login?redirect=/practice-dsh`，无 `X-Dsh-Build`。记 **skipped**，不是 passed。
