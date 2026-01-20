import { useAppStore } from '../../stores/appStore';

export function Toast() {
  const toastMessage = useAppStore((state) => state.toastMessage);

  if (!toastMessage) return null;

  return <div className="toast">{toastMessage}</div>;
}
