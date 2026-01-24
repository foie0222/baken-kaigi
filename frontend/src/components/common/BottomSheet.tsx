import { useEffect, useRef } from 'react';
import './BottomSheet.css';

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function BottomSheet({ isOpen, onClose, title, children }: BottomSheetProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className={`bottom-sheet ${isOpen ? 'open' : ''}`}>
      <div className="bottom-sheet-backdrop" onClick={onClose} />
      <div className="bottom-sheet-content" ref={contentRef}>
        <div className="bottom-sheet-header">
          <span className="bottom-sheet-title">{title}</span>
          <button className="bottom-sheet-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="bottom-sheet-body">
          {children}
        </div>
      </div>
    </div>
  );
}
