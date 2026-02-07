import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIpatSettingsStore } from '../stores/ipatSettingsStore';
import { ConfirmModal } from '../components/common/ConfirmModal';

export function IpatSettingsPage() {
  const navigate = useNavigate();
  const { status, isLoading, error, checkStatus, saveCredentials, deleteCredentials, clearError } = useIpatSettingsStore();

  const [cardNumber, setCardNumber] = useState('');
  const [birthday, setBirthday] = useState('');
  const [pin, setPin] = useState('');
  const [dummyPin, setDummyPin] = useState('');
  const [validationError, setValidationError] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const validate = (): boolean => {
    if (cardNumber.length !== 12 || !/^\d{12}$/.test(cardNumber)) {
      setValidationError('カード番号は12桁の数字で入力してください');
      return false;
    }
    if (birthday.length !== 8 || !/^\d{8}$/.test(birthday)) {
      setValidationError('生年月日はYYYYMMDD形式（8桁の数字）で入力してください');
      return false;
    }
    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
      setValidationError('暗証番号は4桁の数字で入力してください');
      return false;
    }
    if (dummyPin.length !== 4 || !/^\d{4}$/.test(dummyPin)) {
      setValidationError('P-ARS暗証番号は4桁の数字で入力してください');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validate()) return;
    await saveCredentials({ cardNumber, birthday, pin, dummyPin });
    if (!useIpatSettingsStore.getState().error) {
      setSaved(true);
      setCardNumber('');
      setBirthday('');
      setPin('');
      setDummyPin('');
      setTimeout(() => setSaved(false), 3000);
    }
  };

  const handleDelete = async () => {
    setShowDeleteModal(false);
    await deleteCredentials();
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <button className="back-btn" onClick={() => navigate('/settings')}>
        ← 設定に戻る
      </button>

      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>IPAT設定</h2>

      {saved && (
        <div style={{ background: '#e8f5e9', color: '#2e7d32', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          IPAT認証情報を保存しました
        </div>
      )}

      {(error || validationError) && (
        <div style={{ background: '#fce4ec', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {validationError || error}
        </div>
      )}

      {status?.configured ? (
        <div style={{ background: 'white', borderRadius: 12, padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>&#x2705;</div>
          <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>IPAT認証情報は設定済みです</p>
          <p style={{ fontSize: 13, color: '#666', marginBottom: 24 }}>
            認証情報を変更する場合は、一度削除してから再設定してください
          </p>
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            disabled={isLoading}
            style={{
              padding: '12px 24px',
              background: '#c62828',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              opacity: isLoading ? 0.5 : 1,
            }}
          >
            認証情報を削除
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              INET-ID（加入者番号）
            </label>
            <input
              type="text"
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              placeholder="12桁の数字"
              maxLength={12}
              inputMode="numeric"
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              生年月日
            </label>
            <input
              type="text"
              value={birthday}
              onChange={(e) => setBirthday(e.target.value)}
              placeholder="YYYYMMDD"
              maxLength={8}
              inputMode="numeric"
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              暗証番号
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="4桁の数字"
              maxLength={4}
              inputMode="numeric"
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              P-ARS暗証番号
            </label>
            <input
              type="password"
              value={dummyPin}
              onChange={(e) => setDummyPin(e.target.value)}
              placeholder="4桁の数字"
              maxLength={4}
              inputMode="numeric"
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              padding: 14,
              background: '#1a73e8',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              fontSize: 16,
              fontWeight: 600,
              cursor: 'pointer',
              opacity: isLoading ? 0.5 : 1,
            }}
          >
            {isLoading ? '保存中...' : '保存'}
          </button>
        </form>
      )}

      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        title="IPAT認証情報の削除"
        confirmText="削除する"
        confirmVariant="danger"
      >
        <p>IPAT認証情報を削除しますか？</p>
        <p style={{ fontSize: 13, color: '#666', marginTop: 8 }}>
          削除後はIPATでの購入ができなくなります。再度設定が必要です。
        </p>
      </ConfirmModal>
    </div>
  );
}
