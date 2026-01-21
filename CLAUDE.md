# CLAUDE.md - 馬券会議プロジェクト

## プロジェクト概要

競馬AI相談アプリ「馬券会議」のフロントエンド。JRA-VANからレースデータを取得し、AIによる馬券相談機能を提供する。

## 技術スタック

- React + TypeScript + Vite
- Zustand（状態管理）
- API Gateway + Lambda + EC2（バックエンド）
- JRA-VAN Data Lab.（競馬データ）

## 重要な指摘事項（ユーザーフィードバック）

### UI/UX に関する指摘

1. **レース名の表示について**
   - ❌ 「中山 1R」のような会場+レース番号だけは不十分
   - ❌ 「芝1500m」のようなコース情報だけでもダメ
   - ✅ **特別レース名がある場合は「菜の花賞」などを優先表示**
   - ✅ **一般条件戦は「3歳未勝利」「4歳以上1勝クラス」などの条件名を表示**
   - 「メインはレースのタイトルにしたいの！！！」という強い要望あり

2. **不要な機能は削除**
   - 日付ボタンの「前週」「次週」プレフィックスは不要と指摘され削除
   - ヘッダーに日付表示を追加したが「やっぱりいらない」と言われて削除

### 開発プロセスに関する指摘

- UI変更は実装前に確認を取った方が良い
- ユーザーの意図を正確に理解してから実装する

## JRA-VAN データ構造

### RAレコード（レース詳細）のフィールド位置

| フィールド | 位置 | 説明 |
|-----------|------|------|
| レコード種別 | 0:2 | "RA" |
| 開催日 | 11:19 | YYYYMMDD |
| 競馬場コード | 19:21 | 01=札幌, 06=中山, 08=京都 等 |
| 開催回 | 21:23 | |
| 日次 | 23:25 | |
| レース番号 | 25:27 | |
| **Hondai（本題）** | **32:92** | 特別レース名（菜の花賞等）※通常レースは空 |
| 年齢条件コード | 511:513 | 33=3歳, 34=3歳以上, 44=4歳以上 等 |
| JyokenCD | 525:528 | 条件コード |
| トラックコード | 507:509 | 12=芝, 14=ダート, 19=障害 |
| 距離 | 593:597 | メートル |
| 発走時刻 | 734:738 | HHMM |

### 条件コード（JyokenCD）マッピング

```python
JYOKEN_NAMES = {
    "701": "新馬",
    "703": "未勝利",
    "005": "1勝クラス",
    "010": "2勝クラス",
    "016": "3勝クラス",
    "999": "オープン",
}
```

### 年齢条件コード

```python
AGE_CONDITIONS = {
    "31": "3歳",
    "33": "3歳",
    "34": "3歳以上",
    "41": "4歳以上",
    "42": "4歳以上",
    "43": "4歳以上",
    "44": "4歳以上",
    "04": "",  # 障害
}
```

## EC2 サーバー情報

- インスタンスID: `i-08347ed1e2c4bcc80`
- 作業ディレクトリ: `C:\jravan-api`
- 主要ファイル:
  - `sync_jvlink.py` - JV-Linkからデータ同期
  - `main.py` - FastAPI サーバー
  - `jvdata.db` - SQLiteデータベース

### SSM経由でのスクリプト実行例

```bash
# Base64エンコードしてスクリプトを送信・実行
SCRIPT_B64=$(cat << 'SCRIPT' | base64 -w0
# Pythonスクリプト
SCRIPT
)

aws ssm send-command \
  --instance-ids "i-08347ed1e2c4bcc80" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters "commands=[\"[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('$SCRIPT_B64')) | Set-Content -Path 'C:\\jravan-api\\script.py' -Encoding UTF8; cd C:\\jravan-api; python script.py\"]"
```

## API エンドポイント

- **本番**: `https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod`
- レース一覧: `GET /races?date=YYYY-MM-DD`
- レース詳細: `GET /races/{race_id}`

## 競馬場コード

```typescript
const VENUE_NAMES = {
  "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
  "05": "東京", "06": "中山", "07": "中京", "08": "京都",
  "09": "阪神", "10": "小倉",
};
```
