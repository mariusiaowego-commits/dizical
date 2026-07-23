# API 变更日志 (dizical ↔ dizical-minip)

> 记录所有可能影响 dizical-minip 小程序的后端 API 变更。
> 每次 dizical 后端 API 变更后，在此登记，然后去 dizical-minip 做对应检查/修复。

---

## 2026-07-23 · 确认上课接口兼容 JSON body

| 项 | 值 |
|----|----|
| **PR** | [#163](https://github.com/mariusiaowego-commits/dizical/pull/163) |
| **Commit** | 28efd63 |
| **影响 API** | `POST /config/api/lessons/confirm` |
| **变更类型** | ✅ 向后兼容（纯新增支持，不破坏原有调用） |
| **需要 minip 同步？** | ❌ 不需要 |
| **备注** | 原接口只支持 query 参数 `?date=...`，前端传 JSON body 导致 422 错误。修复后同时兼容两种调用方式。 |

---

## 登记规范

每次后端 API 修改后，按以下格式登记：

```
## YYYY-MM-DD · 变更摘要

| 项 | 值 |
|----|----|
| **PR** | PR 链接 |
| **Commit** | commit hash |
| **影响 API** | 路径 + 方法 |
| **变更类型** | 🔴 不兼容 / 🟡 部分兼容 / ✅ 完全兼容 |
| **需要 minip 同步？** | ✅ 需要 / ❌ 不需要 |
| **备注** | 变更内容，影响范围 |
```

### 变更类型说明

- 🔴 **不兼容**：参数名/结构变化、返回字段删除、HTTP 方法改变 → minip 必须改代码
- 🟡 **部分兼容**：新增可选参数、新增返回字段 → 不改也能跑，但建议同步
- ✅ **完全兼容**：bug fix、新增校验、新增接口、内部逻辑优化 → minip 无需改动
