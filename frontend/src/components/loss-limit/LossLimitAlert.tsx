import { useAuthStore } from '../../stores/authStore';
import { useLossLimitStore } from '../../stores/lossLimitStore';

export function LossLimitAlert() {
  const { isAuthenticated } = useAuthStore();
  const { lossLimit, totalLossThisMonth, remainingLossLimit } = useLossLimitStore();

  if (!isAuthenticated || lossLimit === null || lossLimit <= 0) {
    return null;
  }

  const usageRate = (totalLossThisMonth / lossLimit) * 100;

  if (usageRate < 80) {
    return null;
  }

  const isCritical = remainingLossLimit <= 0;

  return (
    <div role="alert" aria-live="assertive" style={{
      background: isCritical
        ? 'linear-gradient(90deg, #dc2626, #b91c1c)'
        : 'linear-gradient(90deg, #f59e0b, #d97706)',
      color: 'white',
      padding: '10px 16px',
      fontSize: 13,
      fontWeight: 600,
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    }}>
      <span aria-hidden="true">{isCritical ? '!!' : '!'}</span>
      {isCritical ? (
        <span>負け額限度額に到達しました。今月は馬券を購入できません。</span>
      ) : (
        <span>
          負け額限度額の{Math.round(usageRate)}%に到達しました（残り: {remainingLossLimit.toLocaleString()}円）
        </span>
      )}
    </div>
  );
}
