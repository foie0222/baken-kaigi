export function SettingsPage() {
  return (
    <div className="fade-in">
      <div
        style={{
          background: 'white',
          borderRadius: 12,
          marginBottom: 16,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            fontSize: 13,
            color: '#666',
            padding: '12px 16px',
            background: '#f8f8f8',
            fontWeight: 600,
          }}
        >
          サポート
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 16,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <span style={{ fontSize: 15 }}>ヘルプ</span>
          <span style={{ color: '#ccc' }}>›</span>
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 16,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <span style={{ fontSize: 15 }}>利用規約</span>
          <span style={{ color: '#ccc' }}>›</span>
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 16,
          }}
        >
          <span style={{ fontSize: 15 }}>プライバシーポリシー</span>
          <span style={{ color: '#ccc' }}>›</span>
        </div>
      </div>

      <a
        href="https://www.ncgmkohnodai.go.jp/subject/094/gambling.html"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'block',
          textAlign: 'center',
          padding: 20,
          color: '#c62828',
          fontSize: 14,
          textDecoration: 'none',
        }}
      >
        ギャンブル依存症相談窓口
      </a>

      <p style={{ textAlign: 'center', color: '#999', fontSize: 12, marginTop: 20 }}>
        馬券会議 v1.0.0
        <br />
        ※ 認証機能は今後のアップデートで追加予定です
      </p>
    </div>
  );
}
