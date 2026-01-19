# ドメインモデル概要図

## Unit 1: AI対話機能（認証不要）

---

## 全体アーキテクチャ

```mermaid
flowchart TB
    subgraph Domain["ドメイン層"]
        subgraph Services["ドメインサービス"]
            CS[ConsultationService]
            FG[FeedbackGenerator]
            DC[DeadlineChecker]
            BV[BetSelectionValidator]
        end

        subgraph Aggregates["集約"]
            subgraph CartAgg["Cart集約"]
                Cart["◆ Cart"]
                CartItem[CartItem]
                Cart --> CartItem
            end

            subgraph SessionAgg["ConsultationSession集約"]
                Session["◆ ConsultationSession"]
                Message[Message]
                DF[DataFeedback]
                AF[AmountFeedback]
                Session --> Message
                Session --> DF
                Session --> AF
            end
        end

        subgraph Ports["ポート（インターフェース）"]
            AIClient[AIClient]
            RDP[RaceDataProvider]
        end
    end

    subgraph External["外部参照（リードモデル）"]
        Race[Race]
        Runner[Runner]
        User[User]
    end

    subgraph Infra["インフラストラクチャ層"]
        AIImpl[AIClientImpl<br/>Claude/OpenAI]
        JRA[JRARaceDataProvider]
        CartRepo[CartRepository]
    end

    CS --> Cart
    CS --> Session
    CS --> FG
    CS --> DC
    FG --> AIClient
    FG --> RDP
    DC --> RDP

    CartAgg -.->|参照 ID| External
    SessionAgg -.->|参照 ID| External

    AIImpl -.->|実装| AIClient
    JRA -.->|実装| RDP
```

---

## 集約詳細図

### Cart集約

```mermaid
classDiagram
    class Cart {
        <<集約ルート>>
        -cartId: CartId
        -userId: UserId?
        -items: List~CartItem~
        -createdAt: DateTime
        -updatedAt: DateTime
        +addItem(raceRef, betSelection)
        +removeItem(itemId)
        +clear()
        +getTotalAmount() Money
        +getItemCount() Integer
        +associateUser(userId)
    }

    class CartItem {
        -itemId: ItemId
        -raceReference: RaceReference
        -betSelection: BetSelection
        -addedAt: DateTime
        +getAmount() Money
        +getBetType() BetType
    }

    class BetSelection {
        <<値オブジェクト>>
        -betType: BetType
        -horseNumbers: HorseNumbers
        -amount: Money
        +isValid() Boolean
        +getRequiredCount() Integer
    }

    class RaceReference {
        <<値オブジェクト>>
        -raceId: RaceId
        -raceName: String
        -venue: String
        -startTime: DateTime
        -bettingDeadline: DateTime
        +isBeforeDeadline(now) Boolean
        +getRemainingTime(now) Duration
    }

    class Money {
        <<値オブジェクト>>
        -value: Integer
        +add(other) Money
        +subtract(other) Money
        +format() String
    }

    class HorseNumbers {
        <<値オブジェクト>>
        -numbers: List~Integer~
        +count() Integer
        +toDisplayString() String
    }

    class BetType {
        <<列挙型>>
        WIN
        PLACE
        QUINELLA
        QUINELLA_PLACE
        EXACTA
        TRIO
        TRIFECTA
        +getRequiredCount() Integer
        +getDisplayName() String
    }

    Cart "1" *-- "0..*" CartItem : contains
    CartItem "1" *-- "1" BetSelection : has
    CartItem "1" *-- "1" RaceReference : references
    BetSelection "1" *-- "1" BetType : has
    BetSelection "1" *-- "1" HorseNumbers : has
    BetSelection "1" *-- "1" Money : has
```

### ConsultationSession集約

```mermaid
classDiagram
    class ConsultationSession {
        <<集約ルート>>
        -sessionId: SessionId
        -userId: UserId?
        -cartSnapshot: List~CartItem~
        -messages: List~Message~
        -dataFeedbacks: List~DataFeedback~
        -amountFeedback: AmountFeedback?
        -status: SessionStatus
        -startedAt: DateTime
        -endedAt: DateTime?
        +start(cartItems)
        +addUserMessage(content)
        +addAIMessage(content)
        +setDataFeedbacks(feedbacks)
        +setAmountFeedback(feedback)
        +end()
        +isLimitExceeded(limit) Boolean
    }

    class Message {
        -messageId: MessageId
        -type: MessageType
        -content: String
        -timestamp: DateTime
        +isFromUser() Boolean
        +isFromAI() Boolean
    }

    class DataFeedback {
        <<値オブジェクト>>
        -cartItemId: ItemId
        -horseSummaries: List~HorseDataSummary~
        -overallComment: String
        -generatedAt: DateTime
    }

    class HorseDataSummary {
        <<値オブジェクト>>
        -horseNumber: Integer
        -horseName: String
        -recentResults: String
        -jockeyStats: String
        -trackSuitability: String
        -currentOdds: String
        -popularity: Integer
    }

    class AmountFeedback {
        <<値オブジェクト>>
        -totalAmount: Money
        -remainingLossLimit: Money?
        -averageAmount: Money?
        -isLimitExceeded: Boolean
        -warningLevel: WarningLevel
        -comment: String
        -generatedAt: DateTime
    }

    class SessionStatus {
        <<列挙型>>
        NOT_STARTED
        IN_PROGRESS
        COMPLETED
    }

    class MessageType {
        <<列挙型>>
        USER
        AI
        SYSTEM
    }

    class WarningLevel {
        <<列挙型>>
        NONE
        CAUTION
        WARNING
    }

    ConsultationSession "1" *-- "0..*" Message : contains
    ConsultationSession "1" *-- "0..*" DataFeedback : has
    ConsultationSession "1" *-- "0..1" AmountFeedback : has
    ConsultationSession "1" *-- "1" SessionStatus : has
    Message "1" *-- "1" MessageType : has
    DataFeedback "1" *-- "1..*" HorseDataSummary : contains
    AmountFeedback "1" *-- "1" WarningLevel : has
```

