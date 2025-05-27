import os
import pytest
from click.testing import CliRunner
from crdb_schema_exporter.exporter import write_file, diff_schemas, archive_output, main


@pytest.fixture
def sample_files(tmp_path):
    file1 = tmp_path / "file1.sql"
    file2 = tmp_path / "file2.sql"
    file1.write_text("CREATE TABLE test (id INT);")
    file2.write_text("CREATE TABLE test (id INT);")
    return str(file1), str(file2)


def test_write_file(tmp_path):
    filepath = tmp_path / "sample.txt"
    content = "This is a test."
    write_file(filepath, content)
    assert filepath.read_text() == content


def test_diff_schemas_no_diff(sample_files):
    file1, file2 = sample_files
    diff = diff_schemas(file1, file2)
    assert diff == ''


def test_archive_output(tmp_path):
    test_dir = tmp_path / "to_archive"
    test_dir.mkdir()
    test_file = test_dir / "file.txt"
    test_file.write_text("data")
    archive_output(str(test_dir))
    archive_path = str(test_dir) + ".tar.gz"
    assert os.path.exists(archive_path)


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_cli_missing_db():
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert "--db" in result.output
