# 0001: Agent 的入口是 CLI 包装器 skill，而不是新 CLI

MediaCrawler 已有成熟的 `uv run main.py` 命令行入口和配套文档。为了让 AI 智能体能驱动它，参考 HKUDS/CLI-Anything 的"让软件 agent-native"思路（已有 CLI 时，skill 就是 agent 的入口），我们决定：**不重写 CLI、不改核心代码**，而是在全局技能目录放一个 `mediacrawler` skill，由 Runner（`mediacrawler_runner.py`）把智能体友好的参数名翻译成 main.py 的参数并执行。

选它而非"给 main.py 加 JSON 输出"或"新建一套 CLI"，是因为：核心采集链路已实测可用且不宜为交互层动刀；包装层独立于仓库，可随 agent 宿主（opencode/Claude Code 等）迁移复用；改动可逆、无侵入。

Status: accepted