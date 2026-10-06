import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 打成一份 IIFE。AstrBot 只稳定改写 HTML 的 src/href，运行时不再走 CDN，也不拆多文件。
const classicScriptPlugin = () => ({
  name: "classic-script-plugin",
  transformIndexHtml(html: string) {
    return html
      .replace(/<script\s+type=["']module["']\s+crossorigin\b/gi, "<script defer")
      .replace(/<script\s+type=["']module["']\b/gi, "<script defer")
      .replace(/\s+crossorigin(?:=["'][^"']*["'])?/gi, "");
  },
});

export default defineConfig({
  base: "./",
  plugins: [react(), classicScriptPlugin()],
  build: {
    outDir: "../pages/monitor",
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: 150000,
    chunkSizeWarningLimit: 5000,
    rollupOptions: {
      output: {
        format: "iife",
        name: "CodexResetApp",
        // Vite 8 对 iife 已默认不分包，这里不再写 inlineDynamicImports
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name].[ext]",
      },
    },
  },
});
