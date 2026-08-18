# 0002: 采集走 CDP 自启模式并复用已保存登录态

skill 初版的文档要求"Chrome 开启 9222 远程调试后连接"，但实测本机用户的 Chrome（`chrome://inspect` 模式）拒绝 Playwright 上下文管理（报 `Browser context management is not supported`），连接模式在本环境不可用。能稳定跑通的是 **CDP 自启模式**（`CDP_CONNECT_EXISTING=False`）：采集器自行启动 Chrome、自动分配端口、把登录态持久化到独立数据目录。

由此决定：skill 指引智能体确认自启模式，优先复用已保存的登录态（首次扫码后免登录），仅当无登录态时才让用户扫码或提供 cookie 文件。

选它而非连接模式，是因为连接用户的浏览器既不可靠也不隔离（会污染用户会话）；自启模式多花一次启动代价，换取可重复、可隔离的采集。此决策与具体端口、Chrome 版本无关，是模式层面的选择。

Status: accepted