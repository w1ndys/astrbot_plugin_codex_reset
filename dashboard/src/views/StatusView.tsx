// 页面层：轮询状态。只读后端内存里的最近一轮，不额外请求来源。

import { useEffect, useState } from "react";
import { App as AntdApp, Button, Card, Descriptions, Tag } from "antd";
import { apiGet, readError } from "../bridge";
import { rawUtcTitle, showRate, showTime } from "../time";
import type { StatusResponse } from "../types";

// 只用到两个方法，避免深层导入 antd 的内部类型
interface Notice {
  error: (text: string) => void;
}

async function fetchStatus(): Promise<StatusResponse> {
  // 不额外打来源，避免突破每分钟 1 次
  return apiGet<StatusResponse>("status");
}

function useStatus(notice: Notice) {
  // 最近一轮状态和加载态。刷新只重新读后端内存，不再打来源
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 只跑一次：切回来时组件已销毁重建，会重新读
    let cancelled = false;
    fetchStatus()
      .then((data) => {
        // 已经切走这个 Tab 时不要再写状态
        if (!cancelled) {
          setStatus(data);
        }
      })
      .catch((error) => {
        notice.error(readError(error));
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function refresh(): Promise<void> {
    setLoading(true);
    try {
      setStatus(await fetchStatus());
    } catch (error) {
      notice.error(readError(error));
    }
    setLoading(false);
  }

  return { status, loading, refresh };
}

function buildItems(data: StatusResponse | null) {
  // 九个字段到人话的映射。还没基线时要说清为什么不推历史
  return [
    {
      key: "baseline",
      label: "基线",
      children: data?.baselined ? (
        <Tag color="green">已完成</Tag>
      ) : (
        <Tag color="orange">还没有，第一次成功拉取只记位置</Tag>
      ),
    },
    { key: "seen", label: "上次见到的事件", children: data?.last_seen_id || "无" },
    {
      key: "reset",
      label: "上次重置时间",
      // 后端给的是 UTC，这里按访问者本地时区显示
      children: (
        <span title={rawUtcTitle(data?.last_reset_at || "")}>
          {showTime(data?.last_reset_at || "")}
        </span>
      ),
    },
    {
      key: "rate24",
      label: "未来 24 小时重置概率",
      // 概率只是展示，不代表已经重置
      children: showRate(data?.rounded_24h ?? null),
    },
    {
      key: "rate48",
      label: "未来 48 小时重置概率",
      children: showRate(data?.rounded_48h ?? null),
    },
    {
      key: "poll",
      label: "最近一轮时间",
      children: (
        <span title={rawUtcTitle(data?.last_poll_at || "")}>{showTime(data?.last_poll_at || "")}</span>
      ),
    },
    { key: "count", label: "最近一轮推送条数", children: data?.last_message_count ?? 0 },
    { key: "error", label: "最近一轮错误", children: data?.last_error || "无" },
    {
      key: "source",
      label: "数据来源",
      children:
        (data?.source_label || "Data: codex-reset.com") +
        " " +
        (data?.source_url || "https://codex-reset.com"),
    },
  ];
}

export function StatusView() {
  // message 从 useApp 取；静态调用不跟随宿主明暗主题
  const { message } = AntdApp.useApp();
  const { status, loading, refresh } = useStatus(message);

  return (
    <Card
      title="轮询状态"
      loading={loading}
      extra={
        <Button size="small" onClick={refresh}>
          刷新
        </Button>
      }
    >
      <p className="hint">时间按访问者本地时区显示，括号里是时区偏移，鼠标悬停可以看到后端的 UTC 原值。</p>
      <Descriptions column={1} bordered size="small" items={buildItems(status)} />
    </Card>
  );
}
