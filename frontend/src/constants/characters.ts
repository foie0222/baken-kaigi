export interface AICharacter {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export const AI_CHARACTERS: AICharacter[] = [
  { id: 'analyst', name: 'データ分析官', icon: '\u{1F4CA}', description: '統計データに基づく冷静な分析' },
  { id: 'intuition', name: '直感の達人', icon: '\u{1F3B2}', description: '数字に表れない要素を重視' },
  { id: 'conservative', name: '堅実派', icon: '\u{1F6E1}\u{FE0F}', description: 'リスク管理・資金管理重視' },
  { id: 'aggressive', name: '勝負師', icon: '\u{1F525}', description: '高配当・穴馬を積極的に分析' },
];

export const DEFAULT_CHARACTER_ID = 'analyst';

export const STORAGE_KEY_CHARACTER = 'baken-kaigi-character';
