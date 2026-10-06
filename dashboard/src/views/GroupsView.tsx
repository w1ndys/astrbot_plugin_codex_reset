// 页面层：监控群。只收集群号、备注和开关；能不能推由后端按会话算。

import { useEffect, useState } from "react";
import { App as AntdApp, Button, Card, Input, Space, Switch, Table, Tag } from "antd";
import type { TableProps } from "antd";
import { apiGet, apiPost, readError } from "../bridge";
import type { GroupListResponse, GroupRow, SavedGroupResponse } from "../types";

// 只用到三个方法，避免深层导入 antd 的内部类型
interface Notice {
  success: (text: string) => void;
  warning: (text: string) => void;
  error: (text: string) => void;
}

// 列定义数组；TableProps 里的类型带 undefined，拼不起来，这里去掉
type GroupColumns = NonNullable<TableProps<GroupRow>["columns"]>;

// 新增时要提交的草稿
interface GroupDraft {
  group_id: string;
  remark: string;
  enabled: boolean;
}

async function fetchGroups(): Promise<GroupRow[]> {
  // 后端按群号排序返回全部行，没记录就是没有推送目标
  const data = await apiGet<GroupListResponse>("groups");
  return data.groups;
}

function useGroupRows(notice: Notice) {
  // 群表、加载态和重新拉取。行内改动由调用方在本地副本上做
  const [rows, setRows] = useState<GroupRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 只跑一次：切回来时组件已销毁重建，会重新拉
    let cancelled = false;
    fetchGroups()
      .then((data) => {
        // 已经切走这个 Tab 时不要再写表格
        if (!cancelled) {
          setRows(data);
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

  async function reload(): Promise<void> {
    // 存完重新拉一次，拿到后端算出来的 can_push
    setRows(await fetchGroups());
  }

  return { rows, loading, setRows, reload };
}

function useGroupActions(notice: Notice, reload: () => Promise<void>) {
  // 三个写操作。notice 非空表示群状态存下了、但群里没通知到
  async function report(result: SavedGroupResponse, done: string): Promise<void> {
    if (result.notice) {
      notice.warning(result.notice);
    } else {
      notice.success(done);
    }
    await reload();
  }

  async function add(draft: GroupDraft): Promise<boolean> {
    try {
      const result = await apiPost<SavedGroupResponse>("groups", draft);
      await report(result, "已添加");
      return true;
    } catch (error) {
      notice.error(readError(error));
      return false;
    }
  }

  async function save(row: GroupRow): Promise<void> {
    try {
      const result = await apiPost<SavedGroupResponse>("groups/update", {
        group_id: row.group_id,
        remark: row.remark,
        enabled: row.enabled,
      });
      await report(result, "已保存");
    } catch (error) {
      notice.error(readError(error));
    }
  }

  async function remove(row: GroupRow): Promise<void> {
    try {
      await apiPost("groups/delete", { group_id: row.group_id });
      notice.success("已删除");
      await reload();
    } catch (error) {
      notice.error(readError(error));
    }
  }

  return { add, save, remove };
}

function GroupsToolbar({ add }: { add: (draft: GroupDraft) => Promise<boolean> }) {
  // 上方一行：群号、备注、开关、添加。只有真的加进去了才清空输入
  const [groupId, setGroupId] = useState("");
  const [remark, setRemark] = useState("");
  const [enabled, setEnabled] = useState(true);

  async function submit(): Promise<void> {
    const ok = await add({ group_id: groupId.trim(), remark: remark.trim(), enabled });
    if (ok) {
      setGroupId("");
      setRemark("");
      setEnabled(true);
    }
  }

  return (
    <Space className="section" wrap>
      <Input
        placeholder="群号，5 到 16 位数字"
        value={groupId}
        style={{ width: "14rem" }}
        onChange={(event) => {
          setGroupId(event.target.value);
        }}
      />
      <Input
        placeholder="备注，可选"
        value={remark}
        maxLength={40}
        style={{ width: "14rem" }}
        onChange={(event) => {
          setRemark(event.target.value);
        }}
      />
      <Switch checked={enabled} onChange={setEnabled} />
      <Button type="primary" onClick={submit}>
        添加
      </Button>
    </Space>
  );
}

function buildInfoColumns(
  editRow: (groupId: string, patch: Partial<GroupRow>) => void,
): GroupColumns {
  // 前五列：群号、备注、开关、会话、能否推送
  return [
    { title: "群号", dataIndex: "group_id", width: "12rem" },
    {
      title: "备注",
      dataIndex: "remark",
      render: (value: string, row: GroupRow) => (
        <Input
          value={value}
          maxLength={40}
          placeholder="可选，最多 40 字"
          onChange={(event) => {
            editRow(row.group_id, { remark: event.target.value });
          }}
        />
      ),
    },
    {
      title: "推送开关",
      dataIndex: "enabled",
      width: "7rem",
      render: (value: boolean, row: GroupRow) => (
        <Switch
          checked={value}
          onChange={(checked) => {
            editRow(row.group_id, { enabled: checked });
          }}
        />
      ),
    },
    {
      title: "已记录会话",
      dataIndex: "has_session",
      width: "8rem",
      // 群里来过消息才有真实会话，没有就靠平台 ID 拼
      render: (value: boolean) => (value ? <Tag color="blue">有</Tag> : <Tag>无</Tag>),
    },
    {
      title: "能否推送",
      dataIndex: "can_push",
      width: "9rem",
      // 关掉的群也不推重置，这里只表示现在发得出消息
      render: (value: boolean) =>
        value ? <Tag color="green">可以</Tag> : <Tag color="orange">不能</Tag>,
    },
  ];
}

function buildActionColumn(
  save: (row: GroupRow) => Promise<void>,
  remove: (row: GroupRow) => Promise<void>,
): GroupColumns {
  // 最后一列：保存和删除
  return [
    {
      title: "操作",
      width: "10rem",
      render: (_value: unknown, row: GroupRow) => (
        <Space>
          <Button size="small" onClick={() => save(row)}>
            保存
          </Button>
          <Button size="small" danger onClick={() => remove(row)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];
}

function buildColumns(
  editRow: (groupId: string, patch: Partial<GroupRow>) => void,
  save: (row: GroupRow) => Promise<void>,
  remove: (row: GroupRow) => Promise<void>,
): GroupColumns {
  // 信息列在前，操作列在后
  return [...buildInfoColumns(editRow), ...buildActionColumn(save, remove)];
}

export function GroupsView() {
  // message 从 useApp 取；静态调用不跟随宿主明暗主题
  const { message } = AntdApp.useApp();
  const { rows, loading, setRows, reload } = useGroupRows(message);
  const { add, save, remove } = useGroupActions(message, reload);

  function editRow(groupId: string, patch: Partial<GroupRow>): void {
    // 只改本地副本，点保存才发给后端
    setRows((current) =>
      current.map((row) => (row.group_id === groupId ? { ...row, ...patch } : row)),
    );
  }

  return (
    <Card title="监控群" loading={loading}>
      <p className="hint">
        列表为空就是没有推送目标。没添加的群不会收到推送。群从关到开、或从开到关时，会在该群发一条状态通知；
        只改备注不发。会话串格式是「平台ID:GroupMessage:群号」，平台 ID 在插件配置里填。
      </p>
      <GroupsToolbar add={add} />
      <Table
        rowKey="group_id"
        size="small"
        columns={buildColumns(editRow, save, remove)}
        dataSource={rows}
        pagination={false}
      />
    </Card>
  );
}
