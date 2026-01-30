# 負荷テスト

Locust を使用した負荷テストです。

## セットアップ

```bash
pip install locust
```

## 実行方法

### Web UI モード
```bash
cd backend/tests/load
locust -f locustfile.py --host=https://your-api-endpoint.com
```
その後、http://localhost:8089 にアクセスしてテストを実行。

### コマンドラインモード（100同時接続テスト）
```bash
locust -f locustfile.py \
    --host=https://your-api-endpoint.com \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 60s \
    --only-summary
```

### パラメータ説明
- `--users 100`: 同時接続ユーザー数
- `--spawn-rate 10`: 1秒あたりに生成するユーザー数
- `--run-time 60s`: テスト実行時間
- `--only-summary`: サマリーのみ出力

## テストクラス

### BakenKaigiUser
通常のユーザー行動をシミュレート:
- レース一覧取得
- レース詳細取得
- コンサルテーション開始
- メッセージ送信
- カート操作

### HighLoadUser
高負荷テスト専用（100同時接続テスト用）:
- ヘルスチェック
- レース一覧取得（軽量）

## 完了条件（Issue #157）
- 100同時接続での安定動作
- 平均レスポンスタイム < 2秒
- エラー率 < 1%
