# 右栏卡片唯一真源目录 (`cards/`)

> **唯一真源声明**：  
> 本目录下的 6 个语义命名的 `.html` 文件是右栏卡片的**唯一权威真源**。  
> 以后修改卡片内容、样式或脚本，**只在本目录的文件中修改**。修改完成后，运行 `python3 tools/sync-demo-templates.py` 自动注入到 `canvas-01.html` 中；**严禁直接修改 `canvas-01.html` 内联的 `<template>` 标签**。

---

## 1. 权威源文件清单（仅保留语义命名）

| 模板 ID | 权威源文件 | 说明 |
|---|---|---|
| `tpl-A` | [`card-a-dashboard.html`](card-a-dashboard.html) | A 仪表盘卡片 |
| `tpl-B` | [`card-b-metronome-full.html`](card-b-metronome-full.html) | B 全功能节拍器卡片 |
| `tpl-S` | [`card-s-metronome-strip.html`](card-s-metronome-strip.html) | S 竖条节拍器卡片 |
| `tpl-D` | [`card-d-duration.html`](card-d-duration.html) | D 今日练习时长卡片 (Bauhaus Widget) |
| `tpl-R` | [`card-r-records.html`](card-r-records.html) | R 今日练习记录卡片 |
| `tpl-Q` | [`card-q-requests.html`](card-q-requests.html) | Q 老师要求卡片 (3D Deck) |

*注：目录中仅保留上述 6 个语义命名文件，不保留 `card-a.html` 等重复短名。*

---

## 2. 独立完整 HTML 规范与单卡独立预览

本目录下每个 `card-*.html` 都是**完整的独立 HTML 文档**（包含 `<!DOCTYPE html>`、`<html>`、`<head>`、`<style>`、`<body>`、`<script>`），因为它们在宿主画布中是通过 `iframe.srcdoc` 载入沙箱运行的。

- **浏览器独立预览**：  
  无需通过 `canvas-01.html`，你可以**直接用浏览器打开任意 `card-*.html` 文件**进行快速预览与独立调试（这也是未来 expand 展开模式与 feed 信息流模式单卡独立验证的基础）。
- **禁止添加 `<template>` 标签**：  
  文件内部即为卡片本身完整 DOM/CSS/JS，**严禁在这些文件内部包裹 `<template>` 标签**。向 `canvas-01.html` 的 `<template id="tpl-*">` 注入由同步工具自动完成。

---

## 3. 工作流与自动化命令

1. **修改卡片**：直接编辑 `cards/card-*.html`。
2. **同步注入**：
   ```bash
   python3 tools/sync-demo-templates.py
   ```
3. **校验一致性（CI / 提交前检查）**：
   ```bash
   python3 tools/sync-demo-templates.py --check
   ```
   若返回 code 0 则表示内联模板与权威源 100% 字节级一致；若返回 code 1 则会报告首个差异行号与上下文。
4. **自动化测试套件**：
   - 真正执行的是 Node.js Playwright 测试套件：
     ```bash
     node tools/verify.js
     ```
   - `tools/verify.py` 是便捷入口 Shim（底层直接调用 `node tools/verify.js`）：
     ```bash
     python3 tools/verify.py
     ```

---

## 4. 历史镜像文件状态说明

上级目录中的独立历史文件（`dashboard-skin-01-v3.html`、`metronome-01-v3.html`、`metronome-02-strip.html`、`practice-duration-card-01-v3.html`、`today-records-01.html`、`requests-card-01-v3.html`）**已确认为废弃镜像**，将在 S8 阶段统一清理归档，请勿再行编辑。
