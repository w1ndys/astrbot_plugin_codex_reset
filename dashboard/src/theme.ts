// 页面层：读宿主主题。宿主会把主题放进 query；没有就跟随系统。

export function readIsDark(): boolean {
  const params = new URLSearchParams(window.location.search);
  // 明确给了主题就按给的值
  if (params.get("theme") === "dark" || params.get("isDark") === "true") {
    return true;
  }
  if (params.get("theme") === "light" || params.get("isDark") === "false") {
    return false;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
