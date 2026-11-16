// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

import vue from "@vitejs/plugin-vue";
import path, { resolve } from "path";
import AutoImport from "unplugin-auto-import/vite";
import { AntDesignVueResolver } from "unplugin-vue-components/resolvers";
import Components from "unplugin-vue-components/vite";
import { defineConfig, loadEnv } from "vite";
import viteCompression from "vite-plugin-compression";

const pathResolve = (dir: string) => {
  return resolve(__dirname, ".", dir);
};

const alias: Record<string, string> = {
  "@": pathResolve("./src/"),
  "vue-i18n": "vue-i18n/dist/vue-i18n.cjs.js",
};

const viteConfig = defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const serverHost =
    process.env.SERVER_HOST || env.SERVER_HOST || "10.239.58.135";
  const metricsApiTarget = `http://${serverHost}:8000`;
  const libraryApiTarget = `http://${serverHost}:16022`;
  const appApiTarget = `http://${serverHost}:16020`;
  const fileApiTarget = `http://${serverHost}:3001`;
  const wsTarget = "ws://127.0.0.1:18789";

  return {
    plugins: [
      vue(),
      viteCompression(),
      AutoImport({
        imports: ["vue", "vue-router", "pinia"],
        dts: "src/auto-imports.d.ts",
        resolvers: [AntDesignVueResolver()],
      }),
      Components({
        resolvers: [
          AntDesignVueResolver({
            importStyle: false, // css in js
          }),
        ],
      }),
    ],
    root: process.cwd(),
    resolve: { alias },
    server: {
      host: "0.0.0.0",
      port: 7000,
      strictPort: true,
      hmr: true,
      allowedHosts: ["edgeainode1.sh.intel.com"],
      proxy: {
        "/library-api/": {
          target: libraryApiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/library-api\//, "/"),
        },
        "/app-api/": {
          target: appApiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/app-api\//, "/"),
        },
        "/metrics-api/": {
          target: metricsApiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/metrics-api\//, "/"),
        },
        "/workspace-api/": {
          target: fileApiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/workspace-api\//, "/"),
        },
        "/ws": {
          target: wsTarget,
          changeOrigin: true,
          ws: true,
          rewrite: (path) => path.replace(/^\/ws(?=\/|$)/, "") || "/",
        },
      },
    },
    build: {
      outDir: "dist",
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          chunkFileNames: "assets/js/[name]-[hash].js",
          entryFileNames: "assets/js/[name]-[hash].js",
          assetFileNames: "assets/[ext]/[name]-[hash].[ext]",
        },
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          additionalData: `@import "${path.resolve(__dirname, "src/theme/index.less")}";`,
        },
      },
    },
  };
});

export default viteConfig;
