import { useNavigate } from 'react-router-dom';

const sectionStyle = { marginBottom: 24 };
const h3Style = { fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#1a5f2a' } as const;
const pStyle = { fontSize: 14, lineHeight: 1.8, color: '#333' } as const;

export function HelpPage() {
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
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>ヘルプ</h2>

        <section style={sectionStyle}>
          <h3 style={h3Style}>馬券会議とは</h3>
          <p style={pStyle}>
            馬券会議は、AIを活用して競馬の買い目を分析・検討できるサービスです。
            複数のAI予想を比較し、期待値やリスクを考慮した上で馬券購入の判断をサポートします。
          </p>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>基本的な使い方</h3>
          <ol style={{ fontSize: 14, lineHeight: 2, color: '#333', paddingLeft: 20 }}>
            <li>レース一覧から気になるレースを選択</li>
            <li>出馬表から馬を選んで券種・金額を設定</li>
            <li>カートに追加して買い目を管理</li>
            <li>「AIと一緒に確認する」でAI分析を確認</li>
            <li>納得したらIPAT連携で購入</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>AI分析提案について</h3>
          <p style={pStyle}>
            レース詳細ページの「AI分析提案」ボタンから、AIが予算に応じた買い目を提案します。
            複数のAI予想の一致度やレース特性を考慮した提案が生成されます。
          </p>
          <p style={{ ...pStyle, marginTop: 8 }}>
            提案はあくまで参考情報です。最終的な購入判断はご自身で行ってください。
          </p>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>IPAT連携について</h3>
          <p style={pStyle}>
            JRAのIPATアカウントを設定すると、アプリから直接馬券を購入できます。
            設定ページの「IPAT設定」から加入者番号・暗証番号・P-ARS番号・INET-IDを登録してください。
          </p>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>負け額限度額について</h3>
          <p style={pStyle}>
            損益ページから月間の負け額限度額を設定できます。
            限度額に達すると馬券の購入ができなくなり、使いすぎを防止します。
          </p>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>お問い合わせ</h3>
          <p style={pStyle}>
            ご不明な点やお困りのことがございましたら、アプリ内の設定ページからお問い合わせください。
          </p>
        </section>
      </div>
    </div>
  );
}
