const STORAGE_KEY = 'baken-kaigi-guest-id';

function generateId(): string {
  return crypto.randomUUID();
}

export function getOrCreateGuestId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY);
    if (existing) return existing;

    const id = generateId();
    localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    // localStorage が使えない場合はセッション内の一時IDを返す
    return generateId();
  }
}
