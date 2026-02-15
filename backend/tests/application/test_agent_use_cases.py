"""エージェントユースケースのテスト."""
import pytest

from src.application.use_cases import (
    AgentAlreadyExistsError,
    AgentNotFoundError,
    CreateAgentUseCase,
    GetAgentUseCase,
    UpdateAgentUseCase,
)
from src.domain.value_objects import BettingPreference
from src.infrastructure.repositories.in_memory_agent_repository import InMemoryAgentRepository


class TestCreateAgentUseCase:
    """エージェント作成ユースケースのテスト."""

    def _make_repository(self):
        return InMemoryAgentRepository()

    def test_エージェントを作成できる(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        result = use_case.execute("usr_001", "ハヤテ")

        assert result.agent.name.value == "ハヤテ"
        assert result.agent.betting_preference == BettingPreference.default()
        assert result.agent.agent_id.value.startswith("agt_")

    def test_同一ユーザーで2体目はエラー(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        use_case.execute("usr_001", "ハヤテ")

        with pytest.raises(AgentAlreadyExistsError):
            use_case.execute("usr_001", "シンプウ")

    def test_空の名前はエラー(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        with pytest.raises(ValueError):
            use_case.execute("usr_001", "")


class TestGetAgentUseCase:
    """エージェント取得ユースケースのテスト."""

    def test_エージェントを取得できる(self):
        repo = InMemoryAgentRepository()
        create_uc = CreateAgentUseCase(repo)
        create_uc.execute("usr_001", "ハヤテ")

        get_uc = GetAgentUseCase(repo)
        result = get_uc.execute("usr_001")

        assert result.agent.name.value == "ハヤテ"

    def test_存在しないユーザーはエラー(self):
        repo = InMemoryAgentRepository()
        get_uc = GetAgentUseCase(repo)

        with pytest.raises(AgentNotFoundError):
            get_uc.execute("usr_nonexistent")


class TestUpdateAgentUseCase:
    """エージェント更新ユースケースのテスト."""

    def test_存在しないユーザーはエラー(self):
        repo = InMemoryAgentRepository()
        update_uc = UpdateAgentUseCase(repo)

        with pytest.raises(AgentNotFoundError):
            update_uc.execute("usr_nonexistent")


class TestUpdateAgentPreferenceUseCase:
    """エージェント好み設定更新のテスト."""

    def test_好み設定を更新できる(self):
        repo = InMemoryAgentRepository()
        CreateAgentUseCase(repo).execute("usr_001", "ハヤテ")
        uc = UpdateAgentUseCase(repo)

        result = uc.execute(
            "usr_001",
            betting_preference={
                "bet_type_preference": "trio_focused",
            },
            custom_instructions="三連単が好き",
        )
        assert result.agent.betting_preference.bet_type_preference.value == "trio_focused"
        assert result.agent.custom_instructions == "三連単が好き"

    def test_好み設定のみ更新できる(self):
        repo = InMemoryAgentRepository()
        CreateAgentUseCase(repo).execute("usr_001", "ハヤテ")
        uc = UpdateAgentUseCase(repo)

        result = uc.execute(
            "usr_001",
            betting_preference={
                "bet_type_preference": "wide_focused",
            },
        )
        assert result.agent.betting_preference.bet_type_preference.value == "wide_focused"
