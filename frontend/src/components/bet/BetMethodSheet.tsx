import { BottomSheet } from '../common/BottomSheet';
import { OptionItem, OptionSection } from '../common/OptionItem';
import type { BetType, BetMethod } from '../../types';
import { getAvailableBetMethods } from '../../utils/betMethods';

interface BetMethodSheetProps {
  isOpen: boolean;
  onClose: () => void;
  betType: BetType;
  selectedMethod: BetMethod;
  onSelect: (method: BetMethod) => void;
}

export function BetMethodSheet({
  isOpen,
  onClose,
  betType,
  selectedMethod,
  onSelect,
}: BetMethodSheetProps) {
  const methods = getAvailableBetMethods(betType);

  const handleSelect = (method: BetMethod) => {
    onSelect(method);
    onClose();
  };

  // グループ分け
  const normalMethods = methods.filter(m => m.id === 'normal' || m.id === 'box');
  const nagashiMethods = methods.filter(m => m.id.startsWith('nagashi'));
  const formationMethods = methods.filter(m => m.id === 'formation');

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="買い方を選択">
      {/* 基本 */}
      {normalMethods.map((method) => (
        <OptionItem
          key={method.id}
          title={method.label}
          description={method.description}
          selected={selectedMethod === method.id}
          badge={method.badge}
          onClick={() => handleSelect(method.id)}
        />
      ))}

      {/* 流し */}
      {nagashiMethods.length > 0 && (
        <OptionSection title="流し">
          {nagashiMethods.map((method) => (
            <OptionItem
              key={method.id}
              title={method.label}
              description={method.description}
              selected={selectedMethod === method.id}
              badge={method.badge}
              onClick={() => handleSelect(method.id)}
            />
          ))}
        </OptionSection>
      )}

      {/* フォーメーション */}
      {formationMethods.length > 0 && (
        <OptionSection title="その他">
          {formationMethods.map((method) => (
            <OptionItem
              key={method.id}
              title={method.label}
              description={method.description}
              selected={selectedMethod === method.id}
              onClick={() => handleSelect(method.id)}
            />
          ))}
        </OptionSection>
      )}
    </BottomSheet>
  );
}
