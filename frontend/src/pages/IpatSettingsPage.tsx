import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIpatSettingsStore } from '../stores/ipatSettingsStore';
import { ConfirmModal } from '../components/common/ConfirmModal';

export function IpatSettingsPage() {
  const navigate = useNavigate();
  const { status, isLoading, error, checkStatus, saveCredentials, deleteCredentials, clearError } = useIpatSettingsStore();

  const [inetId, setInetId] = useState('');
  const [subscriberNumber, setSubscriberNumber] = useState('');
  const [pin, setPin] = useState('');
  const [parsNumber, setParsNumber] = useState('');
  const [validationError, setValidationError] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const validate = (): boolean => {
    if (inetId.length !== 8 || !/^[a-zA-Z0-9]{8}$/.test(inetId)) {
      setValidationError('INET-IDは8桁の英数字で入力してください');
      return false;
    }
    if (subscriberNumber.length !== 8 || !/^\d{8}$/.test(subscriberNumber)) {
      setValidationError('加入者番号は8桁の数字で入力してください');
      return false;
    }
    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
      setValidationError('暗証番号は4桁の数字で入力してください');
      return false;
    }
    if (parsNumber.length !== 4 || !/^\d{4}$/.test(parsNumber)) {
      setValidationError('P-ARS番号は4桁の数字で入力してください');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validate()) return;
    await saveCredentials({ inetId, subscriberNumber, pin, parsNumber });
    if (!useIpatSettingsStore.getState().error) {
      setSaved(true);
      setInetId('');
      setSubscriberNumber('');
      setPin('');
      setParsNumber('');
      setTimeout(() => setSaved(false), 3000);
    }
  };

  const handleDelete = async () => {
    setShowDeleteModal(false);
    await deleteCredentials();
  };

  // ステータス未ロード中はローディング表示
  if (status === undefined) {
    return (
      <div className="fade-in" style={{ padding: 16 }}>
        <button className="back-btn" onClick={() => navigate('/settings')}>
          ← 設定に戻る
        </button>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>IPAT設定</h2>
        <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
          読み込み中...
        </div>
      </div>
    );
  }

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
              INET-ID
            </label>
            <input
              type="text"
              value={inetId}
              onChange={(e) => setInetId(e.target.value)}
              placeholder="8桁の英数字"
              maxLength={8}
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              加入者番号
            </label>
            <input
              type="text"
              value={subscriberNumber}
              onChange={(e) => setSubscriberNumber(e.target.value)}
              placeholder="8桁の数字"
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
              P-ARS番号
            </label>
            <input
              type="password"
              value={parsNumber}
              onChange={(e) => setParsNumber(e.target.value)}
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
