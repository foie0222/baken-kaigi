import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Race } from '../types';

// モックデータ（後でAPI連携）
const mockRaces: Race[] = [
  { id: '1', number: '11R', name: '天皇賞（春）', time: '15:40', course: '芝3200m', condition: '良', venue: '東京', date: '2024-01-18' },
  { id: '2', number: '10R', name: '駒草特別', time: '15:00', course: '芝1800m', condition: '良', venue: '東京', date: '2024-01-18' },
  { id: '3', number: '9R', name: '青嵐賞', time: '14:25', course: 'ダ1400m', condition: '良', venue: '東京', date: '2024-01-18' },
  { id: '4', number: '12R', name: '立夏特別', time: '16:20', course: '芝1400m', condition: '良', venue: '東京', date: '2024-01-18' },
];

const dates = ['今日 1/18', '明日 1/19', '1/25 (土)', '1/26 (日)'];
const venues = ['東京', '中山', '京都'];

export function RacesPage() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState(0);
  const [selectedVenue, setSelectedVenue] = useState('東京');
  const [races, setRaces] = useState<Race[]>(mockRaces);

  useEffect(() => {
    // TODO: API連携時にsetRacesを使用
    // 現在はモックデータを使用
    setRaces(mockRaces);
  }, [selectedDate, selectedVenue]);

  return (
    <div className="fade-in">
      <div className="race-date-selector">
        {dates.map((date, index) => (
          <button
            key={date}
            className={`date-btn ${selectedDate === index ? 'active' : ''}`}
            onClick={() => setSelectedDate(index)}
          >
            {date}
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

      <p className="section-title">本日のレース</p>

      {races.map((race) => (
        <div
          key={race.id}
          className="race-card"
          onClick={() => navigate(`/races/${race.id}`)}
        >
          <div className="race-header">
            <span className="race-number">{race.number}</span>
            <span className="race-time">{race.time} 発走</span>
          </div>
          <div className="race-name">{race.name}</div>
          <div className="race-info">
            <span>{race.course}</span>
            <span>馬場: {race.condition}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
