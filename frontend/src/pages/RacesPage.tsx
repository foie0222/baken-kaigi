import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Race } from '../types';
import { apiClient } from '../api/client';

// 日付ボタン生成
function generateDateButtons(): { label: string; date: string }[] {
  const today = new Date();
  const result = [];

  for (let i = 0; i < 4; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);

    const month = d.getMonth() + 1;
    const day = d.getDate();
    const dayOfWeek = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()];

    let label: string;
    if (i === 0) {
      label = `今日 ${month}/${day}`;
    } else if (i === 1) {
      label = `明日 ${month}/${day}`;
    } else {
      label = `${month}/${day} (${dayOfWeek})`;
    }

    const dateStr = d.toISOString().split('T')[0];
    result.push({ label, date: dateStr });
  }

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

  const fetchRaces = useCallback(async () => {
    setLoading(true);
    setError(null);

    const selectedDate = dateButtons[selectedDateIdx].date;
    const response = await apiClient.getRaces(selectedDate);

    if (response.success && response.data) {
      setRaces(response.data.races);
      setVenues(response.data.venues);
      // 初回は最初の会場を選択
      if (!selectedVenue && response.data.venues.length > 0) {
        setSelectedVenue(response.data.venues[0]);
      }
    } else {
      setError(response.error || 'レースの取得に失敗しました');
      setRaces([]);
    }

    setLoading(false);
  }, [selectedDateIdx, selectedVenue]);

  useEffect(() => {
    fetchRaces();
  }, [fetchRaces]);

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
            {venue}
          </button>
        ))}
      </div>

      <p className="section-title">
        {selectedDateIdx === 0 ? '本日' : dateButtons[selectedDateIdx].label}のレース
      </p>

      {loading && <div className="loading">読み込み中...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && !error && filteredRaces.length === 0 && (
        <div className="no-races">レースがありません</div>
      )}

      {filteredRaces.map((race) => (
        <div
          key={race.id}
          className="race-card"
          onClick={() => navigate(`/races/${encodeURIComponent(race.id)}`)}
        >
          <div className="race-header">
            <span className="race-number">{race.number}</span>
            <span className="race-time">{race.time} 発走</span>
          </div>
          <div className="race-name">{race.name}</div>
          <div className="race-info">
            {race.course && <span>{race.course}</span>}
            <span>馬場: {race.condition}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
