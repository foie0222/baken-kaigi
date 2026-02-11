import { useNavigate } from 'react-router-dom';
import { TERMS_VERSION } from '../../constants/legal';
import { sectionStyle, h3Style, pStyle, listStyle } from './legalStyles';

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

        <section style={sectionStyle}>
          <h3 style={h3Style}>第1条（総則）</h3>
          <p style={pStyle}>
            本利用規約（以下「本規約」といいます）は、馬券会議（以下「本サービス」といいます）の利用条件を定めるものです。
            ユーザーの皆様には、本規約に同意いただいた上で本サービスをご利用いただきます。
          </p>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第2条（定義）</h3>
          <p style={pStyle}>本規約において使用する用語の定義は以下の通りとします。</p>
          <ol style={listStyle}>
            <li>「本サービス」とは、AI技術を活用した競馬予想の分析・検討を支援するウェブサービスをいいます。</li>
            <li>「ユーザー」とは、本サービスに利用登録を行い、本サービスを利用する個人をいいます。</li>
            <li>「AI予想」とは、本サービスが提供するAIによる競馬レースの分析情報をいいます。</li>
            <li>「コンテンツ」とは、本サービス上で提供される一切の情報（AI予想、分析データ、テキスト、画像等）をいいます。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第3条（利用登録）</h3>
          <ol style={listStyle}>
            <li>本サービスの利用を希望する方は、本規約に同意の上、所定の方法により利用登録を行うものとします。</li>
            <li>利用登録には、Googleアカウントまたは Appleアカウントによる認証が必要です。</li>
            <li>本サービスは20歳以上の方のみ利用登録が可能です。</li>
            <li>当社は、利用登録を申請した方が以下のいずれかに該当する場合、利用登録を拒否することがあります。
              <ul style={{ paddingLeft: 20, marginTop: 4 }}>
                <li>虚偽の情報を申告した場合</li>
                <li>本規約に違反したことがある者からの申請である場合</li>
                <li>その他、当社が利用登録を適当でないと判断した場合</li>
              </ul>
            </li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第4条（アカウント管理）</h3>
          <ol style={listStyle}>
            <li>ユーザーは、自己の責任においてアカウントを適切に管理するものとします。</li>
            <li>ユーザーは、アカウントを第三者に利用させ、または譲渡、貸与、売買等をしてはなりません。</li>
            <li>アカウントの不正利用による損害について、当社は一切の責任を負いません。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第5条（サービス内容）</h3>
          <ol style={listStyle}>
            <li>本サービスは、AIを活用した競馬レースの分析情報を提供し、ユーザーの馬券購入の検討を支援するものです。</li>
            <li>本サービスが提供する情報は、参考情報として提供するものであり、馬券の的中や利益を保証するものではありません。</li>
            <li>当社は、本サービスの内容を予告なく変更・追加・中断・終了することがあります。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第6条（禁止事項）</h3>
          <p style={pStyle}>ユーザーは、本サービスの利用にあたり、以下の行為を行ってはなりません。</p>
          <ol style={listStyle}>
            <li>法令または公序良俗に違反する行為</li>
            <li>犯罪行為に関連する行為</li>
            <li>本サービスのサーバーまたはネットワークに過度な負荷をかける行為</li>
            <li>本サービスの運営を妨害する行為</li>
            <li>本サービスのコンテンツを無断で複製、転載、配布、販売する行為</li>
            <li>他のユーザーまたは第三者の権利を侵害する行為</li>
            <li>不正アクセスまたはこれを試みる行為</li>
            <li>本サービスの情報を利用した第三者への投資助言行為</li>
            <li>反社会的勢力への利益供与</li>
            <li>その他、当社が不適当と判断する行為</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第7条（知的財産権）</h3>
          <ol style={listStyle}>
            <li>本サービスに関する知的財産権は、当社または正当な権利者に帰属します。</li>
            <li>ユーザーは、本サービスのコンテンツを本サービスの利用目的の範囲内でのみ使用できるものとします。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第8条（免責事項）</h3>
          <ol style={listStyle}>
            <li>本サービスは馬券購入の判断を支援するものであり、的中や利益を保証するものではありません。馬券の購入はユーザーご自身の判断と責任において行ってください。</li>
            <li>当社は、本サービスが提供するAI予想・分析情報の正確性、完全性、有用性等について、いかなる保証も行いません。</li>
            <li>ユーザーが本サービスの情報に基づいて馬券を購入し、損失が発生した場合であっても、当社は一切の責任を負いません。</li>
            <li>当社は、本サービスの利用に起因してユーザーに発生した損害について、当社の故意または重大な過失による場合を除き、一切の責任を負いません。</li>
            <li>本サービスの利用に関連して、ユーザーと第三者との間でトラブルが発生した場合、ユーザーの費用と責任において解決するものとします。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第9条（ギャンブル依存症に関する注意事項）</h3>
          <p style={pStyle}>
            競馬を含む公営競技は、適切に楽しむことが大切です。以下の点にご注意ください。
          </p>
          <ul style={listStyle}>
            <li>馬券の購入は、生活に支障のない余裕資金の範囲内で行ってください。</li>
            <li>負けを取り返そうとして、予算以上の金額を賭けることはお控えください。</li>
            <li>本サービスの負け額制限機能を活用し、計画的な利用を心がけてください。</li>
          </ul>
          <p style={pStyle}>
            ギャンブル依存症が疑われる場合は、以下の相談窓口にご相談ください。
          </p>
          <ul style={{ ...listStyle, listStyleType: 'none', paddingLeft: 0 }}>
            <li style={{ marginBottom: 8 }}>
              <strong>リカバリーサポート・ネットワーク</strong><br />
              電話: 0120-683-705（24時間対応）
            </li>
            <li style={{ marginBottom: 8 }}>
              <strong>依存症対策全国センター</strong><br />
              各都道府県・政令指定都市の精神保健福祉センター
            </li>
            <li style={{ marginBottom: 8 }}>
              <strong>消費者ホットライン</strong><br />
              電話: 188
            </li>
          </ul>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第10条（利用制限・登録抹消）</h3>
          <ol style={listStyle}>
            <li>当社は、ユーザーが本規約に違反した場合、事前の通知なく、本サービスの利用を制限し、またはユーザーの登録を抹消することができるものとします。</li>
            <li>ユーザーは、所定の手続きにより、いつでもアカウントを削除し、退会することができます。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第11条（規約の変更）</h3>
          <ol style={listStyle}>
            <li>当社は、必要と判断した場合には、ユーザーに事前に通知した上で本規約を変更することができるものとします。</li>
            <li>変更後の規約は、本サービス上に掲示した時点から効力を生じるものとします。</li>
            <li>変更後に本サービスを利用した場合、変更後の規約に同意したものとみなします。</li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h3 style={h3Style}>第12条（個人情報の取扱い）</h3>
          <p style={pStyle}>
            本サービスにおける個人情報の取扱いについては、別途定めるプライバシーポリシーによるものとします。
          </p>
        </section>

        <section>
          <h3 style={h3Style}>第13条（準拠法・裁判管轄）</h3>
          <ol style={listStyle}>
            <li>本規約の解釈にあたっては、日本法を準拠法とします。</li>
            <li>本サービスに関して紛争が生じた場合、東京地方裁判所を第一審の専属的合意管轄裁判所とします。</li>
          </ol>
        </section>
      </div>
    </div>
  );
}
