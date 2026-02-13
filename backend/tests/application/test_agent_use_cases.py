"""エージェントユースケースのテスト."""
import pytest

from src.application.use_cases import (
    AgentAlreadyExistsError,
    AgentNotFoundError,
    CreateAgentUseCase,
    GetAgentUseCase,
    UpdateAgentUseCase,
)
from src.domain.enums import AgentStyle
from src.infrastructure.repositories.in_memory_agent_repository import InMemoryAgentRepository


class TestCreateAgentUseCase:
    """エージェント作成ユースケースのテスト."""

    def _make_repository(self):
        return InMemoryAgentRepository()

    def test_エージェントを作成できる(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        result = use_case.execute("usr_001", "ハヤテ", "solid")

        assert result.agent.name.value == "ハヤテ"
        assert result.agent.base_style == AgentStyle.SOLID
        assert result.agent.performance.total_bets == 0
        assert result.agent.level == 1
        assert result.agent.agent_id.value.startswith("agt_")

    def test_各スタイルでエージェントを作成できる(self):
        for i, style in enumerate(["solid", "longshot", "data", "pace"]):
            repo = self._make_repository()
            use_case = CreateAgentUseCase(repo)
            result = use_case.execute(f"usr_{i}", "テスト", style)
            assert result.agent.base_style.value == style

    def test_同一ユーザーで2体目はエラー(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        use_case.execute("usr_001", "ハヤテ", "solid")

        with pytest.raises(AgentAlreadyExistsError):
            use_case.execute("usr_001", "シンプウ", "data")

    def test_不正なスタイルはエラー(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        with pytest.raises(ValueError):
            use_case.execute("usr_001", "ハヤテ", "invalid_style")

    def test_空の名前はエラー(self):
        repo = self._make_repository()
        use_case = CreateAgentUseCase(repo)
        with pytest.raises(ValueError):
            use_case.execute("usr_001", "", "solid")


class TestGetAgentUseCase:
    """エージェント取得ユースケースのテスト."""

    def test_エージェントを取得できる(self):
        repo = InMemoryAgentRepository()
        create_uc = CreateAgentUseCase(repo)
        create_uc.execute("usr_001", "ハヤテ", "data")

        get_uc = GetAgentUseCase(repo)
        result = get_uc.execute("usr_001")

        assert result.agent.name.value == "ハヤテ"
        assert result.agent.base_style == AgentStyle.DATA

    def test_存在しないユーザーはエラー(self):
        repo = InMemoryAgentRepository()
        get_uc = GetAgentUseCase(repo)

        with pytest.raises(AgentNotFoundError):
            get_uc.execute("usr_nonexistent")


class TestUpdateAgentUseCase:
    """エージェント更新ユースケースのテスト."""

    def test_スタイルを更新できる(self):
        repo = InMemoryAgentRepository()
        create_uc = CreateAgentUseCase(repo)
        create_uc.execute("usr_001", "ハヤテ", "solid")

        update_uc = UpdateAgentUseCase(repo)
        result = update_uc.execute("usr_001", base_style="data")

        assert result.agent.base_style == AgentStyle.DATA

    def test_存在しないユーザーはエラー(self):
        repo = InMemoryAgentRepository()
        update_uc = UpdateAgentUseCase(repo)

        with pytest.raises(AgentNotFoundError):
            update_uc.execute("usr_nonexistent", base_style="data")

    def test_不正なスタイルはエラー(self):
        repo = InMemoryAgentRepository()
        create_uc = CreateAgentUseCase(repo)
        create_uc.execute("usr_001", "ハヤテ", "solid")

        update_uc = UpdateAgentUseCase(repo)
        with pytest.raises(ValueError):
            update_uc.execute("usr_001", base_style="invalid")
