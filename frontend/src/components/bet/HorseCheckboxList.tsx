import type { Horse, BetType, BetMethod, ColumnSelections, ColumnConfig } from '../../types';
import { BetTypeRequiredHorses, BetTypeOrdered } from '../../types';
import './HorseCheckboxList.css';

interface HorseCheckboxListProps {
  horses: Horse[];
  betType: BetType;
  method: BetMethod;
  selections: ColumnSelections;
  onSelectionChange: (selections: ColumnSelections) => void;
}

// 列設定を取得
function getColumnConfig(betType: BetType, method: BetMethod): ColumnConfig[] {
  const required = BetTypeRequiredHorses[betType];
  const ordered = BetTypeOrdered[betType];
  const isNagashi = method.startsWith('nagashi');
  const isFormation = method === 'formation';
  const isBox = method === 'box';

  if (method === 'normal' || isBox) {
    return [{ id: 'col1', label: '選択', colorClass: 'col-single' }];
  }

  if (isNagashi) {
    // 馬単の場合
    if (required === 2 && ordered) {
      if (method === 'nagashi_2') {
        return [
          { id: 'col2', label: '1着', colorClass: 'col-partner' },
          { id: 'col1', label: '2着軸', colorClass: 'col-axis' },
        ];
      }
      return [
        { id: 'col1', label: '1着軸', colorClass: 'col-axis' },
        { id: 'col2', label: '2着', colorClass: 'col-partner' },
      ];
    }
    // 三連単の場合
    if (required === 3 && ordered) {
      if (method === 'nagashi_1') {
        return [
          { id: 'col1', label: '1着軸', colorClass: 'col-axis' },
          { id: 'col2', label: '2-3着', colorClass: 'col-partner' },
        ];
      } else if (method === 'nagashi_2') {
        return [
          { id: 'col2', label: '1,3着', colorClass: 'col-partner' },
          { id: 'col1', label: '2着軸', colorClass: 'col-axis' },
        ];
      } else if (method === 'nagashi_3') {
        return [
          { id: 'col2', label: '1-2着', colorClass: 'col-partner' },
          { id: 'col1', label: '3着軸', colorClass: 'col-axis' },
        ];
      }
      // マルチ/軸2頭流し
      return [
        { id: 'col1', label: '軸', colorClass: 'col-axis' },
        { id: 'col2', label: '相手', colorClass: 'col-partner' },
      ];
    }
    // 馬連・ワイド・三連複（順不同）
    return [
      { id: 'col1', label: '軸', colorClass: 'col-axis' },
      { id: 'col2', label: '相手', colorClass: 'col-partner' },
    ];
  }

  if (isFormation) {
    if (required === 2) {
      if (ordered) {
        return [
          { id: 'col1', label: '1着', colorClass: 'col-1' },
          { id: 'col2', label: '2着', colorClass: 'col-2' },
        ];
      }
      return [
        { id: 'col1', label: '1頭目', colorClass: 'col-1' },
        { id: 'col2', label: '2頭目', colorClass: 'col-2' },
      ];
    } else if (required === 3) {
      if (ordered) {
        return [
          { id: 'col1', label: '1着', colorClass: 'col-1' },
          { id: 'col2', label: '2着', colorClass: 'col-2' },
          { id: 'col3', label: '3着', colorClass: 'col-3' },
        ];
      }
      return [
        { id: 'col1', label: '1頭目', colorClass: 'col-1' },
        { id: 'col2', label: '2頭目', colorClass: 'col-2' },
        { id: 'col3', label: '3頭目', colorClass: 'col-3' },
      ];
    }
  }

  return [{ id: 'col1', label: '', colorClass: 'col-single' }];
}

