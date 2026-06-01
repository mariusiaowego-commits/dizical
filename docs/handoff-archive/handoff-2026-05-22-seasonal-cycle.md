# Handoff 2026-05-22 — feat/seasonal-cycle-clean

## 分支
`feat/seasonal-cycle-clean`（当前 HEAD: `4c0b504`）

## 已完成
1. **seasonal_type 维度** — CalcResult 新增 `seasonal_type` 字段，支持 daily/weekly/monthly/stage 四种周期
2. **_calc_seasonal 重构** — 按 seasonal_type 分支计算，daily=当天打卡、weekly=周累计≥10分钟、monthly=月累计≥60分钟、stage=赛季周期
3. **daily_checkin badge** — DB 记录已插入（achievements 表），seasonal_type=daily
4. **迁移脚本** — `src/migrate_seasonal_cycle.py`，加列 + 更新现有 badge 的 seasonal_type + 插入 daily_checkin

## 未完成（下次开发）
- [ ] **daily_checkin 图片** — 需生成 badge 图片（去背、-u/-l 两版），放到 `src/kid_app/static/badges/`
- [ ] **BADGE_URLS / BADGE_FILES 注册** — `app.py` 两处字典都要加 daily_checkin 映射
- [ ] **迁移脚本执行** — 还没跑过 `python3 src/migrate_seasonal_cycle.py`
- [ ] **类型标注不一致** — 迁移脚本里 full_month/top1/early bird 系列标成了 stage，但代码里还是按自然月算，需对齐
- [ ] **前端展示验证** — badges.html / achievements 页面是否正确显示 daily_checkin
- [ ] **calc_all 验证** — 跑 calc_all() 确认 daily_checkin 计算结果正确

## 注意
- `_calc_seasonal` 的 daily 分支按 `seasonal_type` 判断，不依赖 aid 名，所以 daily_checkin 直接走这个分支
- 迁移脚本未执行前，achievements 表没有 seasonal_type 列，会报错