---

## ドメインサービスの依存関係

```mermaid
flowchart TB
    subgraph DomainServices["ドメインサービス"]
        CS[ConsultationService<br/>- startConsultation<br/>- continueConversation<br/>- endConsultation]
        FG[FeedbackGenerator<br/>- generateDataFeedbacks<br/>- generateAmountFeedback]
        DC[DeadlineChecker<br/>- isBeforeDeadline<br/>- checkCartDeadlines]
        BV[BetSelectionValidator<br/>- validate<br/>- validateForRace]
    end

    subgraph Ports["ポート（インターフェース）"]
        AI[AIClient]
        RDP[RaceDataProvider]
    end

    CS --> FG
    CS --> DC
    CS --> BV
    FG --> AI
    FG --> RDP
    DC --> RDP
```

---

## 集約間の関係

```mermaid
flowchart LR
    subgraph CartAggregate["Cart集約"]
        Cart[Cart]
        CI[CartItem]
        Cart --> CI
    end

    subgraph SessionAggregate["ConsultationSession集約"]
        Session[ConsultationSession]
        Msg[Message]
        DF[DataFeedback]
        AF[AmountFeedback]
        Session --> Msg
        Session --> DF
        Session --> AF
    end

    subgraph External["外部リードモデル"]
        Race[Race / Runner / Odds]
        User[User]
    end

    Cart -->|スナップショットコピー| Session
    CI -.->|RaceId参照| Race
    Cart -.->|UserId参照| User
    Session -.->|UserId参照| User
```

---

## ユーザーストーリーとドメインモデルの対応

```mermaid
flowchart TB
    subgraph Stories["ユーザーストーリー"]
        US001[US-01-001<br/>レース一覧表示]
        US002[US-01-002<br/>レース詳細表示]
        US003[US-01-003<br/>買い目入力]
        US003a[US-01-003a<br/>カート追加]
        US003b[US-01-003b<br/>カート管理]
        US003c[US-01-003c<br/>まとめてAI相談]
        US004[US-01-004<br/>AIへの賭け相談]
        US005[US-01-005<br/>データフィードバック]
        US006[US-01-006<br/>掛け金フィードバック]
    end

    subgraph DomainModel["ドメインモデル"]
        EXT[外部リードモデル<br/>Race, Runner]
        BV[BetSelectionValidator]
        BS[BetSelection]
        CART[Cart集約]
        SESS[ConsultationSession集約]
        FG[FeedbackGenerator]
    end

    US001 --> EXT
    US002 --> EXT
    US003 --> BV
    US003 --> BS
    US003a --> CART
    US003b --> CART
    US003c --> CART
    US003c --> SESS
    US004 --> SESS
    US005 --> FG
    US005 --> SESS
    US006 --> FG
    US006 --> SESS
```

---

## 主要なデータフロー

### 買い目をカートに追加してAIに相談するフロー

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant App as アプリケーション層
    participant BV as BetSelectionValidator
    participant Cart as Cart集約
    participant CS as ConsultationService
    participant DC as DeadlineChecker
    participant FG as FeedbackGenerator
    participant RDP as RaceDataProvider
    participant AI as AIClient
    participant Session as ConsultationSession

    U->>App: (1) レース選択
    App->>RDP: getRace(raceId)
    RDP-->>App: RaceData

    U->>App: (2) 買い目入力
    App->>BV: validate(betSelection)
    BV-->>App: ValidationResult

    U->>App: (3) カート追加
    App->>Cart: addItem(raceRef, betSelection)
    Cart-->>App: Cart(更新済み)

    U->>App: (4) AI相談開始
    App->>CS: startConsultation(cart, limit?)
    CS->>Cart: getItems()
    Cart-->>CS: List~CartItem~

    CS->>DC: checkCartDeadlines(cart)
    DC->>RDP: getRace(raceId)
    RDP-->>DC: RaceData
    DC-->>CS: DeadlineCheckResult

    CS->>Session: create() & start(cartItems)

    CS->>FG: generateDataFeedbacks(items)
    FG->>RDP: getRunners(), getPastPerformance()
    RDP-->>FG: データ
    FG->>AI: generateBetFeedback(context)
    AI-->>FG: feedbackText
    FG-->>CS: List~DataFeedback~

    CS->>FG: generateAmountFeedback(total, limit)
    FG->>AI: generateAmountFeedback(context)
    AI-->>FG: feedbackText
    FG-->>CS: AmountFeedback

    CS->>Session: setFeedbacks()
    CS-->>App: ConsultationSession
    App-->>U: AI相談画面表示
```

---

## 値オブジェクト一覧

```mermaid
mindmap
  root((値オブジェクト))
    識別子型
      CartId
      ItemId
      SessionId
      MessageId
      RaceId
      UserId
    ビジネス型
      BetSelection
      Money
      HorseNumbers
      RaceReference
    列挙型
      BetType
      MessageType
      SessionStatus
      WarningLevel
    フィードバック型
      DataFeedback
      HorseDataSummary
      AmountFeedback
```
