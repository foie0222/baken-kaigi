import { useAppStore } from '../../stores/appStore';

export function Toast() {
  const toastMessage = useAppStore((state) => state.toastMessage);
  const toastType = useAppStore((state) => state.toastType);

  if (!toastMessage) return null;

  const className = toastType === 'error' ? 'toast toast-error' : 'toast';

  return <div className={className}>{toastMessage}</div>;
}
