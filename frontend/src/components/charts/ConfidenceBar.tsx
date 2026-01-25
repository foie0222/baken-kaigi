/**
 * AI自信度プログレスバーコンポーネント
 *
 * AIの分析に基づく自信度を視覚的に表示する
 */

interface ConfidenceBarProps {
  /** 自信度（0-100の数値） */
  confidence: number;
  /** ラベルテキスト */
  label?: string;
}

/**
 * 自信度に基づいて色を返す
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 70) return '#2e7d32'; // 緑（高い自信度）
  if (confidence >= 40) return '#f9a825'; // 黄色（中程度）
  return '#c62828'; // 赤（低い自信度）
}

/**
 * 自信度に基づいてテキストを返す
 */
function getConfidenceText(confidence: number): string {
  if (confidence >= 70) return '高';
  if (confidence >= 40) return '中';
  return '低';
}

export function ConfidenceBar({ confidence, label = 'AI分析の自信度' }: ConfidenceBarProps) {
  const clampedConfidence = Math.max(0, Math.min(100, confidence));
  const color = getConfidenceColor(clampedConfidence);
  const text = getConfidenceText(clampedConfidence);

  return (
    <div className="confidence-bar-container" style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <span style={{ fontSize: 14, color: '#666', fontWeight: 500 }}>
          {label}
        </span>
        <span
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: color,
          }}
        >
          {text} ({clampedConfidence}%)
        </span>
      </div>
      <div
        style={{
          width: '100%',
          height: 12,
          backgroundColor: '#e0e0e0',
          borderRadius: 6,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${clampedConfidence}%`,
            height: '100%',
            backgroundColor: color,
            borderRadius: 6,
            transition: 'width 0.5s ease-in-out, background-color 0.3s ease',
          }}
          role="progressbar"
          aria-valuenow={clampedConfidence}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label}: ${clampedConfidence}%`}
        />
      </div>
    </div>
  );
}
