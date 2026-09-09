import importlib.util
import io
import json
import pathlib
import sys
import unittest
from unittest import mock


def _load_module():
    module_path = pathlib.Path(__file__).resolve().parent / "claude-notify.py"
    spec = importlib.util.spec_from_file_location("claude_notify", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


claude_notify = _load_module()


class SendNotificationEncodingTests(unittest.TestCase):
    def test_send_notification_sets_utf8_content_type(self):
        message = "SingleOrDefault \u2192 FirstOrDefault"
        with mock.patch.object(claude_notify.requests, "post") as mock_post:
            mock_post.return_value = mock.Mock(status_code=200)

            claude_notify.send_notification("Title", message)

        sent = mock_post.call_args.kwargs
        headers = sent["headers"]
        self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
        self.assertEqual(sent["data"], message.encode("utf-8"))


class SubagentNotificationTests(unittest.TestCase):
    def test_detects_subagent_transcript_on_windows(self):
        payload = {
            "transcript_path": r"C:\work\.claude\projects\demo\subagents\agent-123.jsonl",
        }
        self.assertTrue(claude_notify._is_subagent_notification(payload))

    def test_root_transcript_is_not_suppressed(self):
        payload = {"transcript_path": r"C:\work\.claude\projects\demo\session.jsonl"}
        self.assertFalse(claude_notify._is_subagent_notification(payload))

    def test_direct_agent_provenance_is_suppressed(self):
        self.assertTrue(claude_notify._is_subagent_notification({"agent_id": "agent-123"}))

    def test_notification_hook_skips_subagent_side_effects(self):
        payload = {
            "notification_type": "permission_prompt",
            "message": "Agent needs approval",
            "transcript_path": "/tmp/project/subagents/agent-123.jsonl",
        }
        stdin = io.StringIO(json.dumps(payload))
        with (
            mock.patch.object(sys, "stdin", stdin),
            mock.patch.object(claude_notify, "_auto_start_server") as start_server,
            mock.patch.object(claude_notify.requests, "post") as post,
        ):
            claude_notify.run_as_hook("notification", "http://127.0.0.1:8787")

        start_server.assert_not_called()
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
