# 测试包。从插件目录的上一级导入包名 astrbot_plugin_codex_reset。
import sys
from pathlib import Path

PARENT = str(Path(__file__).resolve().parents[2])
# 重复插入会让后导入的测试拿到错误的包
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
