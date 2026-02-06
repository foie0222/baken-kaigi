import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function SettingsPage() {
  const navigate = useNavigate();
  const { isAuthenticated, signOut } = useAuthStore();

  return (
    <div className="fade-in">
      {/* アカウントセクション（認証済みの場合のみ） */}
      {isAuthenticated && (
        <div style={{ background: 'white', borderRadius: 12, marginBottom: 16, overflow: 'hidden' }}>
          <div style={{ fontSize: 13, color: '#666', padding: '12px 16px', background: '#f8f8f8', fontWeight: 600 }}>
            アカウント
          </div>
          <div onClick={() => navigate('/profile')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}>
            <span style={{ fontSize: 15 }}>プロフィール</span>
            <span style={{ color: '#ccc' }}>›</span>
          </div>
          <div onClick={() => navigate('/change-password')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}>
            <span style={{ fontSize: 15 }}>パスワード変更</span>
            <span style={{ color: '#ccc' }}>›</span>
          </div>
          <div onClick={() => signOut()} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}>
            <span style={{ fontSize: 15, color: '#c62828' }}>ログアウト</span>
          </div>
          <div onClick={() => navigate('/delete-account')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, cursor: 'pointer' }}>
            <span style={{ fontSize: 15, color: '#999' }}>アカウント削除</span>
            <span style={{ color: '#ccc' }}>›</span>
          </div>
        </div>
      )}

      {/* 未ログイン時のログインボタン */}
      {!isAuthenticated && (
        <div style={{ background: 'white', borderRadius: 12, marginBottom: 16, overflow: 'hidden' }}>
          <div onClick={() => navigate('/login')} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 16, cursor: 'pointer' }}>
            <span style={{ fontSize: 15, color: '#1a73e8', fontWeight: 600 }}>ログイン / 新規登録</span>
          </div>
        </div>
      )}

      {/* サポートセクション */}
      <div style={{ background: 'white', borderRadius: 12, marginBottom: 16, overflow: 'hidden' }}>
        <div style={{ fontSize: 13, color: '#666', padding: '12px 16px', background: '#f8f8f8', fontWeight: 600 }}>
          サポート
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottom: '1px solid #f0f0f0' }}>
          <span style={{ fontSize: 15 }}>ヘルプ</span>
          <span style={{ color: '#ccc' }}>›</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottom: '1px solid #f0f0f0' }}>
          <span style={{ fontSize: 15 }}>利用規約</span>
          <span style={{ color: '#ccc' }}>›</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16 }}>
          <span style={{ fontSize: 15 }}>プライバシーポリシー</span>
          <span style={{ color: '#ccc' }}>›</span>
        </div>
      </div>

      <a href="https://www.ncgmkohnodai.go.jp/subject/094/gambling.html" target="_blank" rel="noopener noreferrer"
        style={{ display: 'block', textAlign: 'center', padding: 20, color: '#c62828', fontSize: 14, textDecoration: 'none' }}>
        ギャンブル依存症相談窓口
      </a>

      <p style={{ textAlign: 'center', color: '#999', fontSize: 12, marginTop: 20 }}>
        馬券会議 v1.0.0
      </p>
    </div>
  );
}
