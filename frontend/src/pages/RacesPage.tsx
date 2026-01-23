import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Race, RaceGrade } from '../types';
import { getVenueName } from '../types';
import { apiClient } from '../api/client';

// グレードバッジのCSSクラスを取得
function getGradeBadgeClass(grade: RaceGrade | undefined): string {
  if (!grade) return '';
  switch (grade) {
    case 'G1': return 'grade-badge g1';
    case 'G2': return 'grade-badge g2';
    case 'G3': return 'grade-badge g3';
    case 'L': return 'grade-badge listed';
    case 'OP': return 'grade-badge open';
    default: return '';
  }
}

// グレードバッジの表示テキストを取得
function getGradeBadgeText(grade: RaceGrade | undefined): string {
  if (!grade) return '';
  switch (grade) {
    case 'G1': return 'GⅠ';
    case 'G2': return 'GⅡ';
    case 'G3': return 'GⅢ';
    case 'L': return 'L';
    case 'OP': return 'OP';
    default: return '';
  }
}

// 日付を表示用にフォーマット
function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr);
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const dow = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()];
  return `${m}/${day}(${dow})`;
}

// 今日の日付を YYYY-MM-DD 形式で取得
function getTodayDateStr(): string {
  const today = new Date();
  const year = today.getFullYear();
  const m = String(today.getMonth() + 1).padStart(2, '0');
  const d = String(today.getDate()).padStart(2, '0');
  return `${year}-${m}-${d}`;
}

// 検索範囲を計算（前後2週間）
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

// 表示する日付を選択（金〜日: 次の週末、月〜木: 前の週末）
function selectDisplayDates(dates: string[]): string[] {
  if (dates.length === 0) return [];

  const today = new Date();
  const todayStr = getTodayDateStr();
  const dayOfWeek = today.getDay(); // 0=日, 1=月, ..., 6=土

  // 日付を Date オブジェクトに変換してソート
  const sortedDates = [...dates].sort();

  // 今日の開催があれば、その週末を表示
  if (sortedDates.includes(todayStr)) {
    // 今日を含む週末を取得
    const todayDate = new Date(todayStr);
    const weekend = sortedDates.filter((d: string) => {
      const diff = Math.abs(new Date(d).getTime() - todayDate.getTime());
      return diff <= 2 * 24 * 60 * 60 * 1000; // 2日以内
    });
    if (weekend.length > 0) {
      // today を必ず含める形で 2 日分を選択する
      if (weekend.length <= 2) {
        return weekend;
      }

      const todayIndex = weekend.indexOf(todayStr);
      // 理論上は必ず含まれるが、安全のためフォールバックを用意
      if (todayIndex === -1) {
        return weekend.slice(0, 2);
      }

      // today 以外の中から、today に最も近い 1 日を選択
      const nearest = weekend
        .filter((d: string) => d !== todayStr)
        .map((d: string) => ({
          date: d,
          diff: Math.abs(new Date(d).getTime() - todayDate.getTime()),
        }))
        .sort((a, b) => a.diff - b.diff)[0]?.date;

      if (!nearest) {
        return [todayStr];
      }

      // 返却時は日付昇順に並べる
      return [todayStr, nearest].sort();
    }
  }

  // 金〜日: 次の週末（今日以降の直近2日）
  if (dayOfWeek >= 5 || dayOfWeek === 0) {
    const futureDates = sortedDates.filter(d => d >= todayStr);
    if (futureDates.length > 0) {
      return futureDates.slice(0, 2);
    }
  }

  // 月〜木: 前の週末（今日以前の直近2日）
  const pastDates = sortedDates.filter(d => d <= todayStr).reverse();
  if (pastDates.length > 0) {
    return pastDates.slice(0, 2).reverse();
  }

  // フォールバック: 最も近い日付
  return sortedDates.slice(0, 2);
}

