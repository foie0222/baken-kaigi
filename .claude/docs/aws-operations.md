# AWS操作ガイド

## 認証

AWS認証情報が必要な場合:

```bash
aws login
```

## CDKデプロイ

**重要**: 必ず `--context jravan=true` を付けること。

```bash
cd cdk
npx cdk deploy --all --context jravan=true --require-approval never
```

このフラグがないとLambda関数がVPCなしのモックモードになる。

## デプロイ前チェック

```bash
./scripts/pre-deploy-check.sh
```

詳細: `/deploy-prep` スキルを使用

## EC2操作

EC2（JRA-VAN API）の操作は以下のスキルを使用:

- `/ec2-sync` - データ同期・EC2操作の簡易インターフェース
- `/jravan-ec2` - 詳細なSSMコマンドリファレンス

### よく使うコマンド

```bash
# インスタンスID確認
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*jravan*" \
  --query 'Reservations[].Instances[].InstanceId' --output text

# インスタンス状態確認
/ec2-sync status

# ファイル送信
/ec2-sync upload sync_jvlink.py

# データ同期
/ec2-sync sync
/ec2-sync sync-from 20260101

# ログ確認
/ec2-sync logs
```

## API Gateway確認

```bash
aws apigateway get-rest-apis --query 'items[?name==`baken-kaigi-api`].id' --output text
```

## CloudWatch Logs確認

```bash
aws logs tail /aws/lambda/baken-kaigi-races --follow
```

## CI/CD

- **GitHub Actions**: プッシュ/PR時に自動テスト実行
- **Amplify**: `main` ブランチへのマージで自動デプロイ
