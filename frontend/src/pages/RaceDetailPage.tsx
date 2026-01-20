import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { useCartStore } from '../stores/cartStore';
import type { RaceDetail, BetType } from '../types';
import { BetTypeLabels, BetTypeRequiredHorses } from '../types';
import { apiClient } from '../api/client';

const betTypes: BetType[] = ['win', 'place', 'quinella', 'exacta', 'trio', 'trifecta'];

export function RaceDetailPage() {
  const { raceId } = useParams<{ raceId: string }>();
  const navigate = useNavigate();
  const showToast = useAppStore((state) => state.showToast);
  const addItem = useCartStore((state) => state.addItem);
  const itemCount = useCartStore((state) => state.getItemCount());

  const [race, setRace] = useState<RaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedHorses, setSelectedHorses] = useState<number[]>([]);
  const [betType, setBetType] = useState<BetType>('quinella');
  const [betAmount, setBetAmount] = useState(1000);

  const fetchRaceDetail = useCallback(async () => {
    if (!raceId) return;

    setLoading(true);
    setError(null);

    const response = await apiClient.getRaceDetail(decodeURIComponent(raceId));

    if (response.success && response.data) {
      setRace(response.data);
    } else {
      setError(response.error || 'レース詳細の取得に失敗しました');
    }

    setLoading(false);
  }, [raceId]);

  useEffect(() => {
    fetchRaceDetail();
  }, [fetchRaceDetail]);

  const toggleHorse = (number: number) => {
    setSelectedHorses((prev) =>
      prev.includes(number) ? prev.filter((n) => n !== number) : [...prev, number]
    );
  };

  const clearSelection = () => setSelectedHorses([]);

  const requiredCount = BetTypeRequiredHorses[betType];
  const isValidSelection = selectedHorses.length === requiredCount;

  const getSelectionHint = () => {
    switch (requiredCount) {
      case 1: return '（1頭選択）';
      case 2: return '（2頭選択）';
      case 3: return '（3頭選択）';
      default: return '';
    }
  };

  const getSelectionError = () => {
    if (selectedHorses.length === 0) return '';
    if (selectedHorses.length < requiredCount) {
      return `あと${requiredCount - selectedHorses.length}頭選択してください`;
    }
    if (selectedHorses.length > requiredCount) {
      return `${selectedHorses.length - requiredCount}頭多く選択されています`;
    }
    return '';
  };

  const handleAddToCart = () => {
    if (!race || !isValidSelection) return;

    addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType,
      horseNumbers: [...selectedHorses].sort((a, b) => a - b),
      amount: betAmount,
    });

    setSelectedHorses([]);
    setBetAmount(1000);
    showToast('カートに追加しました');
  };

  if (loading) return <div className="loading">読み込み中...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!race) return <div className="no-races">レースが見つかりません</div>;

  return (
    <div className="fade-in">
      <button className="back-btn" onClick={() => navigate('/')}>
        ← レース一覧に戻る
      </button>

      <div className="race-detail-header">
        <span className="race-number">{race.venue} {race.number}</span>
        <div className="race-name">{race.name}</div>
        <div className="race-conditions">
          <span className="condition-tag">{race.course}</span>
          <span className="condition-tag">馬場: {race.condition}</span>
          <span className="condition-tag">{race.time} 発走</span>
        </div>
      </div>

      <div className="horse-list">
        <div className="horse-list-header">
          <span></span>
          <span>馬番</span>
          <span>馬名</span>
          <span>オッズ</span>
        </div>
        {race.horses.map((horse) => (
          <div
            key={horse.number}
            className={`horse-item ${selectedHorses.includes(horse.number) ? 'selected' : ''}`}
            onClick={() => toggleHorse(horse.number)}
          >
            <div className="horse-checkbox">
              <input
                type="checkbox"
                checked={selectedHorses.includes(horse.number)}
                onChange={() => {}}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
            <div className="horse-number" style={{ background: horse.color }}>
              {horse.number}
            </div>
            <div className="horse-info">
              <div className="horse-name">{horse.name}</div>
              <div className="horse-jockey">{horse.jockey}</div>
            </div>
            <div className="horse-odds">{horse.odds}</div>
          </div>
        ))}
      </div>

      <div className="bet-section">
        <h3>🎫 買い目を入力</h3>

        <div className="bet-type-selector">
          {betTypes.map((type) => (
            <button
              key={type}
              className={`bet-type-btn ${betType === type ? 'active' : ''}`}
              onClick={() => setBetType(type)}
            >
              {BetTypeLabels[type]}
            </button>
          ))}
        </div>

        <div className="bet-input-group">
          <label>選択した馬番 {getSelectionHint()}</label>
          <div className={`selected-horses-display ${selectedHorses.length > 0 ? 'has-selection' : ''}`}>
            {selectedHorses.length > 0 ? (
              <>
                <span className="selected-numbers">
                  {[...selectedHorses].sort((a, b) => a - b).join(' - ')}
                </span>
                <button className="clear-selection-btn" onClick={clearSelection}>
                  クリア
                </button>
              </>
            ) : (
              <span className="no-selection">上のリストから馬を選択してください</span>
            )}
          </div>
          {getSelectionError() && (
            <div className="selection-error">{getSelectionError()}</div>
          )}
        </div>

        <div className="bet-input-group">
          <label>金額</label>
          <div className="amount-input-wrapper">
            <span className="currency-symbol">¥</span>
            <input
              type="number"
              className="amount-input"
              value={betAmount}
              onChange={(e) => setBetAmount(parseInt(e.target.value) || 0)}
            />
          </div>
          <div className="amount-presets">
            {[100, 500, 1000, 5000].map((amount) => (
              <button
                key={amount}
                className="preset-btn"
                onClick={() => setBetAmount(amount)}
              >
                ¥{amount.toLocaleString()}
              </button>
            ))}
          </div>
        </div>

        <button
          className="ai-consult-btn"
          onClick={handleAddToCart}
          disabled={!isValidSelection}
        >
          🛒 カートに追加
        </button>

        {itemCount > 0 && (
          <button
            className="btn-secondary"
            style={{ marginTop: 12, width: '100%' }}
            onClick={() => navigate('/cart')}
          >
            カートを確認する（{itemCount}件）
          </button>
        )}
      </div>
    </div>
  );
}
