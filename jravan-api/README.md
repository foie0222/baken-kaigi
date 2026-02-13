# JRA-VAN FastAPI サーバー

PC-KEIBA Database (PostgreSQL) からレースデータを提供する FastAPI サーバー。

## 前提条件

- Python 3.11+
- PC-KEIBA Database がインストール・設定済み
- PostgreSQL サーバーが稼働中

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
# PC-KEIBA Database 接続設定
export PCKEIBA_HOST=localhost
export PCKEIBA_PORT=5432
export PCKEIBA_DATABASE=jvd_db
export PCKEIBA_USER=postgres
export PCKEIBA_PASSWORD=your_password
```

### 3. 動作確認

```bash
# サーバー起動
python main.py

# 別ターミナルでテスト
curl http://localhost:8000/health
```

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/sync-status` | データベース状態 |
| GET | `/races?date=YYYYMMDD` | レース一覧 |
| GET | `/races/{race_id}` | レース詳細 |
| GET | `/races/{race_id}/runners` | 出走馬情報（オッズ含む） |
| GET | `/races/{race_id}/weights` | レースの馬体重 |
| GET | `/horses/{horse_id}/pedigree` | 血統情報 |
| GET | `/horses/{horse_id}/weights` | 馬体重履歴 |

## PC-KEIBA Database テーブル構造

主要テーブル:

| テーブル | 内容 |
|----------|------|
| `jvd_ra` | レース詳細 |
| `jvd_se` | 出走馬情報 |
| `jvd_um` | 馬マスタ（血統） |
| `jvd_o1` | 単勝・複勝オッズ |
| `jvd_hr` | 払戻情報 |

### 血統カラム (jvd_um)

| カラム | 内容 |
|--------|------|
| `ketto_joho_01b` | 父 |
| `ketto_joho_02b` | 母 |
| `ketto_joho_05b` | 母父 |

## ファイル構成

```
jravan-api/
├── main.py              # FastAPI エントリポイント
├── database.py          # PostgreSQL データアクセス層
├── requirements.txt     # Python 依存パッケージ
├── run.bat              # 起動スクリプト（Windows用）
└── README.md            # このファイル
```

## Windows サービスとして登録 (EC2)

```powershell
# NSSM でサービス化
nssm install JraVanApi "python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set JraVanApi AppDirectory "C:\jravan-api"
nssm set JraVanApi AppEnvironmentExtra PCKEIBA_PASSWORD=your_password
nssm start JraVanApi

# サービス状態確認
Get-Service JraVanApi
```

## データ更新

PC-KEIBA Database のデータ更新は PC-KEIBA アプリケーションから行います。
JV-Link を通じてデータを取得・更新してください。
