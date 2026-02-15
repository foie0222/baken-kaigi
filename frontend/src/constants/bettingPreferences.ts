import type { BetTypePreference } from '../types';

export interface PreferenceOption<T extends string> {
  value: T;
  label: string;
}

export const BET_TYPE_PREFERENCE_OPTIONS: readonly PreferenceOption<BetTypePreference>[] = [
  { value: 'trio_focused', label: '三連系重視' },
  { value: 'exacta_focused', label: '馬単系重視' },
  { value: 'quinella_focused', label: '馬連系重視' },
  { value: 'wide_focused', label: 'ワイド重視' },
  { value: 'auto', label: 'おまかせ' },
] as const;
