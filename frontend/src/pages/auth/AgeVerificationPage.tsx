import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

export function AgeVerificationPage() {
  const navigate = useNavigate();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear - 25);
  const [month, setMonth] = useState(1);
  const [day, setDay] = useState(1);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    // 有効な日付かバリデーション（2/31等の無効日付を検出）
    const birthDate = new Date(year, month - 1, day);
    if (
      birthDate.getFullYear() !== year ||
      birthDate.getMonth() !== month - 1 ||
      birthDate.getDate() !== day
    ) {
      setErrorMsg('有効な日付を入力してください。');
      return;
    }

    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    if (today.getMonth() < birthDate.getMonth() ||
        (today.getMonth() === birthDate.getMonth() && today.getDate() < birthDate.getDate())) {
      age--;
    }

    if (age < 20) {
      setErrorMsg('20歳未満の方は馬券会議をご利用いただけません。');
      return;
    }

    navigate('/signup/terms', { state: { birthdate: `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}` } });
  };

  const years = Array.from({ length: 80 }, (_, i) => currentYear - 20 - i);
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  const days = Array.from({ length: 31 }, (_, i) => i + 1);

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>年齢確認</h2>

      <p style={{ textAlign: 'center', color: '#666', marginBottom: 24, fontSize: 14 }}>
        馬券購入には20歳以上であることが必要です。
        <br />
        生年月日を入力してください。
      </p>

      {errorMsg && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ flex: 2 }}>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>年</label>
            <select value={year} onChange={(e) => setYear(Number(e.target.value))}
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16 }}>
              {years.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>月</label>
            <select value={month} onChange={(e) => setMonth(Number(e.target.value))}
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16 }}>
              {months.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>日</label>
            <select value={day} onChange={(e) => setDay(Number(e.target.value))}
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16 }}>
              {days.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>

        <button type="submit" style={{
          padding: 14, background: '#1a73e8', color: 'white', border: 'none',
          borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer',
        }}>
          次へ
        </button>
      </form>
    </div>
  );
}
