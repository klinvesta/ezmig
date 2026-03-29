from pathlib import Path

import pytest
from typer.testing import CliRunner

from .utils import copy_example


class ExampleEnv:
    def __init__(self, runner, path, app):
        self.runner = runner
        self.path = path
        self.app = app

    def load(self, name: str):
        copy_example(name, self.path)

    def run(self, *args):
        return self.runner.invoke(self.app, list(args))


@pytest.fixture
def example_env():
    runner = CliRunner()

    from ezmig.cli import app

    with runner.isolated_filesystem() as tmp_dir:
        env = ExampleEnv(runner, Path(tmp_dir), app)  # ✅ inject here
        yield env
