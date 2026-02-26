import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  Race,
  RaceDetail,
  Horse,
  AiPredictionsResponse,
  SpeedIndicesResponse,
  AiPrediction,
  SpeedIndex,
} from '../types';
import {
  getVenueName,
  isJraVenue,
} from '../types';
import { apiClient } from '../api/client';
import { toJapaneseError } from '../stores/purchaseStore';
import { buildJraShutsubaUrl } from '../utils/jraUrl';
import './SinglePageApp.css';
import './RaceDashboardPage.css';

// AI prediction source display names
const AI_SOURCE_NAMES: Record<string, string> = {
  'ai-shisu': 'AI指数',
  'keiba-ai-athena': 'ATHENA',
  'keiba-ai-navi': 'AIナビ',
  'umamax': 'うまmax',
  'muryou-keiba-ai': '無料AI',
};

// Speed index source display names
const SPEED_SOURCE_NAMES: Record<string, string> = {
  'jiro8-speed': 'Jiro8',
  'kichiuma-speed': '吉馬',
  'daily-speed': 'デイリー',
};

// ランク（1位〜N位）に応じたヒートマップスタイルを返す
function getRankStyle(rank: number, total: number): { color: string; backgroundColor: string; fontWeight?: number } {
  if (total <= 1) return { color: 'var(--color-text)', backgroundColor: 'transparent' };
  // 0.0(1位) 〜 1.0(最下位) に正規化
  const t = (rank - 1) / (total - 1);
  if (t <= 0.15) return { color: '#fff', backgroundColor: 'rgba(233, 69, 96, 0.35)', fontWeight: 700 };   // 上位15% - 赤
  if (t <= 0.30) return { color: '#f8b4c0', backgroundColor: 'rgba(233, 69, 96, 0.15)' };                   // 上位30% - 薄赤
  if (t <= 0.50) return { color: '#c8b080', backgroundColor: 'rgba(192, 160, 96, 0.08)' };                   // 中位 - 金
  if (t <= 0.70) return { color: 'var(--color-text-muted)', backgroundColor: 'transparent' };                // 下位半分 - 薄
  return { color: 'rgba(255,255,255,0.25)', backgroundColor: 'transparent' };                                // 下位 - 暗い
}

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr);
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const dow = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()];
  return `${m}/${day}(${dow})`;
}

function getTodayDateStr(): string {
  const today = new Date();
  const year = today.getFullYear();
  const m = String(today.getMonth() + 1).padStart(2, '0');
  const d = String(today.getDate()).padStart(2, '0');
  return `${year}-${m}-${d}`;
}

function getSearchRange(): { from: string; to: string } {
  const today = new Date();
  const year = today.getFullYear();
  const from = `${year}-01-01`;
  const to = `${year}-12-31`;
  return { from, to };
}

