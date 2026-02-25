import { useState, useEffect, useCallback, useRef } from 'react';
import { useAppStore } from '../stores/appStore';
import { useCartStore } from '../stores/cartStore';
import type {
  Race,
  RaceDetail,
  Horse,
  BetType,
  BetMethod,
  ColumnSelections,
  AiPredictionsResponse,
  SpeedIndicesResponse,
  AiPrediction,
  SpeedIndex,
} from '../types';
import {
  BetTypeLabels,
  BetTypeRequiredHorses,
  BetTypeOrdered,
  extractOdds,
  getVenueName,
  isJraVenue,
} from '../types';
import { apiClient } from '../api/client';
import { toJapaneseError } from '../stores/purchaseStore';
import { buildJraShutsubaUrl } from '../utils/jraUrl';
import { getBetMethodLabel } from '../utils/betMethods';
import { BetTypeSheet } from '../components/bet/BetTypeSheet';
import { BetMethodSheet } from '../components/bet/BetMethodSheet';
import { CartModal } from '../components/common/CartModal';
import { useBetCalculation } from '../hooks/useBetCalculation';
import { MAX_BET_AMOUNT } from '../constants/betting';
import './SinglePageApp.css';
import './RaceDashboardPage.css';

const initialSelections: ColumnSelections = { col1: [], col2: [], col3: [] };

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
  const from = new Date(today);
  from.setDate(today.getDate() - 14);
  const to = new Date(today);
  to.setDate(today.getDate() + 14);

  const formatDate = (d: Date) => {
    const year = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${m}-${day}`;
  };

  return { from: formatDate(from), to: formatDate(to) };
}

function selectDisplayDates(dates: string[]): string[] {
  if (dates.length === 0) return [];

  const today = new Date();
  const todayStr = getTodayDateStr();
  const dayOfWeek = today.getDay();

  const sortedDates = [...dates].sort();

  if (sortedDates.includes(todayStr)) {
    const todayDate = new Date(todayStr);
    const weekend = sortedDates.filter((d: string) => {
      const diff = Math.abs(new Date(d).getTime() - todayDate.getTime());
      return diff <= 2 * 24 * 60 * 60 * 1000;
    });
    if (weekend.length > 0) {
      if (weekend.length <= 2) return weekend;
      const todayIndex = weekend.indexOf(todayStr);
      if (todayIndex === -1) return weekend.slice(0, 2);
      const nearest = weekend
        .filter((d: string) => d !== todayStr)
        .map((d: string) => ({
          date: d,
          diff: Math.abs(new Date(d).getTime() - todayDate.getTime()),
        }))
        .sort((a, b) => a.diff - b.diff)[0]?.date;
      if (!nearest) return [todayStr];
      return [todayStr, nearest].sort();
    }
  }

  if (dayOfWeek >= 5 || dayOfWeek === 0) {
    const futureDates = sortedDates.filter(d => d >= todayStr);
    if (futureDates.length > 0) return futureDates.slice(0, 2);
  }

  const pastDates = sortedDates.filter(d => d <= todayStr).reverse();
  if (pastDates.length > 0) return pastDates.slice(0, 2).reverse();

  return sortedDates.slice(0, 2);
}

export function SinglePageApp() {
  const showToast = useAppStore((state) => state.showToast);
  const addItem = useCartStore((state) => state.addItem);
  const cartItems = useCartStore((state) => state.items);
  const removeItem = useCartStore((state) => state.removeItem);
  const getTotalAmount = useCartStore((state) => state.getTotalAmount);
  const getItemCount = useCartStore((state) => state.getItemCount);

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

  // ---------- Betting state ----------
  const [betType, setBetType] = useState<BetType>('win');
  const [betMethod, setBetMethod] = useState<BetMethod>('normal');
  const [selections, setSelections] = useState<ColumnSelections>(initialSelections);
  const [betAmount, setBetAmount] = useState(100);
  const [amountInput, setAmountInput] = useState('100');

  // Bottom sheets
  const [isBetTypeSheetOpen, setIsBetTypeSheetOpen] = useState(false);
  const [isBetMethodSheetOpen, setIsBetMethodSheetOpen] = useState(false);

  // Cart modal
  const [isCartModalOpen, setIsCartModalOpen] = useState(false);

  // Bet count calculation
  const { betCount } = useBetCalculation(betType, betMethod, selections);

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
        const displayDates = selectDisplayDates(response.data);
        setDateButtons(displayDates);

        if (!isInitialDateSet.current && displayDates.length > 0) {
          const todayStr = getTodayDateStr();
          const todayIdx = displayDates.indexOf(todayStr);
          if (todayIdx >= 0) {
            setSelectedDateIdx(todayIdx);
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
      if (!datesLoading) setRacesLoading(false);
      return;
    }
    const selectedDate = dateButtons[selectedDateIdx];
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

  // Auto-select first race when filtered races change
  useEffect(() => {
    if (filteredRaces.length > 0 && !selectedRaceId) {
      setSelectedRaceId(filteredRaces[0].id);
    }
  }, [filteredRaces, selectedRaceId]);

  // =============================================
  // FETCH: Race detail + AI predictions + speed indices
  // =============================================
  useEffect(() => {
    if (!selectedRaceId) {
      setRace(null);
      setAiPredictions(null);
      setSpeedIndices(null);
      setRaceError(null);
      return;
    }

    let isMounted = true;

    const fetchDetail = async () => {
      setRaceLoading(true);
      setRaceError(null);
      setAiPredictions(null);
      setSpeedIndices(null);

      // Reset betting state for new race
      setBetType('win');
      setBetMethod('normal');
      setSelections(initialSelections);
      setBetAmount(100);
      setAmountInput('100');

      const decodedId = decodeURIComponent(selectedRaceId);

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
  }, [selectedRaceId]);

  // =============================================
  // Betting handlers (copied from RaceDashboardPage)
  // =============================================
  const handleBetTypeChange = (type: BetType) => {
    setBetType(type);
    setBetMethod('normal');
    setSelections(initialSelections);
  };

  const handleBetMethodChange = (method: BetMethod) => {
    setBetMethod(method);
    setSelections(initialSelections);
  };

  const handleAmountMinus = () => {
    if (betAmount > 100) {
      const newAmount = betAmount <= 500 ? betAmount - 100 : betAmount - 500;
      const clamped = Math.max(100, newAmount);
      setBetAmount(clamped);
      setAmountInput(String(clamped));
    }
  };

  const handleAmountPlus = () => {
    const increment = betAmount < 500 ? 100 : 500;
    const effectiveBetCount = betCount > 0 ? betCount : 1;
    const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
    setBetAmount((prev) => {
      const next = Math.min(prev + increment, maxPerBet);
      setAmountInput(String(next));
      return next;
    });
  };

  const toggleHorseSelection = useCallback((horseNumber: number) => {
    setSelections((prev) => {
      const col = prev.col1;
      const isSelected = col.includes(horseNumber);
      const required = BetTypeRequiredHorses[betType];

      if (betMethod === 'normal') {
        if (isSelected) {
          return { ...prev, col1: col.filter((n) => n !== horseNumber) };
        }
        if (col.length >= required) {
          return { ...prev, col1: [...col.slice(0, required - 1), horseNumber] };
        }
        return { ...prev, col1: [...col, horseNumber] };
      }

      if (isSelected) {
        return { ...prev, col1: col.filter((n) => n !== horseNumber) };
      }
      return { ...prev, col1: [...col, horseNumber] };
    });
  }, [betType, betMethod]);

  const getSelectionDisplay = () => {
    const hasAny = selections.col1.length > 0 || selections.col2.length > 0 || selections.col3.length > 0;
    if (!hasAny) return null;

    if (betMethod.startsWith('nagashi')) {
      const required = BetTypeRequiredHorses[betType];
      const ordered = BetTypeOrdered[betType];

      if (required === 2 && ordered) {
        if (betMethod === 'nagashi_2') {
          const partnerText = selections.col2.length > 0 ? `1着:${selections.col2.join(',')}` : '';
          const axisText = selections.col1.length > 0 ? `2着軸:${selections.col1.join(',')}` : '';
          return [partnerText, axisText].filter(Boolean).join(' → ');
        }
        const axisText = selections.col1.length > 0 ? `1着軸:${selections.col1.join(',')}` : '';
        const partnerText = selections.col2.length > 0 ? `2着:${selections.col2.join(',')}` : '';
        return [axisText, partnerText].filter(Boolean).join(' → ');
      }

      const axisText = selections.col1.length > 0 ? `軸:${selections.col1.join(',')}` : '';
      const partnerText = selections.col2.length > 0 ? `相手:${selections.col2.join(',')}` : '';
      return [axisText, partnerText].filter(Boolean).join(' → ');
    } else if (betMethod === 'formation') {
      const parts = [
        selections.col1.length > 0 ? selections.col1.join(',') : '-',
        selections.col2.length > 0 ? selections.col2.join(',') : '-',
        selections.col3.length > 0 ? selections.col3.join(',') : '-',
      ];
      const required = BetTypeRequiredHorses[betType];
      return parts.slice(0, required).join(' x ');
    } else {
      const sorted = [...selections.col1].sort((a, b) => a - b);
      return sorted.join(' - ');
    }
  };

  const handleAddToCart = async () => {
    if (!race || betCount === 0) return;

    let horseNumbersDisplay: number[];
    if (betMethod === 'formation' || betMethod.startsWith('nagashi')) {
      const allNumbers = [...new Set([...selections.col1, ...selections.col2, ...selections.col3])];
      horseNumbersDisplay = allNumbers.sort((a, b) => a - b);
    } else {
      horseNumbersDisplay = [...selections.col1].sort((a, b) => a - b);
    }

    const betDisplay = getSelectionDisplay() || horseNumbersDisplay.join('-');

    let odds: number | undefined;
    let oddsMin: number | undefined;
    let oddsMax: number | undefined;
    try {
      const oddsResult = await apiClient.getAllOdds(race.id);
      if (oddsResult.success && oddsResult.data) {
        const extracted = extractOdds(oddsResult.data, betType, horseNumbersDisplay);
        odds = extracted.odds;
        oddsMin = extracted.oddsMin;
        oddsMax = extracted.oddsMax;
      }
    } catch (err: unknown) {
      console.warn('Failed to fetch odds when adding item to cart:', err);
    }

    const result = addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType,
      betMethod,
      horseNumbers: horseNumbersDisplay,
      betDisplay,
      betCount,
      columnSelections: { ...selections },
      amount: betAmount * betCount,
      odds,
      oddsMin,
      oddsMax,
    });

    if (result === 'different_race' || result === 'invalid_amount') {
      const message = result === 'different_race'
        ? 'カートには同じレースの買い目のみ追加できます'
        : '金額が範囲外です';
      showToast(message, 'error');
      return;
    }

    setSelections(initialSelections);
    setBetAmount(100);
    setAmountInput('100');
    showToast(result === 'merged' ? '同じ買い目の金額を合算しました' : 'カートに追加しました');
  };

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

  const isHorseSelected = (horseNumber: number) => selections.col1.includes(horseNumber);

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

  // Betting panel derived values
  const required = BetTypeRequiredHorses[betType];
  const canSelectMethod = required > 1;
  const selectionDisplay = getSelectionDisplay();
  const totalAmount = betAmount * betCount;
  const cartTotal = getTotalAmount();
  const cartItemCount = getItemCount();

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
                className={`race-num-pill ${selectedRaceId === r.id ? 'active' : ''} ${r.gradeClass && ['G1', 'G2', 'G3'].includes(r.gradeClass) ? 'has-grade' : ''}`}
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
      {!selectedRaceId ? (
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

          {/* Body: Table + Betting Panel */}
          <div className="dashboard-body">
            {/* Main Table */}
            <div className="dashboard-table-area">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th></th>
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
                  {race.horses.map((horse: Horse) => {
                    const selected = isHorseSelected(horse.number);
                    return (
                      <tr
                        key={horse.number}
                        className={selected ? 'row-selected' : ''}
                        onClick={() => toggleHorseSelection(horse.number)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="td-checkbox">
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() => toggleHorseSelection(horse.number)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
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
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Betting Panel */}
            <div className="dashboard-betting-panel">
              <div className="betting-panel-title">馬券購入</div>

              {/* Bet type + method selectors */}
              <div className="panel-selector-row">
                <button
                  className="panel-selector"
                  onClick={() => setIsBetTypeSheetOpen(true)}
                >
                  <span>{BetTypeLabels[betType]}</span>
                  <span className="arrow">▼</span>
                </button>
                <button
                  className={`panel-selector ${!canSelectMethod ? 'disabled' : ''}`}
                  onClick={() => canSelectMethod && setIsBetMethodSheetOpen(true)}
                  disabled={!canSelectMethod}
                >
                  <span>{getBetMethodLabel(betMethod, betType)}</span>
                  <span className="arrow">▼</span>
                </button>
              </div>

              {/* Selection display */}
              <div className={`panel-selection-display ${selectionDisplay ? 'has-selection' : ''}`}>
                {selectionDisplay ? (
                  <>
                    <span className="panel-selection-numbers">{selectionDisplay}</span>
                    {betCount > 0 && <span className="panel-bet-count">{betCount}点</span>}
                    <button className="panel-clear-btn" onClick={() => setSelections(initialSelections)}>
                      クリア
                    </button>
                  </>
                ) : (
                  <span>表のチェックボックスから馬を選択</span>
                )}
              </div>

              {/* Amount input */}
              <div className="panel-amount-row">
                <span className="panel-amount-label">金額</span>
                <div className="panel-amount-input-wrapper">
                  <button className="panel-stepper-btn" onClick={handleAmountMinus}>-</button>
                  <div className="panel-amount-center">
                    <span className="panel-currency">¥</span>
                    <input
                      type="number"
                      className="panel-amount-input"
                      value={amountInput}
                      onChange={(e) => {
                        const raw = e.target.value;
                        const parsed = parseInt(raw, 10);
                        if (!isNaN(parsed) && parsed > 0) {
                          const effectiveBetCount = betCount > 0 ? betCount : 1;
                          const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
                          const clamped = Math.min(maxPerBet, Math.max(100, parsed));
                          setBetAmount(clamped);
                          setAmountInput(String(clamped));
                        } else {
                          setAmountInput(raw);
                        }
                      }}
                      onBlur={() => {
                        const effectiveBetCount = betCount > 0 ? betCount : 1;
                        const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
                        const parsed = parseInt(amountInput, 10);
                        const clamped = Math.min(maxPerBet, Math.max(100, isNaN(parsed) ? 100 : parsed));
                        setBetAmount(clamped);
                        setAmountInput(String(clamped));
                      }}
                    />
                  </div>
                  <button className="panel-stepper-btn" onClick={handleAmountPlus}>+</button>
                </div>
              </div>

              <div className="panel-amount-presets">
                {[100, 500, 1000, 5000].map((amount) => (
                  <button
                    key={amount}
                    className="panel-preset-btn"
                    onClick={() => { setBetAmount(amount); setAmountInput(String(amount)); }}
                  >
                    ¥{amount.toLocaleString()}
                  </button>
                ))}
              </div>

              {/* Bet summary */}
              {betCount > 0 && (
                <div className="panel-bet-summary">
                  <span>{betCount}点</span>
                  <span>¥{totalAmount.toLocaleString()}</span>
                </div>
              )}

              {/* Add to cart */}
              <button
                className="panel-add-btn"
                onClick={handleAddToCart}
                disabled={betCount === 0}
              >
                カートに追加
              </button>

              {/* Cart section */}
              <hr className="panel-cart-divider" />
              <div className="panel-cart-title">カート</div>

              {cartItems.length === 0 ? (
                <div className="panel-cart-empty">カートは空です</div>
              ) : (
                <>
                  {cartItems.map((item) => (
                    <div key={item.id} className="panel-cart-item">
                      <div className="panel-cart-item-info">
                        <span className="panel-cart-bet-type">{BetTypeLabels[item.betType]}</span>
                        <span className="panel-cart-bet-display">
                          {item.betDisplay || item.horseNumbers.join('-')}
                        </span>
                      </div>
                      <span className="panel-cart-item-amount">¥{item.amount.toLocaleString()}</span>
                      <button
                        className="panel-cart-remove"
                        onClick={() => removeItem(item.id)}
                        title="削除"
                      >
                        ×
                      </button>
                    </div>
                  ))}

                  <div className="panel-cart-total">
                    <span>合計</span>
                    <span>¥{cartTotal.toLocaleString()}</span>
                  </div>

                  <button
                    className="panel-confirm-btn"
                    onClick={() => setIsCartModalOpen(true)}
                  >
                    購入確認へ →
                  </button>
                </>
              )}
            </div>
          </div>
        </>
      )}

      {/* Floating cart button */}
      <button
        className="floating-cart-btn"
        onClick={() => setIsCartModalOpen(true)}
        type="button"
        aria-label="カートを開く"
      >
        🛒
        {cartItemCount > 0 && (
          <span className="floating-cart-badge">{cartItemCount}</span>
        )}
      </button>

      {/* Cart modal */}
      <CartModal
        isOpen={isCartModalOpen}
        onClose={() => setIsCartModalOpen(false)}
      />

      {/* Bottom sheets */}
      <BetTypeSheet
        isOpen={isBetTypeSheetOpen}
        onClose={() => setIsBetTypeSheetOpen(false)}
        selectedType={betType}
        onSelect={handleBetTypeChange}
      />
      <BetMethodSheet
        isOpen={isBetMethodSheetOpen}
        onClose={() => setIsBetMethodSheetOpen(false)}
        betType={betType}
        selectedMethod={betMethod}
        onSelect={handleBetMethodChange}
      />
    </div>
  );
}
