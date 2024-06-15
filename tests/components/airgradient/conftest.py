"""AirGradient tests configuration."""

from unittest.mock import patch

from airgradient import Config, Measures
import pytest
from typing_extensions import Generator

from homeassistant.components.airgradient.const import DOMAIN
from homeassistant.const import CONF_HOST

from tests.common import MockConfigEntry, load_fixture
from tests.components.smhi.common import AsyncMock


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.airgradient.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_airgradient_client() -> Generator[AsyncMock]:
    """Mock an AirGradient client."""
    with (
        patch(
            "homeassistant.components.airgradient.AirGradientClient",
            autospec=True,
        ) as mock_client,
        patch(
            "homeassistant.components.airgradient.config_flow.AirGradientClient",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value
        client.host = "10.0.0.131"
        client.get_current_measures.return_value = Measures.from_json(
            load_fixture("current_measures.json", DOMAIN)
        )
        client.get_config.return_value = Config.from_json(
            load_fixture("get_config_local.json", DOMAIN)
        )
        yield client


@pytest.fixture
def mock_new_airgradient_client(
    mock_airgradient_client: AsyncMock,
) -> Generator[AsyncMock]:
    """Mock a new AirGradient client."""
    mock_airgradient_client.get_config.return_value = Config.from_json(
        load_fixture("get_config.json", DOMAIN)
    )
    return mock_airgradient_client


@pytest.fixture
def mock_cloud_airgradient_client(
    mock_airgradient_client: AsyncMock,
) -> Generator[AsyncMock]:
    """Mock a cloud AirGradient client."""
    mock_airgradient_client.get_config.return_value = Config.from_json(
        load_fixture("get_config_cloud.json", DOMAIN)
    )
    return mock_airgradient_client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Airgradient",
        data={CONF_HOST: "10.0.0.131"},
        unique_id="84fce612f5b8",
    )