// 軸の最大頭数を取得
function getAxisCount(method: BetMethod, betType: BetType): number {
  const required = BetTypeRequiredHorses[betType];
  if (['nagashi_12', 'nagashi_13', 'nagashi_23', 'nagashi_2_multi'].includes(method)) {
    return 2;
  }
  // 三連複の軸2頭流し
  if (method === 'nagashi_2' && required === 3 && !BetTypeOrdered[betType]) {
    return 2;
  }
  return 1;
}

export function HorseCheckboxList({
  horses,
  betType,
  method,
  selections,
  onSelectionChange,
}: HorseCheckboxListProps) {
  const columnConfig = getColumnConfig(betType, method);
  const required = BetTypeRequiredHorses[betType];
  const isNagashi = method.startsWith('nagashi');
  const axisCount = getAxisCount(method, betType);

  const handleCheckboxChange = (horseNumber: number, colId: keyof ColumnSelections) => {
    const newSelections = { ...selections };

    if (method === 'normal') {
      // 通常モード: 必要頭数まで
      if (selections.col1.includes(horseNumber)) {
        newSelections.col1 = selections.col1.filter(n => n !== horseNumber);
      } else if (selections.col1.length < required) {
        newSelections.col1 = [...selections.col1, horseNumber];
      }
    } else if (method === 'box') {
      // ボックス: 無制限
      if (selections.col1.includes(horseNumber)) {
        newSelections.col1 = selections.col1.filter(n => n !== horseNumber);
      } else {
        newSelections.col1 = [...selections.col1, horseNumber];
      }
    } else if (isNagashi) {
      // 流し: 軸と相手
      if (colId === 'col1') {
        if (selections.col1.includes(horseNumber)) {
          newSelections.col1 = selections.col1.filter(n => n !== horseNumber);
        } else if (selections.col1.length < axisCount) {
          newSelections.col2 = selections.col2.filter(n => n !== horseNumber);
          newSelections.col1 = [...selections.col1, horseNumber];
        }
      } else {
        if (selections.col2.includes(horseNumber)) {
          newSelections.col2 = selections.col2.filter(n => n !== horseNumber);
        } else if (!selections.col1.includes(horseNumber)) {
          newSelections.col2 = [...selections.col2, horseNumber];
        }
      }
    } else if (method === 'formation') {
      // フォーメーション: 各列独立
      if (selections[colId].includes(horseNumber)) {
        newSelections[colId] = selections[colId].filter(n => n !== horseNumber);
      } else {
        newSelections[colId] = [...selections[colId], horseNumber];
      }
    }

    onSelectionChange(newSelections);
  };

  const isAnySelected = (horseNumber: number) => {
    return columnConfig.some(col => selections[col.id]?.includes(horseNumber));
  };

  return (
    <div className={`horse-checkbox-list cols-${columnConfig.length}`}>
      <div className="horse-list-header">
        <span>馬番</span>
        <span>馬名</span>
        <span>単勝</span>
        <div className="header-checkboxes">
          {columnConfig.map(col => (
            <span key={col.id} className={`header-checkbox-label ${col.colorClass}`}>
              {col.label}
            </span>
          ))}
        </div>
      </div>
      {horses.map((horse) => (
        <div
          key={horse.number}
          className={`horse-item ${isAnySelected(horse.number) ? 'selected' : ''}`}
        >
          <div
            className="horse-number"
            style={{
              background: horse.color,
              color: horse.textColor,
              border: horse.wakuBan === 1 ? '1px solid #ccc' : 'none',
            }}
          >
            {horse.number}
          </div>
          <div className="horse-info">
            <div className="horse-name">{horse.name}</div>
            <div className="horse-jockey">{horse.jockey}</div>
          </div>
          <div className="horse-odds">{horse.odds}</div>
          <div className="horse-checkboxes">
            {columnConfig.map(col => (
              <div key={col.id} className={`checkbox-col ${col.colorClass}`}>
                <input
                  type="checkbox"
                  checked={selections[col.id]?.includes(horse.number) || false}
                  onChange={() => handleCheckboxChange(horse.number, col.id)}
                />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