export function SinglePageApp() {
  // ---------- Date / Venue / Race selector state ----------
  const [dateButtons, setDateButtons] = useState<string[]>([]);
  const [selectedDateIdx, setSelectedDateIdx] = useState(0);
  const [datesLoading, setDatesLoading] = useState(true);

  const [races, setRaces] = useState<Race[]>([]);
  const [venues, setVenues] = useState<string[]>([]);
  const [selectedVenue, setSelectedVenue] = useState<string | null>(null);
  const [racesLoading, setRacesLoading] = useState(false);

  const [selectedRaceId, setSelectedRaceId] = useState<string | null>(null);

  const isInitialDateSet = useRef(false);

  // ---------- Race detail state ----------
  const [race, setRace] = useState<RaceDetail | null>(null);
  const [raceLoading, setRaceLoading] = useState(false);
  const [raceError, setRaceError] = useState<string | null>(null);

  // AI predictions & speed indices
  const [aiPredictions, setAiPredictions] = useState<AiPredictionsResponse | null>(null);
  const [speedIndices, setSpeedIndices] = useState<SpeedIndicesResponse | null>(null);

  // =============================================
  // FETCH: Race dates
  // =============================================
  useEffect(() => {
    let isMounted = true;

    const fetchDates = async () => {
      setDatesLoading(true);
      const { from, to } = getSearchRange();
      const response = await apiClient.getRaceDates(from, to);

      if (!isMounted) return;

      if (response.success && response.data) {
        const allDates = [...response.data].sort();
        setDateButtons(allDates);

        if (!isInitialDateSet.current && allDates.length > 0) {
          // 今日以前の直近開催日をデフォルト選択
          const todayStr = getTodayDateStr();
          const todayIdx = allDates.indexOf(todayStr);
          if (todayIdx >= 0) {
            setSelectedDateIdx(todayIdx);
          } else {
            // 今日が開催日でなければ、直近の過去開催日。過去がなければ最初の未来開催日
            const pastIdx = allDates.filter(d => d <= todayStr).length - 1;
            setSelectedDateIdx(pastIdx >= 0 ? pastIdx : 0);
          }
          isInitialDateSet.current = true;
        }
      } else {
        setDateButtons([]);
      }
      setDatesLoading(false);
    };

    fetchDates();
    return () => { isMounted = false; };
  }, []);

  // =============================================
  // FETCH: Races for selected date
  // =============================================
  const fetchRaces = useCallback(async (date: string, showLoading = true) => {
    if (showLoading) setRacesLoading(true);

    const response = await apiClient.getRaces(date);

    if (response.success && response.data) {
      const filteredJraRaces = response.data.races.filter(r => isJraVenue(r.venue));
      setRaces(filteredJraRaces);
      const fetchedVenues = response.data.venues.filter(isJraVenue);
      setVenues(fetchedVenues);
      if (fetchedVenues.length > 0) {
        setSelectedVenue((prev) => {
          if (!prev || !fetchedVenues.includes(prev)) {
            return fetchedVenues[0];
          }
          return prev;
        });
      }
    } else {
      setRaces([]);
      setVenues([]);
    }

    setRacesLoading(false);
  }, []);

  useEffect(() => {
    if (dateButtons.length === 0 || selectedDateIdx >= dateButtons.length) {
      return;
    }
    const selectedDate = dateButtons[selectedDateIdx];
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetchRaces is async; setState occurs after await
    void fetchRaces(selectedDate, true);
  }, [selectedDateIdx, dateButtons, fetchRaces, datesLoading]);

  // Auto-refresh for today
  useEffect(() => {
    if (dateButtons.length === 0 || selectedDateIdx >= dateButtons.length) return;
    const selectedDate = dateButtons[selectedDateIdx];
    if (selectedDate !== getTodayDateStr()) return;

    const intervalId = setInterval(
      () => void fetchRaces(selectedDate, false),
      60 * 1000
    );
    return () => clearInterval(intervalId);
  }, [selectedDateIdx, dateButtons, fetchRaces]);

  // =============================================
  // Filtered races for current venue
  // =============================================
  const filteredRaces = selectedVenue
    ? races.filter((r) => r.venue === selectedVenue)
    : races;

  // 有効なレースID: 明示的に選択されていなければ最初のレースを使用
  const effectiveRaceId = selectedRaceId ?? (filteredRaces.length > 0 ? filteredRaces[0].id : null);

  // =============================================
  // FETCH: Race detail + AI predictions + speed indices
  // =============================================
  useEffect(() => {
    if (!effectiveRaceId) {
      return;
    }

    let isMounted = true;

    const fetchDetail = async () => {
      setRace(null);
      setAiPredictions(null);
      setSpeedIndices(null);
      setRaceError(null);
      setRaceLoading(true);

      const decodedId = decodeURIComponent(effectiveRaceId);

      const response = await apiClient.getRaceDetail(decodedId);
      if (!isMounted) return;

      if (response.success && response.data) {
        setRace(response.data);
      } else {
        setRaceError(toJapaneseError(response.error, 'レース詳細の取得に失敗しました'));
      }
      setRaceLoading(false);

      // Fetch AI predictions & speed indices (non-blocking)
      apiClient.getAiPredictions(decodedId).then((res) => {
        if (isMounted && res.success && res.data) {
          setAiPredictions(res.data);
        }
      });

      apiClient.getSpeedIndices(decodedId).then((res) => {
        if (isMounted && res.success && res.data) {
          setSpeedIndices(res.data);
        }
      });
    };

    fetchDetail();
    return () => { isMounted = false; };
  }, [effectiveRaceId]);

  // AI / Speed lookups
  const aiSourceKeys = aiPredictions ? Object.keys(aiPredictions.predictions) : [];
  const speedSourceKeys = speedIndices ? Object.keys(speedIndices.indices) : [];

  const getAiScore = (horseNumber: number, sourceKey: string): AiPrediction | undefined => {
    if (!aiPredictions) return undefined;
    const preds = aiPredictions.predictions[sourceKey];
    if (!preds) return undefined;
    return preds.find((p) => p.horse_number === horseNumber);
  };

  const getSpeedScore = (horseNumber: number, sourceKey: string): SpeedIndex | undefined => {
    if (!speedIndices) return undefined;
    const idxs = speedIndices.indices[sourceKey];
    if (!idxs) return undefined;
    return idxs.find((s) => s.horse_number === horseNumber);
  };

  // ソース別ランキングマップ: sourceKey → Map<horseNumber, {rank, total}>
  const aiRankMap = (() => {
    const map: Record<string, Map<number, { rank: number; total: number }>> = {};
    for (const key of aiSourceKeys) {
      const preds = aiPredictions?.predictions[key];
      if (!preds || preds.length === 0) continue;
      const sorted = [...preds].sort((a, b) => b.score - a.score);
      const m = new Map<number, { rank: number; total: number }>();
      sorted.forEach((p, i) => m.set(p.horse_number, { rank: i + 1, total: sorted.length }));
      map[key] = m;
    }
    return map;
  })();

  const speedRankMap = (() => {
    const map: Record<string, Map<number, { rank: number; total: number }>> = {};
    for (const key of speedSourceKeys) {
      const idxs = speedIndices?.indices[key];
      if (!idxs || idxs.length === 0) continue;
      const sorted = [...idxs].sort((a, b) => b.speed_index - a.speed_index);
      const m = new Map<number, { rank: number; total: number }>();
      sorted.forEach((s, i) => m.set(s.horse_number, { rank: i + 1, total: sorted.length }));
      map[key] = m;
    }
    return map;
  })();

  // オッズから人気順を計算（APIがpopularity=0を返す場合のフォールバック）
  const popularityMap = (() => {
    if (!race) return new Map<number, number>();
    const horsesWithOdds = race.horses
      .filter((h: Horse) => h.odds > 0)
      .map((h: Horse) => ({ number: h.number, odds: h.odds }))
      .sort((a, b) => a.odds - b.odds);
    const map = new Map<number, number>();
    horsesWithOdds.forEach((h, i) => map.set(h.number, i + 1));
    return map;
  })();

  const getPopularity = (horse: Horse): number => {
    if (horse.popularity > 0) return horse.popularity;
    return popularityMap.get(horse.number) || 0;
  };

  // Race number click handler
  const handleRaceNumberClick = (raceId: string) => {
    setSelectedRaceId(raceId);
  };

  // Venue change handler - clear race selection
  const handleVenueChange = (venue: string) => {
    setSelectedVenue(venue);
    setSelectedRaceId(null);
  };

  // Date change handler - clear race and venue selection
  const handleDateChange = (idx: number) => {
    setSelectedDateIdx(idx);
    setSelectedRaceId(null);
  };

  // JRA URL for current race
  const jraUrl = race ? buildJraShutsubaUrl(race) : null;

  return (
    <div className="fade-in">
      {/* =============================================
          Race Selector Bar
          ============================================= */}
      <div className="race-selector-bar">
        {/* Date pills */}
        <div className="selector-group">
          {datesLoading ? (
            <span className="selector-loading">読込中...</span>
          ) : dateButtons.length === 0 ? (
            <span className="selector-loading">開催日なし</span>
          ) : (
            dateButtons.map((dateStr, index) => (
              <button
                key={dateStr}
                ref={selectedDateIdx === index ? (el) => { if (el && el.dataset.scrolledOnce !== 'true') { el.scrollIntoView({ block: 'nearest', inline: 'center' }); el.dataset.scrolledOnce = 'true'; } } : undefined}
                className={`date-pill ${selectedDateIdx === index ? 'active' : ''}`}
                onClick={() => handleDateChange(index)}
              >
                {formatDateLabel(dateStr)}
              </button>
            ))
          )}
        </div>

        <div className="selector-divider" />

        {/* Venue pills */}
        <div className="selector-group">
          {venues.map((venue) => (
            <button
              key={venue}
              className={`venue-pill ${selectedVenue === venue ? 'active' : ''}`}
              onClick={() => handleVenueChange(venue)}
            >
              {getVenueName(venue)}
            </button>
          ))}
        </div>

        <div className="selector-divider" />

        {/* Race number pills */}
        <div className="race-number-pills">
          {racesLoading ? (
            <span className="selector-loading">...</span>
          ) : (
            filteredRaces.map((r) => (
              <button
                key={r.id}
                className={`race-num-pill ${effectiveRaceId === r.id ? 'active' : ''} ${r.gradeClass && ['G1', 'G2', 'G3'].includes(r.gradeClass) ? 'has-grade' : ''}`}
                onClick={() => handleRaceNumberClick(r.id)}
                title={r.name || `${r.number}R`}
              >
                {r.number.replace('R', '')}
              </button>
            ))
          )}
        </div>
      </div>

      {/* =============================================
          Main Content Area
          ============================================= */}
      {!effectiveRaceId ? (
        /* Empty state - no race selected */
        <div className="spa-empty-state">
          <div className="spa-empty-icon">🏇</div>
          <div className="spa-empty-text">レースを選択してください</div>
          <div className="spa-empty-subtext">
            上のバーから日付・会場・レース番号を選んでください
          </div>
        </div>
      ) : raceLoading ? (
        /* Loading race detail */
        <div className="spa-dashboard-loading">読み込み中...</div>
      ) : raceError || !race ? (
        /* Error state */
        <div className="dashboard-error">
          <div className="dashboard-error-icon">!</div>
          <h2 className="dashboard-error-title">レースが見つかりませんでした</h2>
          <p className="dashboard-error-message">
            {raceError || '指定されたレースは存在しないか、データがまだ公開されていません。'}
          </p>
        </div>
      ) : (
        /* Race detail loaded - show dashboard */
        <>
          {/* Race info bar */}
          <div className="spa-race-info">
            <span className="spa-race-badge">{getVenueName(race.venue)} {race.number}</span>
            <span className="spa-race-name">{race.name}</span>
            <div className="spa-race-conditions">
              {race.condition && <span className="condition-tag">馬場: {race.condition}</span>}
              {race.trackType && <span className="condition-tag">{race.trackType}</span>}
              {race.distance && <span className="condition-tag">{race.distance}m</span>}
              {race.time && <span className="condition-tag">{race.time} 発走</span>}
            </div>
            {jraUrl && (
              <div className="spa-jra-link">
                <a href={jraUrl} target="_blank" rel="noopener noreferrer" className="jra-link-btn">
                  <span>JRA出馬表</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              </div>
            )}
          </div>

          {/* Main Table */}
          <div className="dashboard-table-area">
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th></th>
                  <th>馬番</th>
                    <th style={{ textAlign: 'left', paddingLeft: 10 }}>馬名</th>
                    <th>体重</th>
                    <th>オッズ</th>
                    <th>人気</th>
                    {aiSourceKeys.map((key) => (
                      <th key={`ai-${key}`} className="col-group-ai">
                        {AI_SOURCE_NAMES[key] || key}
                      </th>
                    ))}
                    {speedSourceKeys.map((key) => (
                      <th key={`sp-${key}`} className="col-group-speed">
                        {SPEED_SOURCE_NAMES[key] || key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {race.horses.map((horse: Horse) => (
                      <tr key={horse.number}>
                        <td className="td-waku">
                          <div
                            className="waku-indicator"
                            style={{ backgroundColor: horse.color }}
                          />
                        </td>
                        <td className="td-horse-number">
                          <span
                            className="horse-num-circle"
                            style={{
                              backgroundColor: horse.color,
                              color: horse.textColor,
                              borderColor: horse.color === '#FFFFFF' ? 'rgba(255,255,255,0.3)' : horse.color,
                            }}
                          >
                            {horse.number}
                          </span>
                        </td>
                        <td className="td-horse-name">
                          <div className="horse-name-text">{horse.name}</div>
                          <div className="horse-jockey-text">{horse.jockey}</div>
                        </td>
                        <td className="td-weight">
                          {horse.weight ? (
                            <>
                              <span className="weight-value">{horse.weight}</span>
                              {horse.weightDiff != null && (
                                <span className={`weight-diff ${horse.weightDiff > 0 ? 'plus' : horse.weightDiff < 0 ? 'minus' : 'zero'}`}>
                                  ({horse.weightDiff > 0 ? '+' : ''}{horse.weightDiff})
                                </span>
                              )}
                            </>
                          ) : (
                            <span className="no-data">-</span>
                          )}
                        </td>
                        <td className={`td-odds ${(() => { const p = getPopularity(horse); return p === 1 ? 'odds-top1' : p === 2 ? 'odds-top2' : p === 3 ? 'odds-top3' : ''; })()}`}>
                          {horse.odds > 0 ? horse.odds.toFixed(1) : <span className="no-data">-</span>}
                        </td>
                        <td className="td-popularity">
                          {(() => {
                            const pop = getPopularity(horse);
                            return (
                              <span className={`popularity-badge ${pop > 0 && pop <= 3 ? `pop-${pop}` : ''}`}>
                                {pop > 0 ? pop : '-'}
                              </span>
                            );
                          })()}
                        </td>
                        {aiSourceKeys.map((key, i) => {
                          const pred = getAiScore(horse.number, key);
                          const rankInfo = pred ? aiRankMap[key]?.get(horse.number) : undefined;
                          const style = rankInfo ? getRankStyle(rankInfo.rank, rankInfo.total) : {};
                          return (
                            <td
                              key={`ai-${key}`}
                              className={`td-ai-score${i === 0 ? ' col-group-first-ai' : ''}`}
                              style={pred ? style : {}}
                            >
                              {pred ? (
                                <>
                                  <span className="score-value">{pred.score}</span>
                                  {rankInfo && rankInfo.rank <= 3 && (
                                    <span className={`score-rank rank-${rankInfo.rank}`}>{rankInfo.rank}</span>
                                  )}
                                </>
                              ) : <span className="no-data">-</span>}
                            </td>
                          );
                        })}
                        {speedSourceKeys.map((key, i) => {
                          const idx = getSpeedScore(horse.number, key);
                          const rankInfo = idx ? speedRankMap[key]?.get(horse.number) : undefined;
                          const style = rankInfo ? getRankStyle(rankInfo.rank, rankInfo.total) : {};
                          return (
                            <td
                              key={`sp-${key}`}
                              className={`td-speed-index${i === 0 ? ' col-group-first-speed' : ''}`}
                              style={idx ? style : {}}
                            >
                              {idx ? (
                                <>
                                  <span className="score-value">{idx.speed_index}</span>
                                  {rankInfo && rankInfo.rank <= 3 && (
                                    <span className={`score-rank rank-${rankInfo.rank}`}>{rankInfo.rank}</span>
                                  )}
                                </>
                              ) : <span className="no-data">-</span>}
                            </td>
                          );
                        })}
                      </tr>
                  ))}
                </tbody>
              </table>
            </div>
        </>
      )}
    </div>
  );
}
