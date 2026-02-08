import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBettingStore } from '../stores/bettingStore';
import { useLossLimitStore } from '../stores/lossLimitStore';
import type { BettingSummary, BettingRecord } from '../types';
import { BetTypeLabels } from '../types';
import { LossLimitSetupForm } from '../components/loss-limit/LossLimitSetupForm';
import { LossLimitCard } from '../components/loss-limit/LossLimitCard';

function formatCurrency(value: number): string {
  const prefix = value < 0 ? '-' : '';
  return `${prefix}¥${Math.abs(value).toLocaleString()}`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function SummaryCard({
  title,
  summary,
  comparison,
}: {
  title: string;
  summary: BettingSummary | null;
  comparison?: BettingSummary | null;
}) {
  if (!summary) return null;

  const profitDiff = comparison ? summary.netProfit - comparison.netProfit : null;

  return (
    <div style={{
      background: 'white',
      borderRadius: 12,
      padding: 16,
    }}>
      <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>{title}</div>
      <div style={{
        fontSize: 28,
        fontWeight: 700,
        color: summary.netProfit >= 0 ? '#2e7d32' : '#c62828',
        marginBottom: 12,
      }}>
        {formatCurrency(summary.netProfit)}
        {profitDiff !== null && (
          <span style={{
            fontSize: 13,
            fontWeight: 500,
            marginLeft: 8,
            color: profitDiff >= 0 ? '#2e7d32' : '#c62828',
          }}>
            {profitDiff >= 0 ? '+' : ''}{formatCurrency(profitDiff)}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 12, color: '#999' }}>投資額</div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{formatCurrency(summary.totalInvestment)}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: '#999' }}>払戻額</div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{formatCurrency(summary.totalPayout)}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: '#999' }}>回収率</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: summary.roi >= 100 ? '#2e7d32' : '#c62828' }}>
            {formatPercent(summary.roi)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: '#999' }}>的中率</div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{formatPercent(summary.winRate)}</div>
        </div>
      </div>
    </div>
  );
}

function ProfitChart({ records }: { records: BettingRecord[] }) {
  if (records.length === 0) return null;

  // 日付順にソートして累計損益を計算
  const sorted = [...records]
    .filter((r) => r.status === 'SETTLED')
    .sort((a, b) => a.raceDate.localeCompare(b.raceDate));

  if (sorted.length === 0) return null;

  const points: { date: string; cumProfit: number }[] = [];
  let cumProfit = 0;
  for (const record of sorted) {
    cumProfit += record.profit;
    points.push({ date: record.raceDate, cumProfit });
  }

  const width = 560;
  const height = 200;
  const paddingX = 40;
  const paddingY = 24;
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  const minProfit = Math.min(0, ...points.map((p) => p.cumProfit));
  const maxProfit = Math.max(0, ...points.map((p) => p.cumProfit));
  const range = maxProfit - minProfit || 1;

  const getX = (i: number) => paddingX + (points.length > 1 ? (i / (points.length - 1)) * chartWidth : chartWidth / 2);
  const getY = (val: number) => paddingY + chartHeight - ((val - minProfit) / range) * chartHeight;

  const polylinePoints = points.map((p, i) => `${getX(i)},${getY(p.cumProfit)}`).join(' ');
  const zeroY = getY(0);

  // X軸ラベル用: 最初、中間、最後の日付
  const labelIndices = points.length <= 3
    ? points.map((_, i) => i)
    : [0, Math.floor(points.length / 2), points.length - 1];

  return (
    <div style={{ background: 'white', borderRadius: 12, padding: 16 }}>
      <div style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>損益推移</div>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto' }}>
        {/* ゼロライン */}
        <line x1={paddingX} y1={zeroY} x2={width - paddingX} y2={zeroY} stroke="#e0e0e0" strokeWidth={1} strokeDasharray="4,4" />
        <text x={paddingX - 4} y={zeroY + 4} textAnchor="end" fontSize={11} fill="#999">0</text>

        {/* 折れ線 */}
        <polyline
          points={polylinePoints}
          fill="none"
          stroke="#1a5f2a"
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* データポイント */}
        {points.map((p, i) => (
          <circle key={i} cx={getX(i)} cy={getY(p.cumProfit)} r={3} fill="#1a5f2a" />
        ))}

        {/* X軸ラベル */}
        {labelIndices.map((idx) => (
          <text key={idx} x={getX(idx)} y={height - 4} textAnchor="middle" fontSize={10} fill="#999">
            {points[idx].date.slice(5)}
          </text>
        ))}

        {/* Y軸ラベル（最大・最小） */}
        {maxProfit !== 0 && (
          <text x={paddingX - 4} y={getY(maxProfit) + 4} textAnchor="end" fontSize={10} fill="#2e7d32">
            {maxProfit >= 1000 ? `${Math.round(maxProfit / 1000)}k` : maxProfit}
          </text>
        )}
        {minProfit !== 0 && (
          <text x={paddingX - 4} y={getY(minProfit) + 4} textAnchor="end" fontSize={10} fill="#c62828">
            {minProfit <= -1000 ? `${Math.round(minProfit / 1000)}k` : minProfit}
          </text>
        )}
      </svg>
    </div>
  );
}