export function RacesPage() {
  const navigate = useNavigate();
  const [dateButtons, setDateButtons] = useState<string[]>([]);
  const [selectedDateIdx, setSelectedDateIdx] = useState(0);
  const [selectedVenue, setSelectedVenue] = useState<string | null>(null);
  const [races, setRaces] = useState<Race[]>([]);
  const [venues, setVenues] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [datesLoading, setDatesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 初回会場選択のためのref（無限ループ防止）
  const isInitialVenueSet = useRef(false);
  const isInitialDateSet = useRef(false);

  // 開催日一覧を取得
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

        // 今日の日付がある場合は選択
        if (!isInitialDateSet.current && displayDates.length > 0) {
          const todayStr = getTodayDateStr();
          const todayIdx = displayDates.indexOf(todayStr);
          if (todayIdx >= 0) {
            setSelectedDateIdx(todayIdx);
          }
          isInitialDateSet.current = true;
        }
      } else {
        // エラー時はフォールバックで空配列
        setDateButtons([]);
      }

      setDatesLoading(false);
    };

    fetchDates();

    return () => {
      isMounted = false;
    };
  }, []);

  // 開催日がない場合のローディング解除
  useEffect(() => {
    if (!datesLoading && dateButtons.length === 0) {
      // 非同期でローディング解除（同期的なsetState呼び出しを回避）
      const resetLoading = async () => {
        setLoading(false);
        setRaces([]);
        setVenues([]);
      };
      resetLoading();
    }
  }, [datesLoading, dateButtons.length]);

  // レース一覧を取得
  useEffect(() => {
    if (dateButtons.length === 0 || selectedDateIdx >= dateButtons.length) {
      return;
    }

    let isMounted = true;
    const selectedDate = dateButtons[selectedDateIdx];

    const fetchRaces = async () => {
      setLoading(true);
      setError(null);

      const response = await apiClient.getRaces(selectedDate);

      if (!isMounted) return;

      if (response.success && response.data) {
        setRaces(response.data.races);
        setVenues(response.data.venues);
        // 初回のみ最初の会場を選択
        if (!isInitialVenueSet.current && response.data.venues.length > 0) {
          setSelectedVenue(response.data.venues[0]);
          isInitialVenueSet.current = true;
        }
      } else {
        setError(response.error || 'レースの取得に失敗しました');
        setRaces([]);
      }

      setLoading(false);
    };

    fetchRaces();

    return () => {
      isMounted = false;
    };
  }, [selectedDateIdx, dateButtons]);

  // 選択された会場でフィルタリング
  const filteredRaces = selectedVenue
    ? races.filter((race) => race.venue === selectedVenue)
    : races;

  const selectedDateLabel = dateButtons[selectedDateIdx]
    ? formatDateLabel(dateButtons[selectedDateIdx])
    : '';

  return (
    <div className="fade-in">
      <div className="race-date-selector">
        {datesLoading ? (
          <span className="loading-text">日程を読み込み中...</span>
        ) : dateButtons.length === 0 ? (
          <span className="no-dates-text">開催日がありません</span>
        ) : (
          dateButtons.map((dateStr, index) => (
            <button
              key={dateStr}
              className={`date-btn ${selectedDateIdx === index ? 'active' : ''}`}
              onClick={() => setSelectedDateIdx(index)}
            >
              {formatDateLabel(dateStr)}
            </button>
          ))
        )}
      </div>

      <div className="venue-tabs">
        {venues.map((venue) => (
          <button
            key={venue}
            className={`venue-tab ${selectedVenue === venue ? 'active' : ''}`}
            onClick={() => setSelectedVenue(venue)}
          >
            {getVenueName(venue)}
          </button>
        ))}
      </div>

      <p className="section-title">
        {selectedDateLabel ? `${selectedDateLabel}のレース` : 'レース'}
      </p>

      {loading && <div className="loading">読み込み中...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && !error && filteredRaces.length === 0 && (
        <div className="no-races">レースがありません</div>
      )}

      {filteredRaces.map((race) => {
        const gradeBadgeClass = getGradeBadgeClass(race.gradeClass);
        const gradeBadgeText = getGradeBadgeText(race.gradeClass);
        const showGradeBadge = gradeBadgeClass && gradeBadgeText;

        return (
          <div
            key={race.id}
            className="race-card-v2"
            onClick={() => navigate(`/races/${encodeURIComponent(race.id)}`)}
          >
            <div className="race-card-left">
              <div className="race-number-badge">{race.number}</div>
              <div className="race-start-time">{race.time}</div>
            </div>
            <div className="race-card-center">
              <div className="race-name-main">
                {showGradeBadge && (
                  <span className={gradeBadgeClass} style={{ marginRight: '6px' }}>
                    {gradeBadgeText}
                  </span>
                )}
                {race.name || `第${race.number}レース`}
              </div>
              <div className="race-conditions-row">
                {race.isObstacle && (
                  <span className="grade-badge obstacle">障害</span>
                )}
                {race.ageCondition && (
                  <span className="condition-chip">{race.ageCondition}</span>
                )}
                {race.sexCondition === '牝' && (
                  <span className="condition-chip female">牝馬限定</span>
                )}
                {race.weightType === 'ハンデ' && (
                  <span className="condition-chip handicap">ハンデ</span>
                )}
                {race.gradeClass && !showGradeBadge && (
                  <span className="condition-chip">{race.gradeClass}</span>
                )}
              </div>
            </div>
            <div className="race-card-right">
              {race.trackType && (
                <span className={`track-badge ${race.trackType === '芝' ? 'turf' : 'dirt'}`}>
                  {race.trackType}
                </span>
              )}
              {race.distance && (
                <span className="distance-text">{race.distance.toLocaleString()}m</span>
              )}
              {race.horseCount && (
                <span className="horse-count-text">{race.horseCount}頭</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
