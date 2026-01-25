# TODO Issues 実装ガイド

## 汎用テンプレート

以下のワークフローは全Issueに適用できる。各ステップを順番に実行し、完了したらチェックを入れる。

### ワークフロー

```
┌─────────────────┐
│  1. Issue確認   │
└────────┬────────┘
         ▼
┌─────────────────┐
│2. リポジトリ確認 │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. 実装方針作成 │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. テスト実装   │ ← TDD: Red
└────────┬────────┘
         ▼
┌─────────────────┐
│   5. 実装       │ ← TDD: Green
└────────┬────────┘
         ▼
┌─────────────────┐
│6. コミット/PR   │
└────────┬────────┘
         ▼
┌─────────────────┐
│  7. デプロイ    │
└────────┬────────┘
         ▼
┌─────────────────┐
│  8. 動作確認    │
└────────┬────────┘
         ▼
┌─────────────────────────────────────────┐
│ 9. Copilotコメント確認                  │
│    ├─ 修正指摘あり → 修正 → 動作確認 ─┐│
│    │                      ↑           ││
│    │                      └───────────┘│
│    └─ 修正指摘なし → 完了              │
└────────┬────────────────────────────────┘
         ▼
┌─────────────────┐
│  10. PRマージ   │
└─────────────────┘
```

### 各ステップ詳細

#### 1. Issue確認
- [ ] Issueの要件を読み込む
- [ ] 返却データの形式を確認
- [ ] パラメータを確認
- [ ] 利用テーブル・依存関係を確認

#### 2. リポジトリ確認
- [ ] 既存の類似実装パターンを確認
- [ ] テストパターンを確認
- [ ] 依存モジュールを確認

#### 3. 実装方針作成
- [ ] エンドポイント設計
- [ ] データベースクエリ設計
- [ ] エラーハンドリング設計

#### 4. テスト実装（TDD: Red）
- [ ] 正常系テスト作成
- [ ] 異常系テスト作成（404、バリデーションエラー等）
- [ ] テスト実行して失敗を確認

#### 5. 実装（TDD: Green）
- [ ] database.py に関数追加
- [ ] main.py にエンドポイント追加
- [ ] テスト実行して成功を確認

#### 6. コミット/PR作成
- [ ] `git checkout -b feat/issue-{番号}-{機能名}`
- [ ] `git add` で変更ファイルをステージング
- [ ] `git commit -m "feat: {説明}"`
- [ ] `git push -u origin {ブランチ名}`
- [ ] `gh pr create --title "{タイトル}" --body "{本文}"`

#### 7. デプロイ
- [ ] `./scripts/pre-deploy-check.sh` 実行
- [ ] `cd cdk && npx cdk deploy --all --context jravan=true --require-approval never`

#### 8. 動作確認
- [ ] 本番環境でAPIエンドポイントを叩いて確認
- [ ] 期待通りのレスポンスが返ることを確認

#### 9. Copilotコメント対応
**重要: Copilotの指摘は後回しにしない。指摘があれば即座に対応する。**

- [ ] PR上のCopilotコメントを確認
- [ ] 修正指摘がある場合:
  - [ ] 指摘内容を修正
  - [ ] コミット/プッシュ
  - [ ] 動作確認
  - [ ] コメントに返信して解決済みをマーク
  - [ ] 再度Copilotコメントを確認（ループ）
- [ ] 修正指摘がない場合: 次へ

#### 10. PRマージ
- [ ] PRがマージ可能な状態か確認
- [ ] マージ実行

---

## Issue #79: 馬の過去成績取得APIエンドポイント追加

### 1. Issue確認

- [x] **要件**: 馬の過去レース成績（着順、タイム、上がり3F等）を取得するAPI
- [x] **エンドポイント**: `GET /horses/{horse_id}/performances`
- [x] **返却データ**:
  ```json
  {
    "horse_id": "string",
    "horse_name": "string",
    "performances": [
      {
        "race_id": "string",
        "race_date": "YYYYMMDD",
        "race_name": "string",
        "venue": "string",
        "distance": 1600,
        "track_type": "芝",
        "track_condition": "良",
        "finish_position": 1,
        "total_runners": 16,
        "time": "1:33.5",
        "time_diff": "+0.2",
        "last_3f": "33.8",
        "weight_carried": 57.0,
        "jockey_name": "string",
        "odds": 3.5,
        "popularity": 2,
        "margin": "クビ",
        "race_pace": "S",
        "running_style": "差し"
      }
    ]
  }
  ```
- [x] **パラメータ**:
  - `limit`: 取得件数（デフォルト: 5、最大: 20）
  - `track_type`: 芝/ダート/障害 でフィルタ
- [x] **利用テーブル**:
  - `jvd_se` (出走馬情報): kakutei_chakujun, time_value, nobori_jikan
  - `jvd_ra` (レース情報): 関連レース情報

### 2. リポジトリ確認

- [ ] **既存パターン確認**:
  - `jravan-api/main.py`: FastAPIエンドポイント定義
  - `jravan-api/database.py`: データベースアクセス関数

- [ ] **テストパターン確認**:
  - `jravan-api/tests/test_statistics.py`: `@patch("database.get_db")` でDBモック
  - `MagicMock` でカーソル・接続をモック

