import { Link, useNavigate } from 'react-router-dom';
import { PRIVACY_VERSION } from '../../constants/legal';

export function PrivacyPolicyPage() {
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
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>プライバシーポリシー</h2>
        <p style={{ fontSize: 12, color: '#999', marginBottom: 24 }}>
          バージョン {PRIVACY_VERSION.version}（{PRIVACY_VERSION.effectiveDate} 施行）
        </p>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>1. 個人情報の収集</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本サービスでは、サービスの提供にあたり、以下の個人情報を収集する場合があります。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>2. 利用目的</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            収集した個人情報は、以下の目的で利用いたします。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>3. 第三者提供</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            当社は、法令に基づく場合を除き、ユーザーの同意なく個人情報を第三者に提供することはありません。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>4. Cookieの利用</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本サービスでは、サービス向上のためにCookieを使用しています。
            詳細については
            <Link to="/cookie-policy" style={{ color: '#1a73e8' }}>Cookieポリシー</Link>
            をご覧ください。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>5. 保管と安全管理</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            当社は、個人情報の漏洩、滅失又は毀損の防止その他の安全管理のために必要な措置を講じます。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>6. 開示・訂正・削除</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            ユーザーは、当社が保有する自己の個人情報について、開示・訂正・削除を求めることができます。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>7. お問い合わせ</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            個人情報の取扱いに関するお問い合わせは、所定の窓口までご連絡ください。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>
      </div>
    </div>
  );
}
