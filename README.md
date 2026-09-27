# Codex 重置监控

独立 AstrBot 插件。只读 [codex-reset.com](https://codex-reset.com) 的公开接口，把已宣布的额度重置推到 WebUI 里开启的 OneBot 群。

第一版没有飞书，也没有群口令。开哪些群在插件页面增删改查。

## 端点

全部 GET、只读，不需要 API Key。

| 路径 | 用途 | 本插件用到的字段 |
|---|---|---|
| `/api/timeline` | 已验证事件，倒序 | `events[].id`、`group`、`announcement_state`、`summary`、`url`、`announced_at` |
| `/api/forecast` | 未来重置概率 | `last_reset_at`。`probabilities.rounded_24h` / `rounded_48h` 只展示 |
| `/api/feed` | Tibo 公告 | 第一版不拉 |
| `/api/status-history` | 服务状态 | 第一版不拉 |

MCP 为 `https://codex-reset.com/mcp`，工具是 `get_reset_forecast`、`get_reset_timeline`、`get_codex_status`。本插件走 REST，不走 MCP。

## 重置判定

推送只在下面两种情况发生：

- `/api/timeline` 里出现 `group == "reset"` 且 `announcement_state == "announced"` 的新事件
- `/api/forecast` 的 `last_reset_at` 比已记下的时间更晚，且没有对应的新宣布事件

概率升高不算重置。缺 `announcement_state` 也不算。

第一次成功拉取只把当前最新位置记成基线，不把历史重置推出去。之后用 `last_seen_id`、宣布时间和 `last_reset_at` 去重。位置先落库再推送；推送失败不回滚，避免下一轮重复推。

## 轮询和署名

最快每分钟 1 次。配置小于 60 秒也会按 60 秒执行，并继续遵守响应头 `Cache-Control: max-age` 和 429 的 `Retry-After`。

请求必须带可识别的 User-Agent。默认是 `astrbot_plugin_codex_reset/0.1 (github.com/w1ndys)`，可在插件配置里改。

每条推送和页面状态都署名 `Data: codex-reset.com`，并带上 `https://codex-reset.com`。

## WebUI

插件页面 `groups`：

- 新增群号和备注
- 改备注、开或关
- 删除
- 看最近一轮轮询有没有基线、有没有错误

没在表里的群不会收到推送。

主动推送要用 AstrBot 会话串，格式是 `平台ID:GroupMessage:群号`。在插件配置填写 OneBot 平台实例 ID 后，开启的群可以不先说话就推。平台 ID 留空时，要等这个群先来一条消息，插件记下真实会话后再推。

## 安装

把本仓放到 `AstrBot/data/plugins/astrbot_plugin_codex_reset`，在 WebUI 重载插件。依赖见 `requirements.txt`。

## 检查

```bash
python3 -m unittest discover -s tests -t .
```
