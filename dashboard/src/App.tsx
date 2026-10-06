// 页面层：页面外壳。两块业务放页内 Tab，切换只改 state，不动顶层 hash。

import { useEffect, useMemo, useState } from "react";
import { App as AntdApp, ConfigProvider, Tabs, theme } from "antd";
import { PAGE_TABS } from "./nav";
import { readIsDark } from "./theme";
import { GroupsView } from "./views/GroupsView";
import { StatusView } from "./views/StatusView";

export function App() {
  const [active, setActive] = useState("groups");
  const isDark = useMemo(() => readIsDark(), []);
  const algorithm = isDark ? theme.darkAlgorithm : theme.defaultAlgorithm;

  // 页面底色跟着宿主明暗走：CSS 里的 body.is-dark 用它。首屏由 index.html 的内联脚本先铺。
  useEffect(() => {
    document.body.classList.toggle("is-dark", isDark);
  }, [isDark]);

  const items = PAGE_TABS.map((tab) => {
    // 只有两块，直接按 key 给组件；切走的面板销毁，避免带着旧值回显
    let children = null;
    if (tab.key === "groups") {
      children = <GroupsView />;
    } else if (tab.key === "status") {
      children = <StatusView />;
    }
    return { key: tab.key, label: tab.label, children };
  });

  return (
    <ConfigProvider theme={{ algorithm }}>
      {/* component={false} 是为了不加多余的 div 包裹；message 走 useApp 才能跟随主题 */}
      <AntdApp component={false}>
        <main className="page">
          <Tabs
            type="card"
            size="small"
            activeKey={active}
            onChange={setActive}
            destroyOnHidden
            items={items}
          />
        </main>
      </AntdApp>
    </ConfigProvider>
  );
}