- [ ] **関連テーブルカラム確認**:
  - `jvd_se`: ketto_toroku_bango, kakutei_chakujun, time_value, nobori_jikan, futan_juryo, kishu_name, tansho_odds, kakutei_ninki, chakusa_code
  - `jvd_ra`: race_id, kaisai_nen, kaisai_tsukihi, race_name, keibajo_code, kyori, track_code, baba_jotai

### 3. 実装方針作成

- [ ] **database.py**:
  ```python
  def get_horse_performances(
      horse_id: str,
      limit: int = 5,
      track_type: str | None = None
  ) -> list[dict]:
      """馬の過去成績を取得する."""
      # jvd_se と jvd_ra を JOIN
      # ketto_toroku_bango = horse_id でフィルタ
      # kaisai_tsukihi で降順ソート
      # limit 件取得
  ```

- [ ] **main.py**:
  ```python
  @app.get("/horses/{horse_id}/performances")
  def get_horse_performances(
      horse_id: str,
      limit: int = Query(5, ge=1, le=20),
      track_type: str | None = Query(None)
  ):
      # database.get_horse_performances() 呼び出し
      # 404 ハンドリング
  ```

### 4. テスト実装（TDD: Red）

- [ ] **テストファイル作成**: `jravan-api/tests/test_horse_performances.py`

- [ ] **正常系テスト**:
  ```python
  def test_get_horse_performances_success():
      """馬の過去成績が正常に取得できる"""
      # モックデータ準備
      # エンドポイント呼び出し
      # レスポンス検証
  ```

- [ ] **件数制限テスト**:
  ```python
  def test_get_horse_performances_with_limit():
      """limit パラメータで件数制限できる"""
  ```

- [ ] **トラック種別フィルタテスト**:
  ```python
  def test_get_horse_performances_filter_by_track_type():
      """track_type でフィルタできる"""
  ```

- [ ] **404テスト**:
  ```python
  def test_get_horse_performances_not_found():
      """存在しない馬IDで404が返る"""
  ```

- [ ] **テスト実行**: `cd jravan-api && pytest tests/test_horse_performances.py -v`
- [ ] **失敗を確認**（Red）

### 5. 実装（TDD: Green）

- [ ] **database.py に関数追加**:
  - `get_horse_performances()` 関数実装
  - JOINクエリ作成
  - データ変換処理

- [ ] **main.py にエンドポイント追加**:
  - `/horses/{horse_id}/performances` エンドポイント
  - パラメータバリデーション
  - エラーハンドリング

- [ ] **テスト実行**: `cd jravan-api && pytest tests/test_horse_performances.py -v`
- [ ] **成功を確認**（Green）

- [ ] **全テスト実行**: `cd jravan-api && pytest`
- [ ] **既存テストが壊れていないことを確認**

### 6. コミット/PR作成

- [ ] `git checkout -b feat/issue-79-horse-performances`
- [ ] `git add jravan-api/database.py jravan-api/main.py jravan-api/tests/test_horse_performances.py`
- [ ] コミットメッセージ:
  ```
  feat: 馬の過去成績取得APIエンドポイント追加 (#79)

  - GET /horses/{horse_id}/performances エンドポイント追加
  - limit, track_type パラメータ対応
  - テスト追加
  ```
- [ ] `git push -u origin feat/issue-79-horse-performances`
- [ ] PR作成: `gh pr create --title "feat: 馬の過去成績取得APIエンドポイント追加 (#79)" --body "..."`

### 7. デプロイ

- [ ] `./scripts/pre-deploy-check.sh`
- [ ] `cd cdk && npx cdk deploy --all --context jravan=true --require-approval never`

### 8. 動作確認

- [ ] EC2上のAPIエンドポイントを確認:
  ```bash
  curl "https://{API_URL}/horses/{馬ID}/performances?limit=5"
  ```
- [ ] レスポンスが期待通りか確認

### 9. Copilotコメント対応

**重要: 指摘は即座に対応する**

- [ ] `gh pr view --comments` でコメント確認
- [ ] 修正指摘があれば:
  - [ ] コード修正
  - [ ] テスト実行
  - [ ] コミット/プッシュ
  - [ ] 動作確認
  - [ ] コメント返信
  - [ ] 再確認（ループ）

### 10. PRマージ

- [ ] CI/CDチェック通過確認
- [ ] PRマージ
- [ ] Issueクローズ確認

---

## 関連Issue一覧

### JRA-VAN APIエンドポイント
| Issue | タイトル | 優先度 |
|-------|---------|--------|
| #79 | 馬の過去成績取得API | 高 |
| #80 | 騎手の詳細成績取得API | 高 |
| #81 | 調教師成績取得API | 中 |
| #82 | 血統詳細取得API | 中 |
| #83 | 馬体重推移取得API | 中 |
| #84 | 調教データ取得API | 中 |
| #85 | 産駒成績取得API | 低 |
| #86 | 種牡馬成績取得API | 低 |
| #87 | コース別統計取得API | 中 |

### AgentCoreツール
| Issue | タイトル | 依存 |
|-------|---------|------|
| #88 | 過去成績分析ツール | #79 |
| #89 | 騎手詳細分析ツール | #80 |
| #90 | 調教師分析ツール | #81 |
| #91 | 血統分析ツール | #82 |
| #92 | 馬体重分析ツール | #83 |
| #93 | 調教分析ツール | #84 |
