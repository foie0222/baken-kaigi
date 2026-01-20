export function HistoryPage() {
  // Unit 1では認証なしなので、ログインプロンプトを表示
  return (
    <div className="fade-in login-prompt">
      <div className="login-prompt-icon">📋</div>
      <h2>賭け履歴</h2>
      <p>
        ログインすると、過去の賭け履歴を
        <br />
        確認できます。
      </p>
      <p style={{ color: '#999', fontSize: 12 }}>
        ※ 認証機能は今後のアップデートで追加予定です
      </p>
    </div>
  );
}
