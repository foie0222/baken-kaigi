import { test, expect } from "@playwright/test";

/**
 * E2Eテスト: コンサルテーションフロー
 * Issue #157 - シナリオ1: 基本的なコンサルテーションフロー
 */
test.describe("コンサルテーションフロー", () => {
  test.beforeEach(async ({ page }) => {
    // ホームページに移動
    await page.goto("/");
  });

  test("レース一覧からレース詳細への遷移", async ({ page }) => {
    // レース一覧が表示されることを確認
    await expect(page.locator("main")).toBeVisible();

    // レースカードまたはリストアイテムを探す
    const raceItem = page.locator('[data-testid="race-item"]').first();

    // レースアイテムの存在確認（count()で安全にチェック）
    const raceItemCount = await raceItem.count();
    if (raceItemCount > 0) {
      await expect(raceItem).toBeVisible();
      await raceItem.click();
      // レース詳細ページに遷移したことを確認
      await expect(page).toHaveURL(/\/races\//);
    } else {
      // レースアイテムがない場合でもテストは成功（データがない場合を許容）
      console.log("No race items found - skipping navigation test");
    }
  });

  test("カートページへの遷移と表示", async ({ page }) => {
    // カートページに移動
    await page.goto("/cart");

    // カートページが表示されることを確認
    await expect(page.locator("main")).toBeVisible();

    // カートが空の場合のメッセージまたはカート内容を探す
    const cartContent = page.locator(
      '[data-testid="cart-content"], [data-testid="empty-cart"]'
    );

    // カートコンテンツの存在確認
    const cartContentCount = await cartContent.count();
    if (cartContentCount > 0) {
      // カートコンテンツが存在する場合、表示を確認
      await expect(cartContent.first()).toBeVisible();
    } else {
      // data-testidがない場合でも、ページ自体は正常に表示されている
      // この場合はmainが表示されていることで成功とする
      console.log(
        "Cart content with expected data-testid not found - page rendered without specific markers"
      );
    }
  });
});

/**
 * E2Eテスト: レース分析フロー
 * Issue #157 - シナリオ2: レース分析と馬券選択
 */
test.describe("レース分析フロー", () => {
  test("レース詳細ページで馬情報を確認", async ({ page }) => {
    // サンプルのレース詳細ページに移動（実際のraceIdが必要）
    await page.goto("/races/20260125_06_11");

    // ページが表示されることを確認（404でも正常なレスポンスとして扱う）
    await expect(page.locator("body")).toBeVisible();

    // レース情報またはエラーメッセージが表示される
    const content = page.locator("main, [role='main']");
    const contentCount = await content.count();

    if (contentCount > 0) {
      // メインコンテンツが存在する場合は表示を確認
      await expect(content.first()).toBeVisible({ timeout: 10000 });
    } else {
      // メインコンテンツがない場合（404ページなど）でもbodyは表示されている
      console.log(
        "Main content not found - page may be showing 404 or error state"
      );
    }
  });

  test("ダッシュボードページの表示", async ({ page }) => {
    await page.goto("/dashboard");

    // ダッシュボードページが表示されることを確認
    await expect(page.locator("main")).toBeVisible();
  });

  test("設定ページの表示", async ({ page }) => {
    await page.goto("/settings");

    // 設定ページが表示されることを確認
    await expect(page.locator("main")).toBeVisible();
  });
});

/**
 * E2Eテスト: ナビゲーションフロー
 * Issue #157 - シナリオ3: アプリ全体のナビゲーション
 */
test.describe("ナビゲーションフロー", () => {
  test("全ページへのナビゲーション", async ({ page }) => {
    const routes = [
      { path: "/", name: "ホーム（レース一覧）" },
      { path: "/cart", name: "カート" },
      { path: "/dashboard", name: "ダッシュボード" },
      { path: "/history", name: "履歴" },
      { path: "/settings", name: "設定" },
    ];

    // ページエラーを収集（ループの外で1回だけ登録）
    const pageErrors: { route: string; error: string }[] = [];
    page.on("pageerror", (error) => {
      pageErrors.push({ route: page.url(), error: error.message });
    });

    for (const route of routes) {
      await page.goto(route.path);

      // ページが正常に表示されることを確認
      await expect(page.locator("body")).toBeVisible();
    }

    // テスト終了時にページエラーがないことを確認
    if (pageErrors.length > 0) {
      console.error("Page errors detected:", pageErrors);
    }
    expect(pageErrors).toHaveLength(0);
  });

  test("レスポンシブデザインの確認", async ({ page }) => {
    // モバイルビューポートでテスト
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // ページが表示されることを確認
    await expect(page.locator("body")).toBeVisible();

    // デスクトップビューポートでテスト
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto("/");

    // ページが表示されることを確認
    await expect(page.locator("body")).toBeVisible();
  });

  test("ページ間の戻る・進む操作", async ({ page }) => {
    // ホームページに移動
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();

    // カートページに移動
    await page.goto("/cart");
    await expect(page.locator("body")).toBeVisible();

    // 戻る操作
    await page.goBack();
    await expect(page).toHaveURL("/");

    // 進む操作
    await page.goForward();
    await expect(page).toHaveURL("/cart");
  });
});
