import { useState, type FormEvent } from 'react';
import { useLossLimitStore } from '../../stores/lossLimitStore';
import { ConfirmModal } from '../common/ConfirmModal';

const MIN_AMOUNT = 1000;
const MAX_AMOUNT = 1000000;
const STEP = 1000;

const PRESET_AMOUNTS = [10000, 30000, 50000, 100000];

export function LossLimitSetupForm() {
  const { isLoading, error, setLossLimit, clearError } = useLossLimitStore();
  const [amount, setAmount] = useState('');
  const [validationError, setValidationError] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);

  const formatAmount = (value: number) => value.toLocaleString();

  const validate = (): boolean => {
    const num = parseInt(amount, 10);
    if (!amount || isNaN(num)) {
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
    setValidationError('');
    return true;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validate()) return;
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    setShowConfirm(false);
    await setLossLimit(parseInt(amount, 10));
  };

  const handlePreset = (value: number) => {
    setAmount(String(value));
    setValidationError('');
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <div style={{
        background: 'white',
        borderRadius: 12,
        padding: 24,
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: 8, fontSize: 18 }}>
          負け額限度額の設定
        </h2>
        <p style={{ textAlign: 'center', fontSize: 13, color: '#666', marginBottom: 24 }}>
          1か月あたりの負け額（損失）の上限を設定します。
          <br />
          限度額に達すると馬券の購入ができなくなります。
        </p>

        {(error || validationError) && (
          <div
            id="loss-limit-error"
            role="alert"
            style={{
              background: '#fef2f2',
              color: '#c62828',
              padding: 12,
              borderRadius: 8,
              marginBottom: 16,
              fontSize: 14,
            }}
          >
            {validationError || error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="loss-limit-amount" style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              月間限度額
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="loss-limit-amount"
                type="number"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value);
                  setValidationError('');
                }}
                placeholder="例: 50000"
                min={MIN_AMOUNT}
                max={MAX_AMOUNT}
                step={STEP}
                inputMode="numeric"
                aria-describedby={(error || validationError) ? 'loss-limit-error' : undefined}
                style={{
                  width: '100%',
                  padding: '12px 36px 12px 12px',
                  border: '1px solid #ddd',
                  borderRadius: 8,
                  fontSize: 16,
                  boxSizing: 'border-box',
                }}
              />
              <span style={{
                position: 'absolute',
                right: 12,
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#666',
                fontSize: 14,
              }}>
                円
              </span>
            </div>
          </div>

          <div style={{
            display: 'flex',
            gap: 8,
            marginBottom: 24,
            flexWrap: 'wrap',
          }}>
            {PRESET_AMOUNTS.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => handlePreset(preset)}
                style={{
                  flex: 1,
                  minWidth: 70,
                  padding: '8px 4px',
                  background: amount === String(preset) ? '#1a5f2a' : '#f3f4f6',
                  color: amount === String(preset) ? 'white' : '#374151',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {formatAmount(preset)}円
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={isLoading || !amount}
            style={{
              width: '100%',
              padding: 14,
              background: '#1a5f2a',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              fontSize: 16,
              fontWeight: 600,
              cursor: 'pointer',
              opacity: isLoading || !amount ? 0.5 : 1,
            }}
          >
            {isLoading ? '設定中...' : '限度額を設定する'}
          </button>
        </form>
      </div>

      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleConfirm}
        title="限度額の設定確認"
        confirmText="設定する"
      >
        <p>月間の負け額限度額を <strong>{formatAmount(parseInt(amount, 10) || 0)}円</strong> に設定しますか？</p>
        <p style={{ fontSize: 13, color: '#666', marginTop: 8 }}>
          設定後、限度額の引き下げは即時反映されますが、引き上げには一定の待機期間があります。
        </p>
      </ConfirmModal>
    </div>
  );
}
