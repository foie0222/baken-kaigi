import { useEffect, useState, useCallback } from 'react';
import { useBettingStore } from '../stores/bettingStore';
import { BetTypeLabels, VenueNames } from '../types';
import type { BettingRecordFilter } from '../types';

const PAGE_SIZE = 20;

const betTypeOptions = [
  { value: '', label: 'すべての券種' },
  { value: 'win', label: '単勝' },
  { value: 'place', label: '複勝' },
  { value: 'quinella', label: '馬連' },
  { value: 'quinella_place', label: 'ワイド' },
  { value: 'exacta', label: '馬単' },
  { value: 'trio', label: '三連複' },
  { value: 'trifecta', label: '三連単' },
];

const venueOptions = [
  { value: '', label: 'すべてのレース場' },
  ...Object.entries(VenueNames).map(([, name]) => ({
    value: name,
    label: name,
  })),
];

function formatCurrency(value: number): string {
  const prefix = value < 0 ? '-' : '';
  return `${prefix}¥${Math.abs(value).toLocaleString()}`;
}

export function HistoryPage() {
  const { records, isLoading, error, fetchRecords } = useBettingStore();
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [venue, setVenue] = useState('');
  const [betType, setBetType] = useState('');
  const [page, setPage] = useState(0);

  const applyFilters = useCallback(() => {
    const filters: BettingRecordFilter = {};
    if (dateFrom) filters.dateFrom = dateFrom;
    if (dateTo) filters.dateTo = dateTo;
    if (venue) filters.venue = venue;
    if (betType) filters.betType = betType;
    setPage(0);
    fetchRecords(filters);
  }, [dateFrom, dateTo, venue, betType, fetchRecords]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  const totalPages = Math.max(1, Math.ceil(records.length / PAGE_SIZE));
  const pagedRecords = records.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="fade-in" style={{ padding: 0 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 16, fontSize: 18, fontWeight: 700 }}>
        賭け履歴
      </h2>

      {error && (
        <div style={{ background: '#fce4ec', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
        </div>
      )}

      {/* フィルタ */}
      <div style={{
        background: 'white',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16,
      }}>
        <div style={{ fontSize: 13, color: '#666', marginBottom: 12, fontWeight: 600 }}>
          フィルタ
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 8,
                fontSize: 13,
              }}
            />
            <span style={{ display: 'flex', alignItems: 'center', color: '#999', fontSize: 13 }}>~</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 8,
                fontSize: 13,
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <select
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 8,
                fontSize: 13,
                background: 'white',
              }}
            >
              {venueOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <select
              value={betType}
              onChange={(e) => setBetType(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 8,
                fontSize: 13,
                background: 'white',
              }}
            >
              {betTypeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={applyFilters}
            style={{
              background: '#1a5f2a',
              color: 'white',
              border: 'none',
              padding: '10px 16px',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            検索
          </button>
        </div>
      </div>

      {/* 一覧 */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <p>読み込み中...</p>
        </div>
      ) : records.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          <p style={{ fontSize: 16 }}>賭け履歴はありません</p>
        </div>
      ) : (
        <>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>
            {records.length}件の記録
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pagedRecords.map((record) => {
              const betLabel = BetTypeLabels[record.betType as keyof typeof BetTypeLabels] || record.betType;
              const isWin = record.profit > 0;
              const isSettled = record.status === 'SETTLED';

              return (
                <div
                  key={record.recordId}
                  style={{
                    background: 'white',
                    borderRadius: 12,
                    padding: 14,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{
                          fontSize: 16,
                          fontWeight: 700,
                          color: isSettled ? (isWin ? '#2e7d32' : '#c62828') : '#666',
                        }}>
                          {isSettled ? (isWin ? 'HIT' : 'MISS') : record.status === 'PENDING' ? '---' : 'CANCEL'}
                        </span>
                        <span style={{ fontSize: 14, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {record.raceName}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#666', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <span>{record.raceDate}</span>
                        <span>{record.venue}</span>
                        <span style={{
                          background: '#1a5f2a',
                          color: 'white',
                          padding: '1px 6px',
                          borderRadius: 3,
                          fontSize: 11,
                          fontWeight: 600,
                        }}>
                          {betLabel}
                        </span>
                        <span>{record.horseNumbers.join('-')}</span>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
                      <div style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: isWin ? '#2e7d32' : record.profit < 0 ? '#c62828' : '#666',
                      }}>
                        {record.profit >= 0 ? '+' : ''}{formatCurrency(record.profit)}
                      </div>
                      <div style={{ fontSize: 12, color: '#999' }}>
                        {formatCurrency(record.amount)} → {formatCurrency(record.payout)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ページネーション */}
          {totalPages > 1 && (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 16,
              marginTop: 16,
              padding: 8,
            }}>
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                style={{
                  padding: '8px 16px',
                  background: page === 0 ? '#eee' : '#1a5f2a',
                  color: page === 0 ? '#999' : 'white',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: page === 0 ? 'default' : 'pointer',
                }}
              >
                前へ
              </button>
              <span style={{ fontSize: 13, color: '#666' }}>
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                style={{
                  padding: '8px 16px',
                  background: page >= totalPages - 1 ? '#eee' : '#1a5f2a',
                  color: page >= totalPages - 1 ? '#999' : 'white',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: page >= totalPages - 1 ? 'default' : 'pointer',
                }}
              >
                次へ
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
