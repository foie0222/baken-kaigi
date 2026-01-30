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

- `/ec2-sync` - EC2操作の簡易インターフェース
- `/jravan-ec2` - 詳細なSSMコマンドリファレンス

> **Note**: JRA-VANデータの同期はPC-KEIBAソフトで行います。

### よく使うコマンド

```bash
# インスタンスID確認
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*jravan*" \
  --query 'Reservations[].Instances[].InstanceId' --output text

# インスタンス状態確認
/ec2-sync status

# ファイル送信
/ec2-sync upload main.py

# ログ確認
/ec2-sync logs
```

## SSMファイル送信時の注意（Windows BOM問題）

**重要**: AWS SSM経由でWindows EC2にファイルを送信する際、PowerShellの `Out-File -Encoding UTF8` はBOM（Byte Order Mark: `EF BB BF`）を付加する。

### 問題

BOMが付加されると以下の問題が発生する:

- `python-dotenv` が `.env` ファイルを正しく解析できない（キー名が `\ufeffKEY_NAME` になる）
- Pythonスクリプトの先頭に `#` ではなく BOM が入り、shebang が無効になる

### 解決策

BOMなしUTF-8で書き込む:

```powershell
# BOMなしUTF-8で書き込み
$content = "PCKEIBA_PASSWORD=your_password"
$encoding = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("C:\jravan-api\.env", $content, $encoding)
```

### 既存ファイルからBOMを除去

```powershell
$bytes = [System.IO.File]::ReadAllBytes("C:\jravan-api\file.py")
if ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
    $bytes = $bytes[3..($bytes.Length-1)]
    [System.IO.File]::WriteAllBytes("C:\jravan-api\file.py", $bytes)
}
```

### Base64経由でのファイル送信（推奨）

`/jravan-ec2` スキルのBase64方式を使う場合、Linux側でBase64エンコードするためBOM問題は発生しない。ただし、PowerShell側でデコード後に `Out-File -Encoding UTF8` を使うと再びBOMが付加される点に注意。

## API Gateway確認

```bash
aws apigateway get-rest-apis --query 'items[?name==`baken-kaigi-api`].id' --output text
```

## CloudWatch Logs確認

```bash
aws logs tail /aws/lambda/baken-kaigi-get-races --follow
```

## CI/CD

- **GitHub Actions**: プッシュ/PR時に自動テスト実行
- **Amplify**: `main` ブランチへのマージで自動デプロイ
