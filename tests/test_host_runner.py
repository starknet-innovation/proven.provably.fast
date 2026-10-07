from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from proven import host_runner


class SandboxTests(unittest.TestCase):
    def test_a_bare_build_command_runs_from_the_sandbox_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            toolchain = Path(temporary) / "toolchain"
            toolchain.mkdir()
            cargo = toolchain / "cargo"
            cargo.write_text("#!/bin/sh\n")
            cargo.chmod(0o755)
            base = Path(temporary) / "request"
            base.mkdir()
            with mock.patch.object(host_runner, "TOOLCHAIN", toolchain), \
                    mock.patch.object(host_runner.subprocess, "run") as run:
                host_runner.sandboxed(base, ["cargo", "build", "--release"], False, base / "build.log")
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--") + 1:], [str(cargo), "build", "--release"])
            self.assertIn("-p", command)
            self.assertIn("PrivateNetwork=yes", command)

    def test_a_program_missing_from_the_sandbox_path_fails_before_systemd_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            with mock.patch.object(host_runner, "TOOLCHAIN", base / "none"), \
                    mock.patch.dict(os.environ, {}), \
                    mock.patch.object(host_runner.subprocess, "run") as run:
                with self.assertRaises(RuntimeError):
                    host_runner.sandboxed(base, ["no-such-builder-xyz"], False, base / "build.log")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
