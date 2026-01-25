/**
 * リスク/リターン散布図コンポーネント
 *
 * 買い目ごとのリスクとリターンを散布図で表示する
 */

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';

export interface RiskReturnDataPoint {
  /** 買い目ID */
  id: string;
  /** 買い目名（表示用） */
  name: string;
  /** リスク（0-100） */
  risk: number;
  /** リターン期待値（倍率） */
  expectedReturn: number;
  /** 金額 */
  amount: number;
}

interface RiskReturnChartProps {
  /** データポイント */
  data: RiskReturnDataPoint[];
}

/**
 * リスクに基づいて色を返す
 */
function getPointColor(risk: number): string {
  if (risk >= 70) return '#c62828'; // 赤（高リスク）
  if (risk >= 40) return '#f9a825'; // 黄色（中リスク）
  return '#2e7d32'; // 緑（低リスク）
}

/**
 * カスタムツールチップ
 */
function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: RiskReturnDataPoint }> }) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload;
  return (
    <div
      style={{
        backgroundColor: 'white',
        padding: '12px 16px',
        border: '1px solid #e0e0e0',
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      <p style={{ margin: 0, fontWeight: 600, marginBottom: 8 }}>{data.name}</p>
      <p style={{ margin: 0, fontSize: 13, color: '#666' }}>
        リスク: <span style={{ color: getPointColor(data.risk), fontWeight: 600 }}>{data.risk}%</span>
      </p>
      <p style={{ margin: 0, fontSize: 13, color: '#666' }}>
        期待リターン: <span style={{ fontWeight: 600 }}>{data.expectedReturn.toFixed(1)}倍</span>
      </p>
      <p style={{ margin: 0, fontSize: 13, color: '#666' }}>
        金額: <span style={{ fontWeight: 600 }}>¥{data.amount.toLocaleString()}</span>
      </p>
    </div>
  );
}

export function RiskReturnChart({ data }: RiskReturnChartProps) {
  if (data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
        表示するデータがありません
      </div>
    );
  }

  return (
    <div className="risk-return-chart" style={{ marginBottom: 16 }}>
      <div style={{ marginBottom: 12 }}>
        <span style={{ fontSize: 14, color: '#666', fontWeight: 500 }}>
          リスク/リターン分析
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            type="number"
            dataKey="risk"
            name="リスク"
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 11 }}
            label={{ value: 'リスク', position: 'bottom', offset: 0, fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="expectedReturn"
            name="期待リターン"
            domain={[0, 'auto']}
            tickFormatter={(v) => `${v}x`}
            tick={{ fontSize: 11 }}
            label={{ value: 'リターン', angle: -90, position: 'insideLeft', fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* リスク50%の参照線 */}
          <ReferenceLine x={50} stroke="#999" strokeDasharray="5 5" />
          {/* リターン1倍の参照線（損益分岐） */}
          <ReferenceLine y={1} stroke="#999" strokeDasharray="5 5" />
          <Scatter name="買い目" data={data}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getPointColor(entry.risk)} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#2e7d32' }} />
          <span>低リスク</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#f9a825' }} />
          <span>中リスク</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#c62828' }} />
          <span>高リスク</span>
        </div>
      </div>
    </div>
  );
}
