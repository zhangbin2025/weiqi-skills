# MEMORY.md - 工作规则与重要事项

## 技能包修改规则 ⚠️

**重要原则**：修改技能包时，只修改 `workspace/` 目录下的技能包，**不要**修改 `workspace/skills/` 目录下的技能包。

### 原因
- `skills/` 目录是被忽略的子模块/引用目录
- `workspace/` 下的技能包才是实际工作的副本
- 两者可能不同步，修改 `skills/` 下的文件会导致提交丢失

### 正确做法
1. 修改前确认路径：`~/.openclaw/workspace/<skill-name>/`
2. 而不是：`~/.openclaw/workspace/skills/<skill-name>/`
3. 提交时也在 `workspace/<skill-name>/` 下提交

### 错误案例
2026-03-23：用户要求修改 weiqi-yunbisai 技能包，我误改了 `skills/weiqi-yunbisai/scripts/query.py`，导致修改无法提交到正确的位置。后已纠正。

---

## 其他工作规则

（待补充）
