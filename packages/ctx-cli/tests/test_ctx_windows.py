import importlib.util
import importlib.machinery
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CTX_ROUTE = ROOT / "bin" / "ctx-route"
CTX_CODEX = ROOT / "bin" / "ctx-codex-bridge"
CTX_WIN_AGENT = ROOT / "bin" / "ctx-win-agent"
CTX_STUB_AGENT = ROOT / "bin" / "ctx-stub-agent"


def load_script(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class WindowsExtensionTests(unittest.TestCase):
    def run_route(self, base, *args, input_obj=None, check=True):
        env = {**os.environ, "CTX_BASE": str(base)}
        data = json.dumps(input_obj) if input_obj is not None else None
        result = subprocess.run(
            [sys.executable, str(CTX_ROUTE), *args],
            input=data,
            text=True,
            capture_output=True,
            env=env,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_ctx_codex_parses_verdict_block(self):
        module = load_script(CTX_CODEX, "ctx_codex_under_test")
        parsed = module.parse_verdict_block(
            "work output\n"
            "CTX-VERDICT: success\n"
            "CTX-ARTIFACTS: /tmp/a.json, /tmp/b.txt\n"
            "CTX-RESIDUAL: none\n"
        )
        self.assertEqual(parsed["status"], "replied")
        self.assertEqual(parsed["verdict"], "success")
        self.assertEqual(parsed["residual"], "none")
        self.assertEqual([item["path"] for item in parsed["artifacts"]], ["/tmp/a.json", "/tmp/b.txt"])

    def test_ctx_win_agent_profile_is_neutral_and_eligible(self):
        module = load_script(CTX_WIN_AGENT, "ctx_win_agent_under_test")
        profile = module.agent_profile()
        self.assertEqual(profile["schema"], "ctx-agent-profile-v1")
        self.assertEqual(profile["device_id"], "windows-local")
        self.assertIn("os.windows", profile["capabilities"])
        self.assertIn("runtime.codex", profile["capabilities"])
        self.assertEqual(profile["audit_profile"]["result_link_kind"], "ctx-codex-result")
        route = {
            "target_site": "windows-local",
            "status": "queued",
            "required_capabilities": ["os.windows", "runtime.codex"],
            "constraints": ["read_only_first", "no_secrets"],
            "approval_required": False,
            "secret_capabilities": [],
        }
        self.assertTrue(module.route_eligible(route))
        route["required_capabilities"] = ["os.macos"]
        self.assertFalse(module.route_eligible(route))

    def test_ctx_win_agent_remote_transport_can_be_injected(self):
        with mock.patch.dict(
            os.environ,
            {
                "CTX_REMOTE": "ctx-ledger@example.invalid",
                "CTX_TRANSPORT": "frp-reverse-ssh:127.0.0.1:6023",
            },
        ):
            module = load_script(CTX_WIN_AGENT, "ctx_win_agent_remote_under_test")
            self.assertEqual(module.device_profile()["transports"], ["frp-reverse-ssh:127.0.0.1:6023"])
            self.assertEqual(module.agent_profile()["transports"], ["frp-reverse-ssh:127.0.0.1:6023"])

    def test_ctx_win_agent_publish_creates_windows_origin_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ctx"
            env = {
                **os.environ,
                "CTX_BASE": str(base),
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(CTX_WIN_AGENT),
                    "publish",
                    "--route-id",
                    "route_from_windows",
                    "--target-site",
                    "lingxiaodian",
                    "--target-agent",
                    "codex",
                    "--title-original",
                    "Windows origin route",
                    "--capability",
                    "os.linux,runtime.codex",
                    "--constraint",
                    "read_only_first,no_secrets",
                    "--instructions",
                    "Return a metadata-first status.",
                ],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            created = json.loads(result.stdout)
            route = json.loads(self.run_route(base, "show", "route_from_windows").stdout)
            self.assertEqual(created["route_id"], "route_from_windows")
            self.assertEqual(route["origin_site"], "windows-local")
            self.assertEqual(route["origin_agent"], "windows-local:codex-local")
            self.assertEqual(route["target_site"], "lingxiaodian")
            self.assertEqual(route["target_agent"], "codex")

    def test_ctx_stub_agent_demo_closes_route_without_external_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ctx"
            env = {
                **os.environ,
                "CTX_BASE": str(base),
                "CTX_DEVICE_ID": "demo-local",
                "CTX_AGENT_ID": "demo-local:stub",
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(CTX_STUB_AGENT),
                    "demo",
                    "--route-id",
                    "route_stub_demo_test",
                ],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            route = json.loads(self.run_route(base, "show", "route_stub_demo_test").stdout)
            self.assertEqual(payload["route_id"], "route_stub_demo_test")
            self.assertEqual(route["status"], "replied")
            self.assertEqual(route["reply"]["executed_by"], "demo-local:stub")
            self.assertEqual(route["reply"]["evidence"][0]["kind"], "ctx-stub-result")

    def test_ctx_stub_agent_only_advertises_stub_capability(self):
        module = load_script(CTX_STUB_AGENT, "ctx_stub_agent_under_test")
        self.assertEqual(module.agent_profile()["capabilities"], ["runtime.stub", "ctx.route"])
        self.assertNotIn("runtime.shell", module.agent_profile()["capabilities"])
        self.assertNotIn("probe.read-only", module.agent_profile()["capabilities"])

    def test_ctx_codex_run_writes_result_with_stub_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ctx"
            stub = Path(tmp) / "codex-stub.py"
            stub.write_text(
                textwrap.dedent(
                    """\
                    import sys
                    print("stub received", sys.argv[1])
                    print("CTX-VERDICT: success")
                    print("CTX-ARTIFACTS: none")
                    print("CTX-RESIDUAL: none")
                    """
                ),
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "CTX_BASE": str(base),
                "CODEX_CMD": f"{sys.executable} {stub}",
            }
            result = subprocess.run(
                [sys.executable, str(CTX_CODEX), "run", "--task", "hello", "--task-id", "task:stub"],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertNotIn(":", Path(payload["result_path"]).name)
            record = json.loads(Path(payload["result_path"]).read_text(encoding="utf-8"))
            self.assertEqual(record["kind"], "ctx-codex-result")
            self.assertEqual(record["task_id"], "task:stub")
            self.assertEqual(record["status"], "replied")

    def test_ctx_win_agent_once_closes_local_route_with_stub_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ctx"
            stub = Path(tmp) / "ctx-codex-stub.py"
            stub.write_text(
                textwrap.dedent(
                    """\
                    import argparse, json, os
                    from pathlib import Path
                    parser = argparse.ArgumentParser()
                    sub = parser.add_subparsers(dest="cmd", required=True)
                    run = sub.add_parser("run")
                    run.add_argument("--task", required=True)
                    run.add_argument("--task-id", required=True)
                    args = parser.parse_args()
                    out = Path(os.environ["CTX_BASE"]) / "done" / (args.task_id + ".json")
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps({"kind":"ctx-codex-result","task_id":args.task_id,"status":"replied"}) + "\\n", encoding="utf-8")
                    print(json.dumps({"task_id": args.task_id, "status": "replied", "result_path": str(out)}))
                    """
                ),
                encoding="utf-8",
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_windows_once",
                "--target-site",
                "windows-local",
                "--target-agent",
                "local-codex",
                "--title-original",
                "Windows local codex drill",
                "--capability",
                "os.windows,runtime.codex",
            )
            env = {
                **os.environ,
                "CTX_BASE": str(base),
                "CTX_CODEX": f"{sys.executable} {stub}",
            }
            result = subprocess.run(
                [sys.executable, str(CTX_WIN_AGENT), "once"],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            route = json.loads(self.run_route(base, "show", "route_windows_once").stdout)
            self.assertEqual(route["status"], "replied")
            self.assertEqual(route["reply"]["executed_by"], "windows-local:codex-local")
            self.assertEqual(route["lease"]["agent_profile_schema"], "ctx-agent-profile-v1")
            self.assertEqual(route["lease"]["audit_profile_snapshot"]["result_link_kind"], "ctx-codex-result")


if __name__ == "__main__":
    unittest.main()
