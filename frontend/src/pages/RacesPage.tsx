import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Race } from '../types';
import { getVenueName } from '../types';
import { apiClient } from '../api/client';
import { USE_MOCK, getMockRaces, getMockVenues } from '../../mock/races';

// 日付ボタン生成（前週土日 + 次週土日）
function generateDateButtons(): { label: string; date: string }[] {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0=日, 1=月, ..., 6=土
  const result: { label: string; date: string }[] = [];

  // 前週の土曜日を計算
  const lastSat = new Date(today);
  const daysToLastSat = dayOfWeek === 0 ? 8 : dayOfWeek + 1;
  lastSat.setDate(today.getDate() - daysToLastSat);

  // 前週の日曜日
  const lastSun = new Date(lastSat);
  lastSun.setDate(lastSat.getDate() + 1);

  // 次週の土曜日を計算
  const nextSat = new Date(today);
  const daysToNextSat = dayOfWeek === 6 ? 7 : 6 - dayOfWeek;
  nextSat.setDate(today.getDate() + daysToNextSat);

  // 次週の日曜日
  const nextSun = new Date(nextSat);
  nextSun.setDate(nextSat.getDate() + 1);

  const formatDate = (d: Date) => {
    const year = d.getFullYear();
    const m = d.getMonth() + 1;
    const day = d.getDate();
    const dow = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()];
    // ローカル日付を使用（toISOString()はUTCを返すため使わない）
    const dateStr = `${year}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return {
      label: `${m}/${day}(${dow})`,
      date: dateStr,
    };
  };

  result.push(formatDate(lastSat));
  result.push(formatDate(lastSun));
  result.push(formatDate(nextSat));
  result.push(formatDate(nextSun));

  return result;
}

const dateButtons = generateDateButtons();

export function RacesPage() {
  const navigate = useNavigate();
  const [selectedDateIdx, setSelectedDateIdx] = useState(0);
  const [selectedVenue, setSelectedVenue] = useState<string | null>(null);
  const [races, setRaces] = useState<Race[]>([]);
  const [venues, setVenues] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 初回会場選択のためのref（無限ループ防止）
  const isInitialVenueSet = useRef(false);

  useEffect(() => {
    let isMounted = true;

    const fetchRaces = async () => {
      setLoading(true);
      setError(null);

      const selectedDate = dateButtons[selectedDateIdx].date;

      // モックモードの場合
      if (USE_MOCK) {
        const mockRaceList = getMockRaces(undefined, undefined);
        const mockVenueList = getMockVenues();
        if (!isMounted) return;
        setRaces(mockRaceList);
        setVenues(mockVenueList);
        if (!isInitialVenueSet.current && mockVenueList.length > 0) {
          setSelectedVenue(mockVenueList[0]);
          isInitialVenueSet.current = true;
        }
        setLoading(false);
        return;
      }

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
  }, [selectedDateIdx]);

  // 選択された会場でフィルタリング
  const filteredRaces = selectedVenue
    ? races.filter((race) => race.venue === selectedVenue)
    : races;

  return (
    <div className="fade-in">
      <div className="race-date-selector">
        {dateButtons.map((btn, index) => (
          <button
            key={btn.date}
            className={`date-btn ${selectedDateIdx === index ? 'active' : ''}`}
            onClick={() => setSelectedDateIdx(index)}
          >
            {btn.label}
          </button>
        ))}
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
        {dateButtons[selectedDateIdx].label}のレース
      </p>

      {loading && <div className="loading">読み込み中...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && !error && filteredRaces.length === 0 && (
        <div className="no-races">レースがありません</div>
      )}

      {filteredRaces.map((race) => (
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
              {race.name || `第${race.number}レース`}
            </div>
            {race.course && (
              <div className="race-name-sub">{race.course}</div>
            )}
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
      ))}
    </div>
  );
}
