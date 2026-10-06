// 页面层：页内 Tab 清单。宿主只链到一个页面，两块业务在页内切。

export interface PageTab {
  key: string;
  label: string;
}

export const PAGE_TABS: PageTab[] = [
  { key: "groups", label: "监控群" },
  { key: "status", label: "轮询状态" },
];
