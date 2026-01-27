import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E テスト設定
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: "./e2e",
  /* 各テストの最大実行時間 */
  timeout: 30 * 1000,
  /* テスト実行オプション */
  expect: {
    timeout: 5000,
  },
  /* テスト並列実行 */
  fullyParallel: true,
  /* CI環境でのリトライ回数 */
  retries: process.env.CI ? 2 : 0,
  /* CI環境でのワーカー数制限 */
  workers: process.env.CI ? 1 : undefined,
  /* レポーター設定 */
  reporter: "html",
  /* グローバル設定 */
  use: {
    /* ベースURL */
    baseURL: process.env.BASE_URL || "http://localhost:5173",
    /* 各アクションのトレース収集 */
    trace: "on-first-retry",
    /* スクリーンショット */
    screenshot: "only-on-failure",
  },

  /* ブラウザ設定 */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    /* モバイルビューポートテスト */
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],

  /* ローカル開発サーバー */
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
  },
});