function RecentRecords({ records }: { records: BettingRecord[] }) {
  const navigate = useNavigate();
  const recent = [...records]
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    .slice(0, 5);

  if (recent.length === 0) return null;

  return (
    <div style={{ background: 'white', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 16px',
        background: '#f8f8f8',
        borderBottom: '1px solid #eee',
      }}>
        <span style={{ fontSize: 13, color: '#666', fontWeight: 600 }}>直近の記録</span>
        <button
          onClick={() => navigate('/history')}
          style={{
            background: 'none',
            border: 'none',
            color: '#1a5f2a',
            fontSize: 13,
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          すべて見る
        </button>
      </div>
      {recent.map((record) => {
        const betLabel = BetTypeLabels[record.betType as keyof typeof BetTypeLabels] || record.betType;
        const isWin = record.profit > 0;
        return (
          <div
            key={record.recordId}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 16px',
              borderBottom: '1px solid #f0f0f0',
            }}
          >
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{record.raceName}</div>
              <div style={{ fontSize: 12, color: '#666' }}>
                {record.raceDate} / {record.venue} / {betLabel}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{
                fontSize: 14,
                fontWeight: 600,
                color: isWin ? '#2e7d32' : record.profit < 0 ? '#c62828' : '#666',
              }}>
                {record.profit >= 0 ? '+' : ''}{formatCurrency(record.profit)}
              </div>
              <div style={{
                fontSize: 11,
                color: isWin ? '#2e7d32' : '#c62828',
                fontWeight: 600,
              }}>
                {record.status === 'SETTLED' ? (isWin ? 'HIT' : 'MISS') : record.status === 'PENDING' ? '---' : 'CANCEL'}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function DashboardPage() {
  const {
    records,
    summary,
    thisMonthSummary,
    lastMonthSummary,
    isLoadingRecords,
    isLoadingSummary,
    error,
    fetchRecords,
    fetchAllSummaries,
  } = useBettingStore();
  const { lossLimit, isLoading: isLoadingLossLimit, fetchLossLimit } = useLossLimitStore();

  const isLoading = isLoadingRecords || isLoadingSummary;

  useEffect(() => {
    fetchAllSummaries();
    fetchRecords();
    fetchLossLimit();
  }, [fetchAllSummaries, fetchRecords, fetchLossLimit]);

  // 限度額未設定の場合はセットアップフォームを表示
  if (!isLoadingLossLimit && (lossLimit === null || lossLimit === 0)) {
    return <LossLimitSetupForm />;
  }

  return (
    <div className="fade-in" style={{ padding: 0 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 16, fontSize: 18, fontWeight: 700 }}>
        損益ダッシュボード
      </h2>

      {error && (
        <div style={{ background: '#fce4ec', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
        </div>
      )}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <p>読み込み中...</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* 負け額限度額カード */}
          <LossLimitCard />

          {/* サマリーカード群 */}
          <SummaryCard title="今月の損益" summary={thisMonthSummary} comparison={lastMonthSummary} />
          <SummaryCard title="先月の損益" summary={lastMonthSummary} />
          <SummaryCard title="累計損益" summary={summary} />

          {/* 損益推移グラフ */}
          <ProfitChart records={records} />

          {/* 直近5件プレビュー */}
          <RecentRecords records={records} />

          {/* データがない場合 */}
          {!thisMonthSummary && !lastMonthSummary && !summary && records.length === 0 && (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              <p style={{ fontSize: 16, marginBottom: 8 }}>まだ賭け記録がありません</p>
              <p style={{ fontSize: 13 }}>レースに賭けると、ここに損益が表示されます</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
