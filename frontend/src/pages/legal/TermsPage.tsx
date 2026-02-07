import { useNavigate } from 'react-router-dom';
import { TERMS_VERSION } from '../../constants/legal';

export function TermsPage() {
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
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>利用規約</h2>
        <p style={{ fontSize: 12, color: '#999', marginBottom: 24 }}>
          バージョン {TERMS_VERSION.version}（{TERMS_VERSION.effectiveDate} 施行）
        </p>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第1条（総則）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本利用規約（以下「本規約」といいます）は、馬券会議（以下「本サービス」といいます）の利用条件を定めるものです。
            ユーザーの皆様には、本規約に同意いただいた上で本サービスをご利用いただきます。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第2条（定義）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本規約において使用する用語の定義は以下の通りとします。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第3条（利用登録）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本サービスの利用を希望する方は、本規約に同意の上、所定の方法により利用登録を行うものとします。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第4条（禁止事項）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            ユーザーは、本サービスの利用にあたり、以下の行為を行ってはなりません。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第5条（免責事項）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本サービスは馬券購入の判断を支援するものであり、的中や利益を保証するものではありません。
            馬券の購入はユーザーご自身の判断と責任において行ってください。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第6条（規約の変更）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            当社は、必要と判断した場合には、ユーザーに通知することなく本規約を変更することができるものとします。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>

        <section>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' }}>第7条（準拠法・裁判管轄）</h3>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
            本規約の解釈にあたっては、日本法を準拠法とします。
          </p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 8 }}>※ 法務確認後に正式な内容を掲載予定</p>
        </section>
      </div>
    </div>
  );
}
