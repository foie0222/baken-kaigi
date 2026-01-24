import type { BetType, BetMethod } from '../types';
import { BetTypeRequiredHorses, BetTypeOrdered } from '../types';

export interface BetMethodOption {
  id: BetMethod;
  label: string;
  description: string;
  badge?: string;
}

export function getAvailableBetMethods(betType: BetType): BetMethodOption[] {
  const required = BetTypeRequiredHorses[betType];
  const ordered = BetTypeOrdered[betType];

  // 単勝・複勝は通常のみ
  if (required === 1) {
    return [{ id: 'normal', label: '通常', description: '1頭をぴったり選択' }];
  }

  const methods: BetMethodOption[] = [
    { id: 'normal', label: '通常', description: `${required}頭をぴったり選択` },
    { id: 'box', label: 'ボックス', description: '選んだ馬の全組み合わせ' },
  ];

  if (ordered) {
    // 馬単
    if (required === 2) {
      methods.push(
        { id: 'nagashi_1', label: '1着流し', description: '軸が1着、相手が2着' },
        { id: 'nagashi_2', label: '2着流し', description: '相手が1着、軸が2着' },
        { id: 'nagashi_multi', label: 'マルチ', description: '1着流し＋2着流し', badge: '×2' },
      );
    }
    // 三連単
    if (required === 3) {
      methods.push(
        { id: 'nagashi_1', label: '軸1頭 1着流し', description: '軸が1着固定' },
        { id: 'nagashi_2', label: '軸1頭 2着流し', description: '軸が2着固定' },
        { id: 'nagashi_3', label: '軸1頭 3着流し', description: '軸が3着固定' },
        { id: 'nagashi_1_multi', label: '軸1頭 マルチ', description: '軸がどこでもOK', badge: '×3' },
        { id: 'nagashi_12', label: '軸2頭 1-2着流し', description: '軸2頭が1-2着' },
        { id: 'nagashi_13', label: '軸2頭 1-3着流し', description: '軸2頭が1-3着' },
        { id: 'nagashi_23', label: '軸2頭 2-3着流し', description: '軸2頭が2-3着' },
        { id: 'nagashi_2_multi', label: '軸2頭 マルチ', description: '軸2頭がどこでもOK', badge: '×6' },
      );
    }
  } else {
    // 馬連・ワイド
    if (required === 2) {
      methods.push(
        { id: 'nagashi', label: '軸1頭流し', description: '軸から相手へ' },
      );
    }
    // 三連複
    if (required === 3) {
      methods.push(
        { id: 'nagashi', label: '軸1頭流し', description: '軸から相手へ' },
        { id: 'nagashi_2', label: '軸2頭流し', description: '軸2頭から相手へ' },
      );
    }
  }

  methods.push(
    { id: 'formation', label: 'フォーメーション', description: '着順ごとに候補を指定' },
  );

  return methods;
}

export function getBetMethodLabel(method: BetMethod, betType: BetType): string {
  const methods = getAvailableBetMethods(betType);
  const found = methods.find(m => m.id === method);
  return found?.label || '通常';
}
