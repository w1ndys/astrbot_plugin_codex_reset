# Codex 重置监控

AstrBot 插件 `astrbot_plugin_codex_reset` `0.1.0`。只读请求 [codex-reset.com](https://codex-reset.com) 的时间线和预测，把已宣布的额度重置推到 WebUI 里开启的 OneBot 群。

开哪些群在插件页面增删改查，不使用群口令。

## 现在会做什么

- 按配置间隔轮询 `/api/timeline` 和 `/api/forecast`。两个接口都成功才判定。
- 已宣布的新重置，或 `last_reset_at` 向前移动，推送到已开启且能定位会话的群。
- 第一次成功拉取只记下当前最新位置，不推历史。
- 插件页面可以新增、修改、删除监控群，并查看最近一轮轮询。
- 群从关到开，或从开到关，会在该群发一条状态通知。只改备注不发。

## 用到的字段

请求都是 GET，不需要 API Key。

| 路径 | 用到的字段 |
|---|---|
| `/api/timeline` | `events[].id`、`group`、`announcement_state`、`summary`、`url`、`announced_at` |
| `/api/forecast` | `last_reset_at`。`probabilities.rounded_24h`、`rounded_48h` 只在页面展示 |

推送条件：

- `group == "reset"` 且 `announcement_state == "announced"` 的新事件
- `last_reset_at` 比已记下的时间更晚，且没有对应的新宣布事件

概率升高不算重置。缺 `announcement_state` 也不算。已见位置用 `last_seen_id`、宣布时间和 `last_reset_at` 去重，先落库再推送。推送失败不回滚，避免下一轮重复推。

## 轮询和署名

最快每分钟 1 次。配置小于 60 秒也按 60 秒执行，并遵守响应头 `Cache-Control: max-age` 和 429 的 `Retry-After`。

请求带可识别的 User-Agent。默认是 `astrbot_plugin_codex_reset/0.1 (github.com/w1ndys)`，可在插件配置里改。

重置推送、开关通知和页面状态都署名 `Data: codex-reset.com`，并带上 `https://codex-reset.com`。

## 群和会话

没在表里的群不会收到推送。关闭的群不接收重置推送；关掉的当下仍会收到一条关闭通知。

会话串格式是 `平台ID:GroupMessage:群号`。插件配置里的 OneBot 平台实例 ID 不含冒号。填了之后，开启的群可以不先说话就推。留空时，要等这个群先来一条消息，插件记下真实会话后再推。发不出通知时，页面会写明群状态已保存，但群里没有发出通知。

## 安装

放到 `AstrBot/data/plugins/astrbot_plugin_codex_reset`，在 WebUI 重载。依赖见 `requirements.txt`。

```bash
python3 -m unittest discover -s tests -t .
```
