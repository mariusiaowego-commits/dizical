# 工具套件说明 (`tools/`)

本目录包含 dizical demo v38 的护栏测试套件与单一真源模板同步工具。

---

## 1. 自动化验证测试套件

- **核心执行脚本**: [`verify.js`](verify.js)  
  基于 Node.js 与 Playwright Chromium 驱动，实测 3 视口 (1133 / 744 / 440) × 3 组合 (C1 / C2 / C3) 共 9 组全矩阵。换算 iframe 绝对坐标，验证重叠面积、露出比例、文字重叠、弹窗明细、动效无空窗无叠字等 10 项基线断言。
  ```bash
  node tools/verify.js
  ```
- **便捷入口 Shim**: [`verify.py`](verify.py)  
  轻量 Python 包装器（约 390B），内部直接代理执行 `node tools/verify.js`，方便习惯使用 `python3` 的开发者直接调用：
  ```bash
  python3 tools/verify.py
  ```

---

## 2. 单一真源模板同步工具

- **同步脚本**: [`sync-demo-templates.py`](sync-demo-templates.py)
  - **默认同步注入**: 将 `cards/` 权威源按行切片精准注入 `canvas-01.html` 的 6 个 `<template>` 内部：
    ```bash
    python3 tools/sync-demo-templates.py
    ```
  - **一致性比对校验**:
    ```bash
    python3 tools/sync-demo-templates.py --check
    ```
    校验权威源与画布内联模板是否 100% 字节级一致。若不一致输出首个差异行号与上下文并退出码 1。
