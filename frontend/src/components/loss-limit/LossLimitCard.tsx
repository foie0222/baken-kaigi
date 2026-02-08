import { useState, type FormEvent } from 'react';
import { useLossLimitStore } from '../../stores/lossLimitStore';
import { ConfirmModal } from '../common/ConfirmModal';

const MIN_AMOUNT = 1000;
const MAX_AMOUNT = 1000000;
const STEP = 1000;

export function LossLimitCard() {
  const {
    lossLimit,
    totalLossThisMonth,
    remainingLossLimit,
    pendingChange,
    isLoading,
    error,
    requestChange,
    clearError,
  } = useLossLimitStore();

  const [showChangeForm, setShowChangeForm] = useState(false);
  const [newAmount, setNewAmount] = useState('');
  const [validationError, setValidationError] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);

  if (lossLimit === null) return null;

  const usageRate = lossLimit > 0 ? (totalLossThisMonth / lossLimit) * 100 : 0;
  const formatAmount = (value: number) => value.toLocaleString();

  const getBarColor = () => {
    if (usageRate >= 100) return '#dc2626';
    if (usageRate >= 80) return '#f59e0b';
    return '#1a5f2a';
  };

  const validate = (): boolean => {
    const num = parseInt(newAmount, 10);
    if (!newAmount || isNaN(num)) {
      setValidationError('金額を入力してください');
      return false;
    }
    if (num < MIN_AMOUNT) {
      setValidationError(`${formatAmount(MIN_AMOUNT)}円以上を指定してください`);
      return false;
    }
    if (num > MAX_AMOUNT) {
      setValidationError(`${formatAmount(MAX_AMOUNT)}円以下を指定してください`);
      return false;
    }
    if (num % STEP !== 0) {
      setValidationError(`${formatAmount(STEP)}円単位で入力してください`);
      return false;
    }
    if (num === lossLimit) {
      setValidationError('現在の限度額と同じです');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleChangeSubmit = (e: FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validate()) return;
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    setShowConfirm(false);
    const result = await requestChange(parseInt(newAmount, 10));
    if (result) {
      setShowChangeForm(false);
      setNewAmount('');
    }
  };

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  };

  return (
    <div style={{
      background: 'white',
      borderRadius: 12,
      padding: 20,
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
      }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
          負け額限度額
        </h3>
        {!showChangeForm && !pendingChange && (
          <button
            onClick={() => setShowChangeForm(true)}
            style={{
              padding: '6px 12px',
              background: '#f3f4f6',
              color: '#374151',
              border: 'none',
              borderRadius: 6,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            変更
          </button>
        )}
      </div>

      {/* 限度額表示 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 4,
        }}>
          <span style={{ fontSize: 13, color: '#666' }}>月間限度額</span>
          <span style={{ fontSize: 20, fontWeight: 700 }}>
            {formatAmount(lossLimit)}円
          </span>
        </div>

        {/* プログレスバー */}
        <div style={{
          width: '100%',
          height: 8,
          background: '#e5e7eb',
          borderRadius: 4,
          marginBottom: 8,
          overflow: 'hidden',
        }}>
          <div style={{
            width: `${Math.min(usageRate, 100)}%`,
            height: '100%',
            background: getBarColor(),
            borderRadius: 4,
            transition: 'width 0.3s ease',
          }} />
        </div>

        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 13,
        }}>
          <span style={{ color: '#666' }}>
            今月の損失: <strong style={{ color: usageRate >= 80 ? getBarColor() : '#374151' }}>{formatAmount(totalLossThisMonth)}円</strong>
          </span>
          <span style={{ color: '#666' }}>
            残り: <strong>{formatAmount(Math.max(remainingLossLimit, 0))}円</strong>
          </span>
        </div>
      </div>

      {/* 保留中の変更 */}
      {pendingChange && (
        <div style={{
          background: '#fffbeb',
          border: '1px solid #f59e0b',
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
          fontSize: 13,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              background: '#f59e0b',
              color: 'white',
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 600,
            }}>
              PENDING
            </span>
            <span style={{ fontWeight: 600 }}>
              限度額{pendingChange.changeType === 'increase' ? '引き上げ' : '引き下げ'}リクエスト
            </span>
          </div>
          <p style={{ color: '#666', margin: 0 }}>
            {formatAmount(pendingChange.currentLimit)}円 → {formatAmount(pendingChange.requestedLimit)}円
          </p>
          <p style={{ color: '#666', margin: '4px 0 0' }}>
            適用予定: {formatDate(pendingChange.effectiveAt)}
          </p>
        </div>
      )}

      {/* エラー表示 */}
      {error && (
        <div style={{
          background: '#fef2f2',
          color: '#c62828',
          padding: 12,
          borderRadius: 8,
          marginBottom: 16,
          fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {/* 変更フォーム */}
      {showChangeForm && (
        <div style={{
          background: '#f9fafb',
          borderRadius: 8,
          padding: 16,
        }}>
          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            限度額の変更
          </h4>

          {validationError && (
            <div style={{
              background: '#fef2f2',
              color: '#c62828',
              padding: 8,
              borderRadius: 6,
              marginBottom: 12,
              fontSize: 13,
            }}>
              {validationError}
            </div>
          )}

          <form onSubmit={handleChangeSubmit}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, marginBottom: 4, color: '#666' }}>
                新しい限度額
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="number"
                  value={newAmount}
                  onChange={(e) => {
                    setNewAmount(e.target.value);
                    setValidationError('');
                  }}
                  placeholder={`現在: ${formatAmount(lossLimit)}円`}
                  min={MIN_AMOUNT}
                  max={MAX_AMOUNT}
                  step={STEP}
                  inputMode="numeric"
                  style={{
                    width: '100%',
                    padding: '10px 36px 10px 10px',
                    border: '1px solid #ddd',
                    borderRadius: 6,
                    fontSize: 16,
                    boxSizing: 'border-box',
                  }}
                />
                <span style={{
                  position: 'absolute',
                  right: 10,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: '#666',
                  fontSize: 14,
                }}>
                  円
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                onClick={() => {
                  setShowChangeForm(false);
                  setNewAmount('');
                  setValidationError('');
                }}
                style={{
                  flex: 1,
                  padding: 10,
                  background: '#e5e7eb',
                  color: '#374151',
                  border: 'none',
                  borderRadius: 6,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={isLoading || !newAmount}
                style={{
                  flex: 1,
                  padding: 10,
                  background: '#1a5f2a',
                  color: 'white',
                  border: 'none',
                  borderRadius: 6,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                  opacity: isLoading || !newAmount ? 0.5 : 1,
                }}
              >
                {isLoading ? '送信中...' : '変更を申請'}
              </button>
            </div>
          </form>

          <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 8 }}>
            引き下げは即時反映、引き上げには待機期間があります。
          </p>
        </div>
      )}

      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleConfirm}
        title="限度額の変更確認"
        confirmText="変更を申請"
      >
        <p>
          負け額限度額を <strong>{formatAmount(lossLimit)}円</strong> から{' '}
          <strong>{formatAmount(parseInt(newAmount, 10) || 0)}円</strong> に変更しますか？
        </p>
        {parseInt(newAmount, 10) > lossLimit && (
          <p style={{ fontSize: 13, color: '#f59e0b', marginTop: 8 }}>
            引き上げの場合、一定の待機期間後に適用されます。
          </p>
        )}
        {parseInt(newAmount, 10) < lossLimit && (
          <p style={{ fontSize: 13, color: '#1a5f2a', marginTop: 8 }}>
            引き下げは即時反映されます。
          </p>
        )}
      </ConfirmModal>
    </div>
  );
}
