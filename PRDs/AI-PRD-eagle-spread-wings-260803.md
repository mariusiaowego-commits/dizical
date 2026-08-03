# Sprint 05 — 雄鹰展翅 PRD (260803)

> **AI 标注:** 本 PRD 由 coder agent 生成, 镜像到 Obsidian `tqob/05-Coding/project-dizical/sprints/sprint-05-eagle-spread-wings-2026-08-03/prd-eagle-spread-wings-2026-08-03.md`.

## 背景

女儿 2026-08-03 完整背出笛子三级考级曲《萨丽哈最听毛主席的话》(文革版哈萨克族民歌). 这是一个值得纪念的突破性成就. dad 想在 `/badges` 勋章墙给她做一个一次性立即获取的徽章.

## 目标

新增 1 个一次性徽章, 立即显示在 `/badges` 成就殿堂.

## 验收标准

- `/badges` 顶部 tab 仍是 3 个 (🏆 成就 / 🎵 考级 / 🌟 赛季)
- 🏆 成就 tab 里找到"雄鹰展翅"卡片:
  - 金色未锁 (显示 achieved 状态)
  - sort_order=37 (在 recovery_first_practice_21 之后)
  - 卡片图: chibi 哈萨克蓝衣辫子女孩双手举金色雄鹰悬头顶
- 点开 modal:
  - 标题: "雄鹰展翅"
  - 副标: "突破"
  - 条件: "考出时间: 2026-08-03"
  - 描述: "草原上, 哈萨克女孩萨丽哈学雄鹰展翅飞..."
- 🏆 成就 tab 已解锁区总数 +1

## 非目标

- 不动其他 badge / calc 路径
- 不动 achievements 表结构
- 不加新 calc 分支 (immediate 模式不需要 calc 参与)
- 不重复生图 (dad 已在 3 个候选里选了 C)

## 关联

- Sprint doc: [[sprint-05-eagle-spread-wings-2026-08-03]]
- Plan: [[plan-eagle-spread-wings-2026-08-03]]
- Tech spec: [[tech-spec-eagle-spread-wings-2026-08-03]]
- Test plan: [[test-plan-eagle-spread-wings-2026-08-03]]
- Verify: [[verify-2026-08-03]]
- PR #221