export function DashboardPage() {
  // Unit 1では認証なしなので、ログインプロンプトを表示
  return (
    <div className="fade-in login-prompt">
      <div className="login-prompt-icon">📊</div>
      <h2>損益ダッシュボード</h2>
      <p>
        ログインすると、損益の管理や
        <br />
        負け額限度額の設定ができます。
      </p>
      <p style={{ color: '#999', fontSize: 12 }}>
        ※ 認証機能は今後のアップデートで追加予定です
      </p>
    </div>
  );
}
