from ezmig.adapters import create_adapter
from ezmig.adapters.oracle import OracleAdapter


def test_create_oracle_adapter_with_credentials_in_url():
    adapter = create_adapter("oracle://system:oracle@localhost:1521/?service_name=XEPDB1")

    assert isinstance(adapter, OracleAdapter)
    assert adapter.url == "oracle://system:oracle@localhost:1521/?service_name=XEPDB1"


def test_create_oracle_adapter_with_path_service_name():
    adapter = create_adapter("oracle://scott:tiger@dbhost:1521/XEPDB1")

    assert isinstance(adapter, OracleAdapter)
    assert adapter.url == "oracle://scott:tiger@dbhost:1521/XEPDB1"


def test_create_oracle_adapter_with_legacy_dsn():
    adapter = create_adapter("oracle://system/oracle@localhost:1521/XEPDB1")

    assert isinstance(adapter, OracleAdapter)
    assert adapter.url == "oracle://system/oracle@localhost:1521/XEPDB1"
