# ホスティング構成

## ドメイン

| 項目 | 値 |
|------|-----|
| ドメイン名 | bakenkaigi.com |
| レジストラ | お名前.com |
| 取得日 | 2026年1月 |

## DNS

| 項目 | 値 |
|------|-----|
| プロバイダ | Cloudflare（無料プラン） |
| 管理画面 | https://dash.cloudflare.com/ |

### レコード構成

| サブドメイン | 用途 | タイプ | 向き先 |
|-------------|------|--------|--------|
| `@`（ルート） | フロントエンド | CNAME | Amplify |
| `api` | バックエンドAPI | CNAME | API Gateway |

## フロントエンド（Amplify）

| 項目 | 値 |
|------|-----|
| URL | https://bakenkaigi.com |
| ホスティング | AWS Amplify |
| SSL証明書 | Amplify マネージド（自動更新） |
| デプロイ | main ブランチへのプッシュで自動デプロイ |

## バックエンドAPI（API Gateway）

| 項目 | 値 |
|------|-----|
| URL | https://api.bakenkaigi.com |
| サービス | API Gateway（REST API） |
| SSL証明書 | ACM（AWS Certificate Manager） |
| ステージ | prod |

## 構成図

```mermaid
flowchart TB
    subgraph registrar["📝 お名前.com"]
        domain["🌐 bakenkaigi.com"]
    end

    subgraph cloudflare["☁️ Cloudflare DNS"]
        direction LR
        root["@ (ルート)<br/>CNAME"]
        api_record["api<br/>CNAME"]
    end

    subgraph aws["☁️ AWS"]
        subgraph frontend["フロントエンド"]
            amplify["📱 Amplify<br/>• React + TypeScript<br/>• 自動デプロイ<br/>• SSL自動管理"]
        end

        subgraph backend["バックエンドAPI"]
            apigw["🔌 API Gateway<br/>REST API"]
            lambda["⚡ Lambda<br/>Python"]

            subgraph ai["AI相談機能"]
                agentcore["🤖 Bedrock<br/>AgentCore"]
            end
        end

        subgraph ec2zone["JRA-VAN データ基盤"]
            ec2["🖥️ EC2 Windows<br/>FastAPI Server"]
            subgraph dataLayer[" "]
                direction LR
                jvlink["📊 JV-Link<br/>JRA-VAN Data Lab."]
                postgres["🗄️ PostgreSQL<br/>PC-KEIBA Database"]
            end
        end
    end

    domain --> cloudflare
    root -->|"bakenkaigi.com"| amplify
    api_record -->|"api.bakenkaigi.com"| apigw
    apigw --> lambda
    lambda --> agentcore
    lambda -->|"直接API"| ec2
    agentcore -->|"ツール経由"| ec2
    ec2 --> postgres
    jvlink -->|"データ同期"| postgres

    style registrar fill:#f5f5f5,stroke:#333,stroke-width:2px
    style cloudflare fill:#f48120,stroke:#333,stroke-width:2px,color:#fff
    style aws fill:#232f3e,stroke:#ff9900,stroke-width:2px,color:#fff
    style frontend fill:#1a73e8,stroke:#fff,stroke-width:1px,color:#fff
    style backend fill:#1a73e8,stroke:#fff,stroke-width:1px,color:#fff
    style ai fill:#7b42bc,stroke:#fff,stroke-width:1px,color:#fff
    style ec2zone fill:#2e7d32,stroke:#fff,stroke-width:1px,color:#fff
    style dataLayer fill:#2e7d32,stroke:none
    style domain fill:#fff,stroke:#333
    style amplify fill:#ff9900,stroke:#fff,color:#000
    style apigw fill:#ff9900,stroke:#fff,color:#000
    style lambda fill:#ff9900,stroke:#fff,color:#000
    style agentcore fill:#9c27b0,stroke:#fff,color:#fff
    style ec2 fill:#4caf50,stroke:#fff,color:#fff
    style postgres fill:#336791,stroke:#fff,color:#fff
    style jvlink fill:#1976d2,stroke:#fff,color:#fff
```

## 備考

- www.bakenkaigi.com は未設定（必要に応じて後から追加可能）
- Cloudflare の Proxy は OFF（DNS only）に設定
