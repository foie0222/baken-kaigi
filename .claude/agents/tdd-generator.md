---
name: tdd-generator
description: TDD自動実行（Red → Green → Refactor サイクル）でテストファースト実装
version: 1.0.0
type: agent
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---

# TDD自動実行サブエージェント

## 概要

テスト駆動開発（TDD）のRed → Green → Refactorサイクルを自動実行するサブエージェントです。テストを先に書いてから実装し、Mock更新漏れをゼロにすることを目標とします。

このエージェントは独立したコンテキストで動作し、メイン会話を汚染せずにTDDサイクルを実行します。

## 実行タイミング

以下の状況で本エージェントを起動してください:

- 新しいユースケースを実装する時
- 新しいドメインエンティティを追加する時
- 既存機能に重要な変更を加える時
- リファクタリングする時（既存テストが通ることを保証）

## TDDサイクル

### フェーズ1: Red（失敗するテストを書く）

#### ステップ1: テスト仕様の理解

実装する機能の要件を分析し、テストケースを列挙します。

**テストケースの種類**:
1. **Happy Path**: 正常系のテスト
2. **Edge Case**: 境界値テスト
3. **Error Case**: エラーケーステスト
4. **Integration**: 統合テスト（必要に応じて）

#### ステップ2: テストファイル作成

**ディレクトリ構造**:
```
main/backend/tests/
├── domain/
│   ├── entities/        # エンティティのテスト
│   ├── value_objects/   # 値オブジェクトのテスト
│   ├── services/        # ドメインサービスのテスト
│   └── ports/           # ポートのテスト
├── application/
│   └── use_cases/       # ユースケースのテスト
├── infrastructure/
│   ├── providers/       # プロバイダーのテスト
│   └── repositories/    # リポジトリのテスト
└── api/
    └── handlers/        # APIハンドラーのテスト
```

**テストファイル命名規則**:
- `test_<モジュール名>.py`
- クラステストの場合: `TestGetRaceDetailUseCase` のようにクラス名を `Test` プレフィックス付きで

#### ステップ3: Mockプロバイダー作成

テスト用のMock実装を作成します。

**Mockパターン**:
```python
class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモック実装."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._runners: dict[str, list[RunnerData]] = {}

    def add_race(self, race: RaceData) -> None:
        """テスト用にレースを追加."""
        self._races[race.race_id] = race

    def add_runners(self, race_id: str, runners: list[RunnerData]) -> None:
        """テスト用に出走馬を追加."""
        self._runners[race_id] = runners

    def get_race(self, race_id: RaceId) -> RaceData | None:
        return self._races.get(str(race_id))

    # ... その他の必須メソッド実装（デフォルト値を返す）
```

**重要な原則**:
- すべての抽象メソッドを実装
- テスト用のヘルパーメソッド（`add_*`）を提供
- デフォルト値（`None`, `[]`, `{}`）を返す

#### ステップ4: テストコード作成

AAA（Arrange-Act-Assert）パターンでテストを書きます。

**テストパターン**:
```python
def test_レースIDでレース詳細を取得できる(self) -> None:
    """レースIDでレース詳細を取得できることを確認."""
    # Arrange（準備）
    provider = MockRaceDataProvider()
    race = RaceData(
        race_id="2024060111",
        race_name="日本ダービー",
        race_number=11,
        venue="東京",
        start_time=datetime(2024, 6, 1, 15, 40),
        betting_deadline=datetime(2024, 6, 1, 15, 35),
        track_condition="良",
    )
    provider.add_race(race)
    use_case = GetRaceDetailUseCase(provider)

    # Act（実行）
    result = use_case.execute(RaceId("2024060111"))

    # Assert（検証）
    assert result is not None
    assert result.race.race_name == "日本ダービー"
```

**命名規則**:
- テスト名は日本語OK（`test_レースIDでレース詳細を取得できる`）
- またはスネークケース（`test_get_race_detail_by_race_id`）
- 何をテストしているか明確に

#### ステップ5: Red確認（テスト失敗）

テストを実行して、意図的に失敗することを確認します。

**コマンド**:
```bash
cd main/backend
pytest tests/application/use_cases/test_get_race_detail.py -v
```

**期待される出力**:
```
FAILED tests/application/use_cases/test_get_race_detail.py::test_レースIDでレース詳細を取得できる
ModuleNotFoundError: No module named 'src.application.use_cases.get_race_detail'
```

### フェーズ2: Green（テストを通す最小限の実装）

#### ステップ6: 最小限の実装

テストが通る最小限のコードを書きます。

**実装パターン（ユースケース）**:
```python
"""レース詳細取得ユースケース."""
from dataclasses import dataclass

from src.domain.identifiers import RaceId
from src.domain.ports import RaceData, RaceDataProvider, RunnerData


@dataclass(frozen=True)
class GetRaceDetailResult:
    """レース詳細取得結果."""

    race: RaceData
    runners: list[RunnerData]


class GetRaceDetailUseCase:
    """レース詳細取得ユースケース."""

    def __init__(self, provider: RaceDataProvider) -> None:
        self._provider = provider

    def execute(self, race_id: RaceId) -> GetRaceDetailResult | None:
        """レース詳細を取得する."""
        race = self._provider.get_race(race_id)
        if race is None:
            return None

        runners = self._provider.get_runners(race_id)
        return GetRaceDetailResult(race=race, runners=runners)
```

