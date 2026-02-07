interface PasswordStrengthIndicatorProps {
  password: string;
}

function getStrength(password: string): { level: number; label: string; color: string } {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[a-z]/.test(password)) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  if (score <= 2) return { level: 1, label: '弱い', color: '#e53935' };
  if (score <= 3) return { level: 2, label: '普通', color: '#fb8c00' };
  return { level: 3, label: '強い', color: '#43a047' };
}

export function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
  if (!password) return null;

  const { level, label, color } = getStrength(password);

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              background: i <= level ? color : '#e0e0e0',
            }}
          />
        ))}
      </div>
      <span style={{ fontSize: 12, color }}>{label}</span>
    </div>
  );
}
