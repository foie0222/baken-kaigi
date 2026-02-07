import { useNavigate } from 'react-router-dom';
import { COOKIE_POLICY_VERSION } from '../../constants/legal';

export function CookiePolicyPage() {
  const navigate = useNavigate();

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="back-btn"
      >
        &larr; 戻る
      </button>

      <div style={{ background: 'white', borderRadius: 12, padding: 24, marginBottom: 16 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Cookieポリシー</h2>
        <p style={{ fontSize: 12, color: '#999', marginBottom: 24 }}>
          バージョン {COOKIE_POLICY_VERSION.version}（{COOKIE_POLICY_VERSION.effectiveDate} 施行）
        </p>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>Cookieとは</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            Cookieとは、ウェブサイトを閲覧した際にブラウザに保存される小さなテキストファイルです。
            本サービスでは、ユーザー体験の向上やサービスの改善のためにCookieを使用しています。
          </p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>使用するCookieの種類</h3>

          <div style={{ marginBottom: 16 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>必須Cookie</h4>
            <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
              サービスの基本的な機能に必要なCookieです。ログイン状態の維持やセキュリティの確保に使用されます。
              これらのCookieは無効にすることができません。
            </p>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>分析Cookie</h4>
            <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
              サービスの利用状況を分析するためのCookieです。ページの閲覧数や利用パターンの把握に使用されます。
            </p>
          </div>

          <div>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>マーケティングCookie</h4>
            <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
              ユーザーの興味に基づいた情報を提供するためのCookieです。
            </p>
          </div>

          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>Cookieの管理方法</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            ブラウザの設定からCookieを管理・削除することができます。
            また、本サービスの設定ページからCookieの同意設定を変更することもできます。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>
      </div>
    </div>
  );
}
