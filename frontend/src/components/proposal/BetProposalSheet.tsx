import { useState } from 'react';
import { BottomSheet } from '../common/BottomSheet';
import { BetProposalContent } from './BetProposalContent';
import type { RaceDetail } from '../../types';

interface BetProposalSheetProps {
  isOpen: boolean;
  onClose: () => void;
  race: RaceDetail;
}

export function BetProposalSheet({ isOpen, onClose, race }: BetProposalSheetProps) {
  // keyを変えることでBetProposalContentをリマウント（state reset）する
  const [resetKey, setResetKey] = useState(0);

  const handleClose = () => {
    setResetKey((k) => k + 1);
    onClose();
  };

  return (
    <BottomSheet isOpen={isOpen} onClose={handleClose} title="AI買い目提案">
      <BetProposalContent key={resetKey} race={race} />
    </BottomSheet>
  );
}
