import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Race, RaceGrade } from '../types';
import { getVenueName } from '../types';

interface NextRacesPanelProps {
  races: Race[];
  isToday: boolean;
}

// カウントダウン表示用のフォーマット
function formatCountdown(diffMs: number): string {
  if (diffMs <= 0) return '発走';

  const totalSeconds = Math.floor(diffMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

// 残り時間が5分以内かどうか
function isUrgent(diffMs: number): boolean {
  return diffMs > 0 && diffMs <= 5 * 60 * 1000;
}

// グレードバッジのCSSクラスを取得
function getGradeBadgeClass(grade: RaceGrade | undefined): string {
  if (!grade) return '';
  switch (grade) {
    case 'G1': return 'next-race-grade-badge g1';
    case 'G2': return 'next-race-grade-badge g2';
    case 'G3': return 'next-race-grade-badge g3';
    default: return 'next-race-grade-badge';
  }
}

// グレードバッジの表示テキスト
function getGradeBadgeText(grade: RaceGrade | undefined): string {
  if (!grade) return '';
  switch (grade) {
    case 'G1': return 'GI';
    case 'G2': return 'GII';
    case 'G3': return 'GIII';
    case 'L': return 'L';
    case 'OP': return 'OP';
    default: return '';
  }
}

// 投票期限を日本時間でフォーマット
function formatBettingDeadline(bettingDeadline: string | undefined): string {
  if (!bettingDeadline) return '';
  const deadline = new Date(bettingDeadline);
  return deadline.toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Tokyo',
    hour12: false,
  });
}

export function NextRacesPanel({ races, isToday }: NextRacesPanelProps) {
  const navigate = useNavigate();
  const [now, setNow] = useState(() => new Date());

  // 1秒ごとに現在時刻を更新
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // 次のレース2件を抽出
  const nextRaces = useMemo(() => {
    if (!isToday) return [];

    const nowTime = now.getTime();

    // startTimeがあり、まだ発走していないレースを抽出
    const upcomingRaces = races
      .filter((race) => {
        if (!race.startTime) return false;
        const startTime = new Date(race.startTime).getTime();
        return startTime > nowTime;
      })
      .sort((a, b) => {
        const aTime = new Date(a.startTime!).getTime();
        const bTime = new Date(b.startTime!).getTime();
        return aTime - bTime;
      });

    return upcomingRaces.slice(0, 2);
  }, [races, isToday, now]);

  // 今日のレースがない、または全て終了している場合は非表示
  if (!isToday || nextRaces.length === 0) {
    return null;
  }

  return (
    <div className="next-races-panel fade-in">
      <div className="next-races-panel-header">
        <div className="next-races-panel-title">
          <span className="next-races-panel-title-icon">🏇</span>
          次のレース
        </div>
      </div>

      <div className="next-races-list">
        {nextRaces.map((race) => {
          const startTime = new Date(race.startTime!).getTime();
          const diffMs = startTime - now.getTime();
          const countdown = formatCountdown(diffMs);
          const urgent = isUrgent(diffMs);

          const gradeBadgeClass = getGradeBadgeClass(race.gradeClass);
          const gradeBadgeText = getGradeBadgeText(race.gradeClass);
          const showGradeBadge = ['G1', 'G2', 'G3', 'L', 'OP'].includes(race.gradeClass || '');

          return (
            <div
              key={race.id}
              className="next-race-card"
              onClick={() => navigate(`/races/${encodeURIComponent(race.id)}`)}
            >
              <div className="next-race-card-top">
                <div className="next-race-venue-info">
                  <span className="next-race-venue-badge">
                    {getVenueName(race.venue)}
                  </span>
                  <span className="next-race-number">{race.number}</span>
                </div>
                <div className="next-race-countdown">
                  <span className="next-race-countdown-label">残り</span>
                  <span className={`next-race-countdown-time ${urgent ? 'urgent' : ''}`}>
                    {countdown}
                  </span>
                </div>
              </div>

              <div className="next-race-name">
                {showGradeBadge && (
                  <span className={gradeBadgeClass} style={{ marginRight: '6px' }}>
                    {gradeBadgeText}
                  </span>
                )}
                {race.name || `第${race.number}`}
              </div>

              <div className="next-race-details">
                {race.trackType && (
                  <span className="next-race-detail-item">
                    {race.trackType}
                  </span>
                )}
                {race.distance && (
                  <span className="next-race-detail-item">
                    {race.distance.toLocaleString()}m
                  </span>
                )}
                {race.horseCount && (
                  <span className="next-race-detail-item">
                    {race.horseCount}頭
                  </span>
                )}
              </div>

              <div className="next-race-time-info">
                <div className="next-race-time-item">
                  <span className="next-race-time-label">発走</span>
                  <span className="next-race-time-value">{race.time}</span>
                </div>
                {race.bettingDeadline && (
                  <div className="next-race-time-item">
                    <span className="next-race-time-label">締切</span>
                    <span className="next-race-time-value">
                      {formatBettingDeadline(race.bettingDeadline)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
