# 实体层：接口地址、轮询下限、署名和库文件名。不含判断逻辑。

API_ORIGIN = "https://codex-reset.com"
TIMELINE_PATH = "/api/timeline"
FORECAST_PATH = "/api/forecast"
SOURCE_LABEL = "Data: codex-reset.com"
SOURCE_URL = "https://codex-reset.com"

# 来源要求服务端请求带可识别的 User-Agent。
DEFAULT_USER_AGENT = "astrbot_plugin_codex_reset/0.1 (github.com/w1ndys)"

# 来源要求最快每分钟 1 次，并遵守 Cache-Control: max-age=60。
MIN_POLL_SECONDS = 60

GROUP_RESET = "reset"
STATE_ANNOUNCED = "announced"

DB_FILE_NAME = "codex_reset.db"
PLUGIN_NAME = "astrbot_plugin_codex_reset"

# 官方会话串格式是 platform_id:message_type:session_id。群消息类型固定这一段。
GROUP_MESSAGE_TYPE = "GroupMessage"

# 群号只接受数字，避免把会话串拼坏。
GROUP_ID_MIN_LEN = 5
GROUP_ID_MAX_LEN = 16
REMARK_MAX_LEN = 40
