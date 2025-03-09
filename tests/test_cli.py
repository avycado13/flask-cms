# import pytest
# from flask.testing import CliRunner
# from flask import current_app

# def test_translate(runner: CliRunner, app):
#     with app.app_context():
#         result = runner.invoke(current_app.cli, args=["translate", "init", "en"])
#         # assert result.exit_code == 0
#         assert b"creating" in result.stdout_bytes
#         assert "en" in result.stdout
