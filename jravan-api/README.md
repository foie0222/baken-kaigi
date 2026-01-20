# JRA-VAN FastAPI サーバー

JV-Link を呼び出して JRA データを提供する FastAPI サーバー。
EC2 Windows 上で動作させ、Lambda からの HTTP リクエストを処理する。

## 前提条件

- Windows Server 2022
- Python 3.11 (32bit) ← **32bit 必須**
- JV-Link インストール済み
- 利用キー設定済み

## EC2 へのデプロイ手順

### 1. Fleet Manager で EC2 に接続

AWS Console → Systems Manager → Fleet Manager → インスタンス選択 → Connect with Remote Desktop

### 2. ファイルを EC2 に転送

PowerShell で以下を実行:

```powershell
# 作業ディレクトリ作成
New-Item -ItemType Directory -Force -Path C:\jravan-api

# GitHub からクローン（Git がある場合）
cd C:\
git clone https://github.com/your-repo/baken-kaigi.git
Copy-Item -Path C:\baken-kaigi\jravan-api\* -Destination C:\jravan-api\ -Recurse

# または手動でファイルをコピー
```

### 3. 依存パッケージのインストール

```powershell
cd C:\jravan-api
pip install -r requirements.txt
```

### 4. 動作確認

```powershell
# サーバー起動
python main.py

# 別ターミナルでテスト
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```

### 5. Windows サービスとして登録

```powershell
# NSSM でサービス化
nssm install JraVanApi "C:\Users\Administrator\AppData\Local\Programs\Python\Python311-32\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set JraVanApi AppDirectory "C:\jravan-api"
nssm start JraVanApi

# サービス状態確認
Get-Service JraVanApi
```

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/races?date=YYYYMMDD` | レース一覧 |
| GET | `/races/{race_id}` | レース詳細 |
| GET | `/races/{race_id}/runners` | 出走馬情報 |
| GET | `/horses/{horse_id}/performances` | 過去成績 |
| GET | `/jockeys/{jockey_id}/stats?course=xxx` | 騎手成績 |

## 注意事項

### 初回データダウンロード

JV-Link は初回起動時に大量のデータをダウンロードします。
これには数時間かかる場合があります。

```
セットアップデータ: 約 2-3GB
所要時間: 1-3 時間（回線速度による）
```

### データ更新

- レースデータ: 毎週更新
- リアルタイムデータ: レース当日に更新

### トラブルシューティング

**JV-Link 初期化エラー**
- 利用キーが正しく設定されているか確認
- 32bit Python を使用しているか確認

**COM オブジェクト作成エラー**
- JV-Link が正しくインストールされているか確認
- pywin32 がインストールされているか確認

## ファイル構成

```
C:\jravan-api\
├── main.py              # FastAPI エントリポイント
├── jvlink_client.py     # JV-Link COM ラッパー
├── requirements.txt     # Python 依存パッケージ
├── run.bat              # 起動スクリプト
└── README.md            # このファイル
```
