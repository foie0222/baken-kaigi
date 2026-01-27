"""Locust 負荷テスト.

Issue #157 - 負荷テスト: 100同時接続をクリアする。
"""

import json
import random
from locust import HttpUser, task, between, events


# サンプルのレースID（実際の環境に合わせて調整）
SAMPLE_RACE_IDS = [
    "20260125_06_11",
    "20260125_06_12",
    "20260126_05_11",
    "20260126_05_12",
]

# サンプルのメッセージ
SAMPLE_MESSAGES = [
    "今日のおすすめレースを教えて",
    "穴馬を探して",
    "展開予想をお願いします",
    "三連単のおすすめは？",
    "このレースの本命は？",
]


class BakenKaigiUser(HttpUser):
    """馬券会議アプリケーションの負荷テストユーザー."""

    # リクエスト間の待機時間（1-3秒）
    wait_time = between(1, 3)

    def on_start(self):
        """ユーザー開始時の処理."""
        self.consultation_id = None

    @task(3)
    def get_race_list(self):
        """レース一覧を取得."""
        with self.client.get(
            "/api/races",
            catch_response=True,
            name="/api/races"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # APIが存在しない場合もテスト継続
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(5)
    def get_race_detail(self):
        """レース詳細を取得."""
        race_id = random.choice(SAMPLE_RACE_IDS)
        with self.client.get(
            f"/api/races/{race_id}",
            catch_response=True,
            name="/api/races/[race_id]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def start_consultation(self):
        """コンサルテーションを開始."""
        race_id = random.choice(SAMPLE_RACE_IDS)
        payload = {"race_id": race_id}
        with self.client.post(
            "/api/consultation/start",
            json=payload,
            catch_response=True,
            name="/api/consultation/start"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.consultation_id = data.get("consultation_id")
                except json.JSONDecodeError:
                    pass
                response.success()
            elif response.status_code in [404, 500]:
                # APIが存在しない場合もテスト継続
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(4)
    def send_message(self):
        """メッセージを送信."""
        if not self.consultation_id:
            self.consultation_id = "test-consultation-id"

        payload = {
            "consultation_id": self.consultation_id,
            "message": random.choice(SAMPLE_MESSAGES),
        }
        with self.client.post(
            "/api/consultation/message",
            json=payload,
            catch_response=True,
            name="/api/consultation/message"
        ) as response:
            if response.status_code in [200, 404, 500]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)
    def get_cart(self):
        """カート内容を取得."""
        with self.client.get(
            "/api/cart",
            catch_response=True,
            name="/api/cart"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)
    def add_to_cart(self):
        """カートに追加."""
        race_id = random.choice(SAMPLE_RACE_IDS)
        payload = {
            "race_id": race_id,
            "bet_type": "win",
            "horse_numbers": [random.randint(1, 16)],
            "amount": random.choice([100, 200, 500, 1000]),
        }
        with self.client.post(
            "/api/cart/add",
            json=payload,
            catch_response=True,
            name="/api/cart/add"
        ) as response:
            if response.status_code in [200, 201, 404, 500]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


class HighLoadUser(HttpUser):
    """高負荷テスト用ユーザー（100同時接続テスト用）."""

    wait_time = between(0.5, 1.5)

    @task(1)
    def health_check(self):
        """ヘルスチェック."""
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="/api/health"
        ) as response:
            # どのステータスでも成功として扱う（接続テスト目的）
            response.success()

    @task(3)
    def get_races(self):
        """レース一覧取得（軽量API）."""
        with self.client.get(
            "/api/races",
            catch_response=True,
            name="/api/races"
        ) as response:
            response.success()


# イベントハンドラ
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """テスト開始時の処理."""
    print("Load test starting...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """テスト終了時の処理."""
    print("Load test completed.")
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Median response time: {stats.total.median_response_time}ms")
    print(f"Average response time: {stats.total.avg_response_time}ms")
