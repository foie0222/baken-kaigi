# JRA-VAN Data Lab. セットアップガイド

## 概要

JRA-VAN Data Lab. は、JRA（日本中央競馬会）の公式データ配信サービスです。
本システムでは、JRA-VAN Data Lab. の JV-Link を使用してレースデータを取得します。

## 料金

| プラン | 料金（税込） | 備考 |
|--------|-------------|------|
| 月額 | 2,090円 | 使い放題 |
| 3ヶ月 | 6,270円 | 割引なし |
| 12ヶ月 | 25,080円 | 割引なし |
| 2台利用 | 2,900円/月 | 複数PC対応 |

## セットアップ手順

### Phase 1: Data Lab. 会員登録

#### Step 1: 会員登録

1. [JRA-VAN Data Lab. 公式サイト](https://jra-van.jp/dlb/) にアクセス
2. 「データラボ会員になる」をクリック
3. 必要情報を入力して会員登録を完了

#### Step 2: 利用キー発行

1. 購入手続き完了後、[専用ページ](https://jra-van.jp/sup/support.html) にログイン
2. 「利用キー発行」から利用キーを確認・取得
3. 利用キーは JV-Link 設定時に必要なので控えておく

#### Step 3: JV-Link インストール

1. [JV-Link ダウンロードページ](https://app.jra-van.jp/cgi-cnt/datalab/id/JVLink_Install.html) にアクセス
2. JV-Link インストーラーをダウンロード
3. インストーラーを実行してセットアップを完了

#### Step 4: 利用キー設定

1. 「JV-Link 設定」アプリを起動
2. 取得した利用キーを入力
3. 設定を保存

> **注意**: PC リカバリや OS 入れ替え時は利用キーの再発行が必要です。

### Phase 2: 開発者登録（ソフト作者登録）

本システムを公開する場合は、ソフト作者登録が必要です。

#### Step 1: 作者登録

1. [各種手続き・確認](https://jra-van.jp/dlb/sdv/support.html) にアクセス
2. 「ソフト作者登録」からサインアップ
3. 登録した住所に郵送で**作者ID**が発行される（数日〜1週間程度）

#### Step 2: パスワード発行

1. 作者IDを受け取ったら、[ソフト作者サポートページ](https://jra-van.jp/dlb/sdv/support.html) にアクセス
2. 「パスワード発行・再発行」からパスワードを取得
3. 競馬ソフト申請に必要

#### Step 3: ソフト登録申請

1. ソフト作者サポートページの「競馬ソフト登録」から申請
2. JRA-VAN サポートデスクによる検証（数週間かかる場合あり）
3. 結果はメールで通知
4. 承認後、ソフトがWEB上で紹介されて完了

### Phase 3: SDK（開発キット）の取得

#### Step 1: SDK ダウンロード

1. [JRA-VAN Data Lab. 開発者コミュニティ](https://developer.jra-van.jp/) にアクセス
2. 「ドキュメント」→「ソフトウェア開発キット（SDK）」をクリック
3. 「JRA-VAN SDK本体」をダウンロード

最新バージョン: **Ver.4.9.0.2**（2024年8月7日時点）

#### Step 2: SDK 内容確認

ダウンロードしたZIPを解凍すると以下が含まれます：

```
JRA-VAN_SDK/
├── JV-Link/           # サーバ通信モジュール（インストーラー）
├── JV-Data構造体/     # 構造体定義（C#, C++, Delphi7, VB2019）
├── サンプルプログラム/  # サンプルコード（Delphi7, VB2019, VC2019）
├── Data Lab.検証ツール/
└── ドキュメント/       # 各種仕様書
```

#### 主要ドキュメント

| ドキュメント名 | バージョン | 内容 |
|---------------|-----------|------|
| JV-Link インターフェース仕様書 | Ver.4.9.0.1 | API仕様 |
| JRA-VAN Data Lab. 開発ガイド | Ver.4.2.2 | 開発全般 |
| JV-Data 仕様書 | Ver.4.9.0.1 | データ構造（PDF/Excel） |
| イベント開発ガイド | - | VB/C++版 |

## 技術要件

### JV-Link の制約

- **32bit アプリケーション専用**: JV-Link は 32bit COM コンポーネント
- **Windows 専用**: Windows 環境でのみ動作
- **Python 32bit 版が必要**: 64bit Python からは直接利用不可

### 推奨環境

| 項目 | 推奨 |
|------|------|
| OS | Windows Server 2022 / Windows 10/11 |
| Python | 3.11 (32bit) |
| 必要ライブラリ | pywin32（COM操作用） |
| ストレージ | 30GB以上の空き容量（データベース用） |

## 本システムでのアーキテクチャ

```
[Lambda (AWS)]
    ↓ HTTP (Private IP / VPC内)
[EC2 Windows - t3.small]
    └─ FastAPI サーバー (Python 32bit)
        └─ JV-Link (COM)
            ↓
        [JRA-VAN Data Lab.]
```

### 構成の理由

1. **JV-Link が 32bit COM**: Lambda から直接利用不可
2. **Windows 必須**: EC2 Windows を中継サーバーとして使用
3. **VPC 内通信**: セキュリティ確保のため Private IP で通信

## EC2 Windows セットアップ

EC2 Windows インスタンスの立ち上げ方法は2つあります：
- **方法A**: AWS コンソールから手動で作成（推奨：初回セットアップ向け）
- **方法B**: AWS CDK で自動化（インフラをコードで管理したい場合）

---

### 方法A: AWS コンソールから手動で作成

#### Step 1: VPC の確認

Lambda と同じ VPC を使用します。VPC ID をメモしておきます。

1. AWS コンソール → VPC → お使いの VPC
2. VPC ID（例: `vpc-xxxxxxxxx`）を控える
3. プライベートサブネット ID も控える

#### Step 2: セキュリティグループの作成

1. AWS コンソール → EC2 → セキュリティグループ → 「セキュリティグループを作成」

2. 基本設定：
   - セキュリティグループ名: `jravan-api-sg`
   - 説明: `Security group for JRA-VAN API server`
   - VPC: Lambda と同じ VPC を選択

3. インバウンドルール：
   | タイプ | ポート | ソース | 説明 |
   |--------|--------|--------|------|
   | カスタム TCP | 8000 | Lambda のセキュリティグループ または VPC CIDR | FastAPI |
   | RDP | 3389 | 自分の IP（初期設定用） | リモートデスクトップ |

4. アウトバウンドルール：
   | タイプ | ポート | 送信先 | 説明 |
   |--------|--------|--------|------|
   | すべてのトラフィック | すべて | 0.0.0.0/0 | インターネットアクセス |

#### Step 3: キーペアの作成

1. AWS コンソール → EC2 → キーペア → 「キーペアを作成」
2. 名前: `jravan-api-key`
3. タイプ: RSA
4. 形式: `.pem`（Mac/Linux）または `.ppk`（Windows PuTTY）
5. 作成してダウンロード（**紛失注意！再ダウンロード不可**）

#### Step 4: EC2 インスタンスの起動

1. AWS コンソール → EC2 → インスタンス → 「インスタンスを起動」

2. 名前とタグ：
   - 名前: `jravan-api-server`

3. AMI の選択：
   - **Microsoft Windows Server 2022 Base** を選択
   - アーキテクチャ: 64-bit (x86)

4. インスタンスタイプ：
   - **t3.small**（2 vCPU, 2 GiB メモリ）
   - 月額コスト目安: 約 $15〜20（東京リージョン、オンデマンド）

5. キーペア：
   - 作成したキーペア（`jravan-api-key`）を選択

6. ネットワーク設定：
   - VPC: Lambda と同じ VPC
   - サブネット: **プライベートサブネット**を選択
   - パブリック IP の自動割り当て: **無効化**
   - セキュリティグループ: 作成した `jravan-api-sg`

7. ストレージ：
   - **50 GiB** gp3（JV-Link データ用に余裕を持たせる）

8. 「インスタンスを起動」をクリック

#### Step 5: Windows パスワードの取得

1. インスタンスが「実行中」になるまで待つ（数分）
2. インスタンスを選択 → アクション → セキュリティ → 「Windows パスワードを取得」
3. キーペアファイル（.pem）をアップロード
4. 「パスワードを復号化」をクリック
5. ユーザー名（Administrator）とパスワードを控える

#### Step 6: リモートデスクトップ接続

**プライベートサブネットの場合**（推奨構成）：

踏み台（Bastion）経由で接続するか、AWS Systems Manager Session Manager を使用します。

**Session Manager を使う場合**：

1. EC2 インスタンスに IAM ロールをアタッチ（AmazonSSMManagedInstanceCore ポリシー）
2. AWS コンソール → EC2 → インスタンス → 接続 → 「Session Manager」タブ
3. 「接続」をクリック

**踏み台経由の場合**：

1. パブリックサブネットに踏み台 Windows を作成
2. 踏み台から EC2 の Private IP に RDP 接続

#### Step 7: Private IP の確認

1. AWS コンソール → EC2 → インスタンス
2. 作成したインスタンスの「プライベート IPv4 アドレス」を確認
3. 例: `10.0.1.100`
4. この IP を `JRAVAN_API_URL` に設定（`http://10.0.1.100:8000`）

---

### 方法B: AWS CDK で自動化

プロジェクトに CDK スタックを追加して EC2 を管理する場合：

#### Step 1: CDK スタックの作成

`cdk/stacks/jravan_server_stack.py` を作成：

```python
"""JRA-VAN API サーバースタック."""
from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct


class JraVanServerStack(Stack):
    """JRA-VAN API サーバー用 EC2 スタック."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # セキュリティグループ
        self.security_group = ec2.SecurityGroup(
            self,
            "JraVanApiSG",
            vpc=vpc,
            description="Security group for JRA-VAN API server",
            allow_all_outbound=True,
        )

        # Lambda からのアクセスを許可（VPC CIDR）
        self.security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(8000),
            "Allow FastAPI from VPC",
        )

        # SSM 用 IAM ロール
        role = iam.Role(
            self,
            "JraVanApiRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # Windows Server 2022 AMI
        windows_ami = ec2.MachineImage.latest_windows(
            ec2.WindowsVersion.WINDOWS_SERVER_2022_JAPANESE_FULL_BASE
        )

        # EC2 インスタンス
        self.instance = ec2.Instance(
            self,
            "JraVanApiInstance",
            instance_type=ec2.InstanceType("t3.small"),
            machine_image=windows_ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_group=self.security_group,
            role=role,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=50,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                    ),
                )
            ],
        )

        # Private IP を出力
        CfnOutput(
            self,
            "PrivateIp",
            value=self.instance.instance_private_ip,
            description="JRA-VAN API Server Private IP",
        )

        # API URL を出力
        CfnOutput(
            self,
            "ApiUrl",
            value=f"http://{self.instance.instance_private_ip}:8000",
            description="JRA-VAN API URL for Lambda",
        )
```

#### Step 2: app.py に追加

```python
from cdk.stacks.jravan_server_stack import JraVanServerStack

# VPC を作成または既存のものを参照
vpc = ec2.Vpc.from_lookup(app, "ExistingVpc", vpc_id="vpc-xxxxxxxxx")

# JRA-VAN サーバースタック
jravan_stack = JraVanServerStack(
    app,
    "JraVanServerStack",
    vpc=vpc,
)

# API スタック（JRA-VAN 連携）
api_stack = BakenKaigiApiStack(
    app,
    "BakenKaigiApiStack",
    vpc=vpc,
    jravan_api_url=f"http://{jravan_stack.instance.instance_private_ip}:8000",
)
```

#### Step 3: デプロイ

```bash
cd cdk
cdk deploy JraVanServerStack
cdk deploy BakenKaigiApiStack
```

---

### EC2 内でのソフトウェアセットアップ

EC2 Windows に接続したら、以下の手順でセットアップします。

#### 1. Python 3.11 (32bit) のインストール

1. ブラウザで https://www.python.org/downloads/ にアクセス
2. Python 3.11.x の **Windows installer (32-bit)** をダウンロード
3. インストーラーを実行
   - **「Add Python to PATH」にチェック**
   - 「Install Now」をクリック

#### 2. 必要パッケージのインストール

PowerShell を管理者として実行：

```powershell
# pip を最新に更新
python -m pip install --upgrade pip

# 必要パッケージをインストール
pip install fastapi uvicorn pywin32 requests
```

#### 3. JV-Link のインストール

1. JRA-VAN SDK をダウンロード（Phase 3 参照）
2. SDK を解凍し、`JV-Link` フォルダ内の `JV-Link.exe` を実行
3. インストール完了後、「JV-Link 設定」を起動
4. 利用キーを入力して保存

#### 4. FastAPI サーバーの配置

`C:\jravan-api\` フォルダを作成し、以下のファイルを配置：

```
C:\jravan-api\
├── main.py              # FastAPI エントリポイント
├── jvlink_client.py     # JV-Link ラッパー
├── models.py            # レスポンスモデル
├── requirements.txt
└── run.bat              # 起動スクリプト
```

**run.bat**:
```batch
@echo off
cd /d C:\jravan-api
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 5. Windows サービスとして登録（自動起動）

NSSM（Non-Sucking Service Manager）を使用：

```powershell
# NSSM をダウンロード
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "nssm.zip"
Expand-Archive -Path "nssm.zip" -DestinationPath "C:\nssm"

# サービスをインストール
C:\nssm\nssm-2.24\win64\nssm.exe install JraVanApi "C:\Users\Administrator\AppData\Local\Programs\Python\Python311-32\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
C:\nssm\nssm-2.24\win64\nssm.exe set JraVanApi AppDirectory "C:\jravan-api"

# サービスを開始
C:\nssm\nssm-2.24\win64\nssm.exe start JraVanApi

# 自動起動を確認
Get-Service JraVanApi
```

#### 6. 動作確認

```powershell
# ローカルで確認
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# レスポンス例: {"status": "ok"}
```

---

### コスト見積もり

| リソース | スペック | 月額コスト目安（東京リージョン） |
|----------|----------|--------------------------------|
| EC2 t3.small | 2 vCPU, 2 GiB | 約 $15〜20（オンデマンド） |
| EBS gp3 50GB | 50 GiB | 約 $4〜5 |
| データ転送 | VPC 内 | 無料 |
| **合計** | | **約 $20〜25/月** |

> **コスト削減 Tips**:
> - 競馬開催日のみ使用する場合は、EC2 を停止しておく
> - リザーブドインスタンス（1年）で約 30% 割引
> - スポットインスタンスは中断リスクがあるため非推奨

## トラブルシューティング

### JV-Link が動作しない

1. 利用キーが正しく設定されているか確認
2. 32bit Python を使用しているか確認
3. pywin32 がインストールされているか確認

### Lambda から接続できない

1. EC2 のセキュリティグループで 8000番ポートが開いているか確認
2. Lambda が同じ VPC 内に配置されているか確認
3. EC2 の Private IP が正しいか確認

### データ取得に時間がかかる

初回のデータ取得は大量のデータをダウンロードするため時間がかかります。
定期的にデータ同期を実行して、差分取得に切り替えてください。

## 参考リンク

- [JRA-VAN Data Lab. 公式サイト](https://jra-van.jp/dlb/)
- [JRA-VAN Data Lab. 開発者コミュニティ](https://developer.jra-van.jp/)
- [JRA-VAN ヘルプセンター](https://support.jra-van.jp/)
- [SDK ダウンロード（ドキュメント）](https://developer.jra-van.jp/t/topic/45)
- [ソフト登録の流れ](https://developer.jra-van.jp/t/topic/29)
