import { BottomSheet } from '../common/BottomSheet';
import { OptionItem } from '../common/OptionItem';
import type { BetType } from '../../types';
import { BetTypeLabels } from '../../types';

const betTypeConfigs: Array<{
  type: BetType;
  description: string;
}> = [
  { type: 'win', description: '1着を当てる' },
  { type: 'place', description: '3着以内を当てる' },
  { type: 'quinella', description: '1-2着を当てる（順不同）' },
  { type: 'quinella_place', description: '3着以内の2頭を当てる' },
  { type: 'exacta', description: '1-2着を順番通りに当てる' },
  { type: 'trio', description: '1-2-3着を当てる（順不同）' },
  { type: 'trifecta', description: '1-2-3着を順番通りに当てる' },
];

interface BetTypeSheetProps {
  isOpen: boolean;
  onClose: () => void;
  selectedType: BetType;
  onSelect: (type: BetType) => void;
}

export function BetTypeSheet({
  isOpen,
  onClose,
  selectedType,
  onSelect,
}: BetTypeSheetProps) {
  const handleSelect = (type: BetType) => {
    onSelect(type);
    onClose();
  };

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="券種を選択">
      {betTypeConfigs.map((config) => (
        <OptionItem
          key={config.type}
          title={BetTypeLabels[config.type]}
          description={config.description}
          selected={selectedType === config.type}
          onClick={() => handleSelect(config.type)}
        />
      ))}
    </BottomSheet>
  );
}