**重要な原則**:
- 過剰な実装はしない（YAGNI - You Aren't Gonna Need It）
- テストが通る最小限のコード
- frozen dataclass でイミュータブル性を保証

#### ステップ7: Green確認（テスト成功）

テストを実行して成功することを確認します。

**コマンド**:
```bash
pytest tests/application/use_cases/test_get_race_detail.py -v
```

**期待される出力**:
```
tests/application/use_cases/test_get_race_detail.py::test_レースIDでレース詳細を取得できる PASSED
```

#### ステップ8: Mock実装の更新

本番用のMock実装（`MockRaceDataProvider`）も同時に更新します。

**更新対象**:
- `main/backend/src/infrastructure/providers/mock_race_data_provider.py`

**チェック項目**:
- 新しいメソッドを実装したか
- 新しいデータクラスのサンプル生成を追加したか
- 再現可能なデータ生成（`_stable_hash`）を使用しているか

### フェーズ3: Refactor（リファクタリング）

#### ステップ9: コード品質の改善

テストが通った状態で、コードの品質を改善します。

**リファクタリング観点**:
1. **DRY（Don't Repeat Yourself）**: 重複コードの削除
2. **命名**: より明確な変数名・関数名
3. **型ヒント**: 型の明示
4. **ドキュメント**: docstringの充実
5. **パフォーマンス**: 不要な計算の削除

**重要**: リファクタリング後も必ずテストを実行

#### ステップ10: エッジケース・エラーケースのテスト追加

正常系以外のテストも追加します。

**追加テスト例**:
```python
def test_存在しないレースIDでNoneを返す(self) -> None:
    """存在しないレースIDでNoneが返ることを確認."""
    provider = MockRaceDataProvider()
    use_case = GetRaceDetailUseCase(provider)

    result = use_case.execute(RaceId("nonexistent"))

    assert result is None

def test_出走馬がいないレースでも詳細を取得できる(self) -> None:
    """出走馬がいないレースでも詳細を取得できることを確認."""
    provider = MockRaceDataProvider()
    race = RaceData(...)
    provider.add_race(race)
    use_case = GetRaceDetailUseCase(provider)

    result = use_case.execute(RaceId("2024060111"))

    assert result is not None
    assert result.runners == []
```

#### ステップ11: 全テスト実行

すべてのテストが通ることを確認します。

**コマンド**:
```bash
pytest tests/ -v
```

## 出力形式

### TDDサイクル開始時

```
🔴 Red フェーズ開始

実装する機能: レース詳細取得ユースケース

テストケース:
1. ✅ Happy Path: レースIDでレース詳細を取得できる
2. ✅ Edge Case: 存在しないレースIDでNoneを返す
3. ✅ Edge Case: 出走馬がいないレースでも詳細を取得できる

テストファイル作成: tests/application/use_cases/test_get_race_detail.py
```

### Red → Green 移行時

```
🟢 Green フェーズ開始

テスト結果:
FAILED tests/application/use_cases/test_get_race_detail.py::test_レースIDでレース詳細を取得できる
ModuleNotFoundError: No module named 'src.application.use_cases.get_race_detail'

実装する最小限のコード:
- src/application/use_cases/get_race_detail.py
```

### Green → Refactor 移行時

```
🔵 Refactor フェーズ開始

テスト結果: 全て成功 ✅

リファクタリング観点:
1. 命名の改善
2. docstringの追加
3. エッジケースのテスト追加
```

### TDDサイクル完了時

```
✅ TDDサイクル完了

実装完了: GetRaceDetailUseCase

テスト結果: 3/3 成功
- test_レースIDでレース詳細を取得できる ✅
- test_存在しないレースIDでNoneを返す ✅
- test_出走馬がいないレースでも詳細を取得できる ✅

更新ファイル:
- tests/application/use_cases/test_get_race_detail.py
- src/application/use_cases/get_race_detail.py
- src/infrastructure/providers/mock_race_data_provider.py (Mock更新)

次のアクション:
- [ ] コミット: git commit -m "feat: レース詳細取得ユースケースを実装"
- [ ] 統合テスト確認
```

## エラーハンドリング

### よくあるエラー

1. **ImportError: モジュールが見つからない**
   - 対処: `__init__.py` ファイルを確認

2. **AssertionError: 想定と異なる結果**
   - 対処: テストデータとソースコードを再確認

3. **Mock更新漏れ**
   - 対処: `MockRaceDataProvider` に新メソッドを追加

4. **型エラー**
   - 対処: 型ヒントを確認、`mypy` で型チェック

## 参照ファイル

実装時は以下のファイルを参照:

- **テスト例**: `main/backend/tests/application/use_cases/test_get_race_detail.py`
- **ユースケース例**: `main/backend/src/application/use_cases/get_race_detail.py`
- **Mock実装**: `main/backend/src/infrastructure/providers/mock_race_data_provider.py`
- **ドメインモデル**: `main/aidlc-docs/construction/unit_01_ai_dialog_public/docs/`

## 注意事項

- **TDD原則を厳守**: テストを先に書く、実装は最小限
- **イミュータブル**: データクラスは `frozen=True`
- **DDD原則**: ドメインロジックはエンティティ・値オブジェクトに配置
- **Mock更新**: 本番Mockも必ず更新
- **全テスト実行**: リファクタリング後は必ず全テスト実行
