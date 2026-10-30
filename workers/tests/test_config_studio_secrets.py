# SPDX-License-Identifier: MPL-2.0
import pytest

from lattice_workers.config_studio_main import read_config
from lattice_workers.config_studio_mapping_proposer import model_from_env
from lattice_workers.config_studio_secrets import secret


def test_a_secret_is_read_from_the_environment_or_the_file_it_names(tmp_path):
    key = tmp_path / "key"
    key.write_text("sk-test-1 \n", encoding="utf-8")
    assert secret({"K": " sk-direct "}, "K") == "sk-direct"
    assert secret({"K_FILE": str(key)}, "K") == "sk-test-1 "  # one line ending dropped, nothing else
    key.write_text("sk-test-2\r\n", encoding="utf-8")
    assert secret({"K_FILE": str(key)}, "K") == "sk-test-2"  # read again each time, so a rotated value is used
    assert secret({}, "K") is None and secret({"K": "  "}, "K") is None


def test_a_secret_set_twice_missing_or_empty_is_refused_without_its_value(tmp_path):
    key = tmp_path / "key"
    key.write_text("sk-hidden", encoding="utf-8")
    with pytest.raises(ValueError, match="both set") as both:
        secret({"K": "sk-other", "K_FILE": str(key)}, "K")
    with pytest.raises(ValueError, match="cannot be read"):
        secret({"K_FILE": str(tmp_path / "absent")}, "K")
    (tmp_path / "empty").write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        secret({"K_FILE": str(tmp_path / "empty")}, "K")
    assert "sk-hidden" not in str(both.value) and "sk-other" not in str(both.value)


def test_the_worker_reads_its_secrets_through_files(tmp_path):
    (tmp_path / "amqp").write_text("amqp://u:p@host/%2F\n", encoding="utf-8")
    (tmp_path / "fuseki").write_text("pw\n", encoding="utf-8")
    (tmp_path / "proposer").write_text("sk-test\n", encoding="utf-8")
    config = read_config({"LATTICE_AMQP_URI_FILE": str(tmp_path / "amqp"), "LATTICE_FUSEKI_URL": "http://f",
                          "LATTICE_FUSEKI_PASSWORD_FILE": str(tmp_path / "fuseki"), "LATTICE_ROOT": str(tmp_path)})
    assert (config.amqp_uri, config.fuseki_password) == ("amqp://u:p@host/%2F", "pw")
    model = model_from_env({"LATTICE_PROPOSER_URL": "http://m", "LATTICE_PROPOSER_MODEL": "m",
                            "LATTICE_PROPOSER_KEY_FILE": str(tmp_path / "proposer")})
    assert model.key == "sk-test"
