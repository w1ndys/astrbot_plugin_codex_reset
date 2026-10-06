// 页面层：挂载点。宿主只给一个 iframe，容器由自己创建。

import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./style.css";

const container = document.getElementById("root");
// 容器不存在就没法挂载，直接不渲染
if (container) {
  createRoot(container).render(<App />);
}
