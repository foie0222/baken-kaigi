import type { BetTypePreference, TargetStyle, BettingPriorityType } from '../types';

export interface PreferenceOption<T extends string> {
  value: T;
  label: string;
}

export const BET_TYPE_PREFERENCE_OPTIONS: readonly PreferenceOption<BetTypePreference>[] = [
  { value: 'trio_focused', label: '三連系重視' },
  { value: 'exacta_focused', label: '馬連系重視' },
  { value: 'wide_focused', label: 'ワイド重視' },
  { value: 'auto', label: 'おまかせ' },
] as const;

export const TARGET_STYLE_OPTIONS: readonly PreferenceOption<TargetStyle>[] = [
  { value: 'honmei', label: '本命' },
  { value: 'medium_longshot', label: '中穴' },
  { value: 'big_longshot', label: '大穴' },
] as const;

export const BETTING_PRIORITY_OPTIONS: readonly PreferenceOption<BettingPriorityType>[] = [
  { value: 'hit_rate', label: '的中率重視' },
  { value: 'roi', label: '回収率重視' },
  { value: 'balanced', label: 'バランス' },
] as const;
