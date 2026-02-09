import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useCookieConsentStore } from '../stores/cookieConsentStore';

function SettingsMenuItem({ label, onClick, color }: { label: string; onClick: () => void; color?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottom: '1px solid #f0f0f0',
        cursor: 'pointer',
        width: '100%',
        background: 'none',
        border: 'none',
        borderBottomStyle: 'solid',
        borderBottomWidth: 1,
        borderBottomColor: '#f0f0f0',
        textAlign: 'left',
      }}
    >
      <span style={{ fontSize: 15, color: color || 'inherit' }}>{label}</span>
      {!color?.includes('c62828') && <span style={{ color: '#ccc' }}>&rsaquo;</span>}
    </button>
  );
}

export function SettingsPage() {
  const navigate = useNavigate();
  const { isAuthenticated, signOut } = useAuthStore();
  const resetConsent = useCookieConsentStore((state) => state.resetConsent);

  return (
    <div className="fade-in">
      {/* アカウントセクション（認証済みの場合のみ） */}
      {isAuthenticated && (
        <div style={{ background: 'white', borderRadius: 12, marginBottom: 16, overflow: 'hidden' }}>
          <div style={{ fontSize: 13, color: '#666', padding: '12px 16px', background: '#f8f8f8', fontWeight: 600 }}>
            アカウント
          </div>
          <SettingsMenuItem label="プロフィール" onClick={() => navigate('/profile')} />
          <SettingsMenuItem label="パスワード変更" onClick={() => navigate('/change-password')} />
          <SettingsMenuItem label="IPAT設定" onClick={() => navigate('/settings/ipat')} />
          <SettingsMenuItem label="ログアウト" onClick={() => signOut()} color="#c62828" />
          <SettingsMenuItem label="アカウント削除" onClick={() => navigate('/delete-account')} color="#999" />
        </div>
      )}

      {/* 未ログイン時のログインボタン */}
      {!isAuthenticated && (
        <div style={{ background: 'white', borderRadius: 12, marginBottom: 16, overflow: 'hidden' }}>
          <button
            type="button"
            onClick={() => navigate('/login')}
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              padding: 16,
              cursor: 'pointer',
              width: '100%',
              background: 'none',
              border: 'none',
            }}
          >
            <span style={{ fontSize: 15, color: '#1a73e8', fontWeight: 600 }}>ログイン / 新規登録</span>
          </button>
        </div>
      )}

      {/* サポートセクション */}
      <div style={{ background: 'white', borderRadius: 12, marginBottom: 16, overflow: 'hidden' }}>
        <div style={{ fontSize: 13, color: '#666', padding: '12px 16px', background: '#f8f8f8', fontWeight: 600 }}>
          サポート
        </div>
        <SettingsMenuItem label="ヘルプ" onClick={() => navigate('/help')} />
        <SettingsMenuItem label="利用規約" onClick={() => navigate('/terms')} />
        <SettingsMenuItem label="プライバシーポリシー" onClick={() => navigate('/privacy')} />
        <SettingsMenuItem label="Cookie設定" onClick={() => resetConsent()} />
      </div>

      <a href="https://www.gaprsc.or.jp/index.html" target="_blank" rel="noopener noreferrer"
        style={{ display: 'block', textAlign: 'center', padding: 20, color: '#c62828', fontSize: 14, textDecoration: 'none' }}>
        ギャンブル依存症相談窓口
      </a>

      <p style={{ textAlign: 'center', color: '#999', fontSize: 12, marginTop: 20 }}>
        馬券会議 v1.0.0
      </p>
    </div>
  );
}
