def test_sqlite_example_runs(example_env):
    example_env.load("sqlite")

    result = example_env.run("apply")

    assert result.exit_code == 0
