// 页面层：后端返回的数据形状。字段名与 main.py 的 row_payload / status_payload 一致。

export interface GroupRow {
  group_id: string;
  remark: string;
  enabled: boolean;
  has_session: boolean;
  can_push: boolean;
}

export interface GroupListResponse {
  groups: GroupRow[];
}

export interface SavedGroupResponse {
  group: GroupRow;
  notice: string;
}

export interface StatusResponse {
  baselined: boolean;
  last_seen_id: string;
  last_reset_at: string;
  rounded_24h: number | null;
  rounded_48h: number | null;
  last_error: string;
  last_poll_at: string;
  last_message_count: number;
  source_label: string;
  source_url: string;
}
