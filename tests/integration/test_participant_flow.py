import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from tests.fixtures.container import create_test_container


class TestParticipantFlow:
    def setup_method(self):
        self.container = create_test_container()
        self.controller = self.container.participant_controller()

    @pytest.mark.asyncio
    async def test_complete_add_flow(self):
        # Test full flow
        pass
