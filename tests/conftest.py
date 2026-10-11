from dataclasses import replace

import pytest

from openvoice_skill.config import Config


@pytest.fixture
def config(tmp_path):
    return replace(Config.load(), data=tmp_path / "data", cache=tmp_path / "cache", exports=tmp_path / "exports")
