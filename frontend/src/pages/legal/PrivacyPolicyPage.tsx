import { Link, useNavigate } from 'react-router-dom';
import { PRIVACY_VERSION } from '../../constants/legal';

const sectionStyle = { marginBottom: 24 };
const h3Style = { fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' } as const;
const pStyle = { fontSize: 14, lineHeight: 1.8, color: '#333' } as const;
const listStyle = { fontSize: 14, lineHeight: 1.8, color: '#333', paddingLeft: 20, margin: '8px 0' } as const;

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

        <section style={sectionStyle}>
          <h3 style={h3Style}>1. 個人情報の収集</h3>
          <p style={pStyle}>
            本サービスでは、サービスの提供にあたり、以下の個人情報を収集する場合があります。
          </p>
          <ul style={listStyle}>
            <li>メールアドレス（Googleアカウント認証を通じて取得）</li>
            <li>氏名（Googleアカウント認証を通じて取得）</li>
            <li>生年月日（年齢確認のため、利用登録時にご入力いただきます）</li>
            <li>利用履歴（本サービスの閲覧・操作履歴）</li>
            <li>端末情報（ブラウザの種類、OS、画面解像度等）</li>
            <li>Cookie情報</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>2. 利用目的</h3>
          <p style={pStyle}>収集した個人情報は、以下の目的で利用いたします。</p>
          <ul style={listStyle}>
            <li>本サービスの提供・運営・維持</li>
            <li>ユーザー認証およびアカウント管理</li>
            <li>年齢確認（20歳以上であることの確認）</li>
            <li>サービスの改善・新機能の開発</li>
            <li>利用状況の分析・統計処理</li>
            <li>お問い合わせへの対応</li>
            <li>規約変更等の重要なお知らせの通知</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>3. 第三者提供</h3>
          <p style={pStyle}>
            当社は、以下の場合を除き、ユーザーの同意なく個人情報を第三者に提供することはありません。
          </p>
          <ul style={listStyle}>
            <li>法令に基づく場合</li>
            <li>人の生命、身体または財産の保護のために必要がある場合</li>
            <li>公衆衛生の向上または児童の健全な育成の推進のために特に必要がある場合</li>
            <li>国の機関もしくは地方公共団体またはその委託を受けた者が法令の定める事務を遂行することに対して協力する必要がある場合</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>4. 外部サービスの利用</h3>
          <p style={pStyle}>
            本サービスでは、以下の外部サービスを利用しています。
            各サービスのプライバシーポリシーについては、それぞれのサービス提供元をご確認ください。
          </p>
          <ul style={listStyle}>
            <li>Google認証（ユーザー認証のため）</li>
            <li>Amazon Web Services（サービス基盤として利用）</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>5. Cookieの利用</h3>
          <p style={pStyle}>
            本サービスでは、サービス向上のためにCookieを使用しています。
            詳細については
            <Link to="/cookie-policy" style={{ color: '#1a73e8' }}>Cookieポリシー</Link>
            をご覧ください。
          </p>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>6. 保管と安全管理</h3>
          <p style={pStyle}>
            当社は、個人情報の漏洩、滅失又は毀損の防止その他の安全管理のために、以下の措置を講じます。
          </p>
          <ul style={listStyle}>
            <li>通信の暗号化（SSL/TLS）</li>
            <li>アクセス制御による不正アクセスの防止</li>
            <li>個人情報を取り扱う従業者への教育・監督</li>
            <li>定期的なセキュリティ対策の見直し</li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>7. 開示・訂正・削除</h3>
          <ol style={listStyle}>
            <li>ユーザーは、当社が保有する自己の個人情報について、開示・訂正・削除を求めることができます。</li>
            <li>アカウントを削除した場合、当社はユーザーの個人情報を速やかに削除します。ただし、法令に基づき保管が必要な情報を除きます。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>8. プライバシーポリシーの変更</h3>
          <p style={pStyle}>
            当社は、必要に応じて本プライバシーポリシーを変更することがあります。
            変更した場合は、本サービス上で通知いたします。
          </p>
        </section>

        <section>
          <h3 style={h3Style}>9. お問い合わせ</h3>
          <p style={pStyle}>
            個人情報の取扱いに関するお問い合わせは、本サービス内のお問い合わせ窓口までご連絡ください。
          </p>
        </section>
      </div>
    </div>
  );
}
