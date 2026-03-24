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

---

## 用户偏好 📌

### 文件发送方式
**用户明确要求：优先直接发送文件，不要生成链接**

- ❌ **不要**使用 `lightclaw_upload_file` 生成下载链接
- ✅ **必须**使用 `message` 工具直接发送文件
- 原因：上传链接经常无法访问（需要特定 referer、过期快、区域限制）
- 即使文件较大或发送可能失败，也要优先尝试直接发送
- 只有直接发送彻底失败时，才询问用户是否接受链接

**注意**：每次会话重置后，系统可能默认 fallback 到链接，我必须主动覆盖这个行为，优先直接发送。
