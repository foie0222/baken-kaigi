#!/bin/bash
# デプロイ前チェックスクリプト
# CDKデプロイ・EC2更新前に必ず実行すること

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "デプロイ前チェックを開始します"
echo "========================================"
echo ""

# バックエンドテスト
echo "[1/4] バックエンドテスト実行中..."
cd "$PROJECT_ROOT/backend"
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt 2>/dev/null || true
fi
python -m pytest tests/ -v --tb=short
echo "-> バックエンドテスト完了"
echo ""

# フロントエンドリント
echo "[2/4] フロントエンドリント実行中..."
cd "$PROJECT_ROOT/frontend"
npm run lint
echo "-> リント完了"
echo ""

# フロントエンドテスト
echo "[3/4] フロントエンドテスト実行中..."
npm run test:run
echo "-> フロントエンドテスト完了"
echo ""

# CDK Synth
echo "[4/4] CDK Synth 確認中..."
cd "$PROJECT_ROOT/cdk"
npx cdk synth --context jravan=true > /dev/null
echo "-> CDK Synth 完了"
echo ""

echo "========================================"
echo "全てのチェックが完了しました"
echo "デプロイを続行できます"
echo "========================================"
