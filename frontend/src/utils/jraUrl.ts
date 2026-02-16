/**
 * JRA公式出馬表URLを生成する
 * URL形式: https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde{4桁venue}{year}{kaisai_kai}{kaisai_nichime}{race_number}{date}/{checksum}
 *
 * 例: pw01dde0106202601080120260124/F3
 *     - pw01dde: 固定プレフィックス
 *     - 0106: 01+競馬場コード(06=中山)
 *     - 2026: 年
 *     - 01: 回次（kaisai_kai）
 *     - 08: 日目（kaisai_nichime）
 *     - 01: レース番号
 *     - 20260124: 日付
 *     - F3: チェックサム（16進数2桁、大文字）
 */

interface RaceForJraUrl {
  id: string;
  kaisaiKai?: string;
  kaisaiNichime?: string;
  jraChecksum?: number | null;
  number: string;
  venue: string;
}

export function buildJraShutsubaUrl(race: RaceForJraUrl): string | null {
  // 必要なフィールドがない・空文字の場合はnullを返す（チェックサム必須）
  if (!race.kaisaiKai || !race.kaisaiNichime || race.jraChecksum == null) {
    return null;
  }

  // race.id から日付を取得（形式: YYYYMMDDXXRR、12桁数字）
  if (!/^\d{12}$/.test(race.id)) {
    return null;
  }
  const datePart = race.id.substring(0, 8); // "20260124"
  const year = datePart.slice(0, 4); // "2026"

  // race.number から数字部分を取得（形式: "8R" → "08"）
  const raceNum = race.number.replace('R', '').padStart(2, '0');

  // 競馬場コード（4桁: 01+2桁コード）
  const venueCode = race.venue.padStart(2, '0');
  const venue4digit = `01${venueCode}`;

  // kaisai_kai, kaisai_nichime（2桁にパディング）
  const kaisaiKai = race.kaisaiKai.padStart(2, '0');
  const kaisaiNichime = race.kaisaiNichime.padStart(2, '0');

  // チェックサム（16進数2桁、大文字）
  const checksum = race.jraChecksum.toString(16).toUpperCase().padStart(2, '0');

  // URL組み立て
  const cname = `pw01dde${venue4digit}${year}${kaisaiKai}${kaisaiNichime}${raceNum}${datePart}`;
  return `https://www.jra.go.jp/JRADB/accessD.html?CNAME=${cname}/${checksum}`;
}
