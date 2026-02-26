# RaceDashboardPage 着順カラム追加 設計

## 概要

RaceDashboardPage の出走馬テーブルに着順カラムを常時表示する。
レース未確定の馬は「-」、確定済みの馬は着順を表示（1〜3着はハイライト）。

## 現状

- DB (`baken-kaigi-runners`): `finish_position` 保存済み（HRDBスクレイパー経由）
- バックエンド: `GET /races/{raceId}` は `finish_position` を返していない
- バックエンド: `GET /races/{raceId}/results` は別エンドポイントとして存在
- フロントエンド: 着順に関する実装なし

## 方針

`get_race_detail` レスポンスに `finish_position` を追加するアプローチを採用。
別APIを呼ばず、既存のデータフローに1フィールド追加するだけで完結する。

## 変更範囲

### バックエンド

1. `backend/src/api/handlers/races.py` の `get_race_detail`
   - `runner_dict` に `finish_position` を追加（runnersテーブルから取得済みのデータ）

2. `backend/src/domain/ports/race_data_provider.py` の `RunnerData`
   - `finish_position: int | None = None` フィールドを追加

3. `backend/src/infrastructure/providers/dynamodb_race_data_provider.py`
   - runners クエリ結果から `finish_position` を `RunnerData` にマッピング

### フロントエンド

4. `frontend/src/types/index.ts`
   - `ApiRunner` に `finish_position?: number` 追加
   - `Horse` に `finishPosition?: number` 追加
   - `mapApiRaceDetailToRaceDetail` でマッピング追加

5. `frontend/src/pages/RaceDashboardPage.tsx`
   - テーブルヘッダに「着順」カラム追加（馬名の後、体重の前）
   - 各行に着順セル追加（未確定なら「-」）

6. `frontend/src/pages/RaceDashboardPage.css`
   - `.td-finish-position` スタイル
   - 1着=赤、2着=橙、3着=緑のハイライト

### テスト

7. バックエンドテスト: `get_race_detail` が `finish_position` を返すことを確認
8. フロントエンドテスト: `mapApiRaceDetailToRaceDetail` の型変換テスト
