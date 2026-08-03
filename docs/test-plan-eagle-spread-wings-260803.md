# Sprint 05 — 雄鹰展翅 Test Plan (260803)

> **AI 标注:** 本 test plan 由 coder agent 生成, 镜像到 Obsidian `tqob/05-Coding/project-dizical/sprints/sprint-05-eagle-spread-wings-2026-08-03/test-plan-eagle-spread-wings-2026-08-03.md`.

## 测试策略

immediate + achieved_at_override 模式不参与 calc (sprint 04 PR #218 修过 calc 路径, 由 `badges_page` 走 `is_commemorative` fallback). 不需要新单测. 浏览器 API 集成验证即可.

## 集成验证 (curl /badges)

重启服务后:

```bash
curl -s http://localhost:8765/badges | python3 -c "
import sys, re, json
html = sys.stdin.read()
m = re.search(r'const DATA = (\[.*?\]);', html, re.DOTALL)
data = json.loads(m.group(1))
for b in data:
    if b['id'] == 'eagle_spread_wings':
        print(f\"{b['id']}: achieved={b['achieved']} achieved_at={b['achieved_at']}\")
        print(f\"  condition={b['condition']}\")
        print(f\"  cond_text={b['cond_text']}\")
        print(f\"  badge_url={b['badge_url']}\")
        break
"
```

期望:

- `achieved=True`
- `achieved_at='2026-08-03'`
- `condition='考出时间: 2026-08-03'`
- `cond_text='把《萨丽哈》整首背出来, 你的笛声像草原的雄鹰一样响亮啦!'`
- `badge_url='/static/badges/eagle_spread_wings.png'`

## PNG 200 OK

```bash
curl -s -o /dev/null -w '%{http_code} size=%{size_download}\\n' \
  http://localhost:8765/static/badges/eagle_spread_wings.png
```

期望: `200 size=1497515`

## 浏览器验证 (dad 走)

```
1. http://localhost:8765/badges (Cmd+Shift+R 强刷)
2. 顶部 tab 仍是 3 个: 🏆 成就 / 🎵 考级 / 🌟 赛季
3. 🏆 成就 tab 往下滚, 找 "雄鹰展翅" (sort_order 37, 在 recovery 21 后面)
4. 卡片金色未锁 + chibi 蓝衣女孩举鹰图
5. 点开 modal:
   - 标题 "雄鹰展翅"
   - 副标 "突破"
   - 条件 "考出时间: 2026-08-03"
   - 描述 "草原上, 哈萨克女孩萨丽哈学雄鹰展翅飞..."
6. 🏆 成就 tab 已解锁区总数 +1
```

## 全套 pytest

跑全套确认 baseline 没破:

```bash
python3 -m pytest tests/ -q
```

期望: 14 pre-existing failed 保持原状, 0 新增 regression.

## 不需要新单元测试

immediate + achieved_at_override 模式由 app.py:badges_page 直接处理 (calc 不参与), 跟 swallow_triumph / grade_1 同模式. sprint 04 PR #218 已修复 calc 流程让 immediate badge 走对路径. 没有 calc 逻辑可测.