"""Runs every tool through the real dify_plugin Tool classes against a fake Tanvo API:
python -m unittest discover -s tests   (with requirements.txt installed)"""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# dify_plugin patches threading and sockets (gevent) on import, so it comes before the fake server starts.
from dify_plugin.entities.tool import ToolInvokeMessage, ToolRuntime  # noqa: E402
from dify_plugin.errors.tool import ToolProviderCredentialValidationError  # noqa: E402
from dify_plugin.file.file import File  # noqa: E402

from provider.tanvo import TanvoProvider  # noqa: E402
from tools import common  # noqa: E402
from tools.generate_image import GenerateImageTool  # noqa: E402
from tools.generate_song import GenerateSongTool  # noqa: E402
from tools.generate_video import GenerateVideoTool  # noqa: E402
from tools.get_generation import GetGenerationTool  # noqa: E402
from tools.list_apps import ListAppsTool  # noqa: E402
from tools.run_app import RunAppTool  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
MP4 = b"\0\0\0\x18ftypmp42" + b"\0" * 64
MP3 = b"ID3" + b"\0" * 64
MODELS = [
    {"id": "nano-banana-2", "kind": "image", "name": "Nano Banana 2", "free_tier": False, "inputs": ["text", "image"],
     "options": {"aspect": ["1:1", "16:9"]}, "defaults": {"aspect": "1:1", "resolution": "1K"}, "credits_at_defaults": 8, "prompt_max_chars": 4000},
    {"id": "veo-3-1", "kind": "video", "name": "Veo 3.1", "free_tier": False, "inputs": ["text", "image"],
     "options": {"tier": ["Lite", "Quality"]}, "defaults": {"tier": "Lite", "duration": 6}, "credits_at_defaults": 60, "prompt_max_chars": 4000},
    {"id": "suno-v6", "kind": "music", "name": "Suno V6", "free_tier": False, "inputs": ["text"], "options": {}, "defaults": {}, "credits_at_defaults": 20, "prompt_max_chars": 4000},
]
APPS = [{
    "slug": "ai-pet-portrait-generator", "kind": "image", "name": "Pet Portrait Generator", "description": "A painted portrait.", "category": "Pets",
    "model": "nano-banana-2", "url": "https://tanvo.ai/image/ai-pet-portrait-generator",
    "inputs": [{"id": "in1", "label": "Pet photo", "accept": "image/*", "min": 1, "max": 1}],
    "looks": [{"id": "renaissance", "name": "Renaissance oil", "prompt": "Paint the pet as a Renaissance oil portrait.", "model": "nano-banana-2", "options": {}},
              {"id": "royal", "name": "Royal", "prompt": "Paint the pet as a monarch.", "model": "nano-banana-2", "options": {"aspect": "1:1"}}],
}]


class Fake:
    def reset(self):
        self.submissions, self.uploads, self.runs = [], {}, {}
        self.polls_needed = 1
        self.fail_with = None


FAKE = Fake()
FAKE.reset()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, status, body: bytes, mime="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def js(self, status, payload):
        self.send(status, json.dumps(payload).encode())

    @property
    def base(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def authed(self):
        if self.headers.get("Authorization") != "Bearer sk_good":
            self.js(401, {"error": "invalid_api_key", "message": "That API key is invalid or has been revoked."})
            return False
        return True

    def do_GET(self):
        p = self.path
        if p.startswith("/dify-files/"):
            return self.send(200, PNG if p.endswith(".png") else MP4, "image/png" if p.endswith(".png") else "video/mp4")
        if p.startswith("/out/"):
            name = p.rsplit("/", 1)[1]
            return self.send(200, {"png": PNG, "mp4": MP4, "mp3": MP3}[name.rsplit(".", 1)[1]],
                             {"png": "image/png", "mp4": "video/mp4", "mp3": "audio/mpeg"}[name.rsplit(".", 1)[1]])
        if p == "/api/v1/models":
            return self.js(200, {"models": MODELS})
        if p == "/api/v1/apps":
            return self.js(200, {"apps": APPS})
        if not self.authed():
            return
        if p == "/api/v1/me":
            return self.js(200, {"tier": "paid", "credits": 100, "watermarked": False, "concurrency": 2})
        if p.startswith("/api/v1/generations/"):
            run = FAKE.runs.get(p.rsplit("/", 1)[1])
            if run is None:
                return self.js(404, {"error": "not_found", "message": "No such generation."})
            run["polls"] += 1
            g = dict(run["g"])
            if run["polls"] >= FAKE.polls_needed:
                g.update(run["final"])
            return self.js(200, {"generation": g})
        self.js(404, {"error": "not_found", "message": p})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if not self.authed():
            return
        if self.path == "/api/v1/uploads":
            uid = uuid.uuid4().hex
            FAKE.uploads[uid] = {"mime": body["mime"]}
            return self.js(200, {"upload_url": f"{self.base}/put/{uid}", "url": f"https://media.example/uploads/{uid}"})
        if self.path == "/api/v1/generations":
            FAKE.submissions.append(body)
            gid = f"g{len(FAKE.runs) + 1}"
            ext = {"image": "png", "video": "mp4", "music": "mp3"}[body["kind"]]
            outs = [{"url": f"{self.base}/out/{gid}-{i}.{ext}", "mime": {"png": "image/png", "mp4": "video/mp4", "mp3": "audio/mpeg"}[ext],
                     **({"title": f"Take {i + 1}", "lyrics": "la la"} if ext == "mp3" else {})} for i in range(2 if ext == "mp3" else 1)]
            final = {"status": "SUCCEEDED", "outputs": outs} if not FAKE.fail_with else {"status": "FAILED", "error": FAKE.fail_with}
            g = {"id": gid, "kind": body["kind"], "model": body["model"], "prompt": body["prompt"], "options": body.get("options") or {},
                 "cost": 8, "status": "PROCESSING", "error": None, "createdAt": 0, "outputs": []}
            FAKE.runs[gid] = {"g": g, "final": final, "polls": 0}
            return self.js(201, {"generation": g})
        self.js(404, {"error": "not_found", "message": self.path})

    def do_PUT(self):
        uid = self.path.rsplit("/", 1)[1]
        FAKE.uploads[uid]["bytes"] = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        FAKE.uploads[uid]["content_type"] = self.headers.get("Content-Type")
        self.send(200, b"", "text/plain")


SERVER = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=SERVER.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{SERVER.server_address[1]}"
os.environ["TANVO_BASE_URL"] = BASE


M = ToolInvokeMessage.MessageType


def dify_file(name: str, mime: str) -> dict:
    """A file parameter as Dify sends it; Tool.invoke turns it into a File."""
    return File(url=f"{BASE}/dify-files/{name}", mime_type=mime, filename=name, type="image" if mime.startswith("image") else "video").model_dump()


def run(tool_cls, params, key="sk_good"):
    tool = tool_cls(runtime=ToolRuntime(credentials={"tanvo_api_key": key}, user_id="u", session_id="s"), session=mock.Mock())
    with mock.patch.object(common.time, "sleep", lambda s: None):
        return list(tool.invoke(params))


def of(messages, kind):
    return [m for m in messages if m.type == kind]


def variables(messages):
    return {m.message.variable_name: m.message.variable_value for m in of(messages, M.VARIABLE)}


class Tools(unittest.TestCase):
    def setUp(self):
        FAKE.reset()

    def test_credentials_are_checked_with_a_free_call(self):
        TanvoProvider()._validate_credentials({"tanvo_api_key": "sk_good"})
        with self.assertRaisesRegex(ToolProviderCredentialValidationError, "invalid_api_key"):
            TanvoProvider()._validate_credentials({"tanvo_api_key": "sk_bad"})
        with self.assertRaisesRegex(ToolProviderCredentialValidationError, "Enter your Tanvo API key"):
            TanvoProvider()._validate_credentials({"tanvo_api_key": " "})
        self.assertEqual(FAKE.submissions, [])

    def test_image_uploads_dify_files_and_returns_a_dify_file(self):
        msgs = run(GenerateImageTool, {"prompt": "combine them", "model": "nano-banana-2", "aspect": "16:9", "resolution": "auto", "format": "auto",
                                       "images": [dify_file("a.png", "image/png"), dify_file("b.png", "image/png")], "wait_seconds": 60})
        body = FAKE.submissions[-1]
        self.assertEqual(body["options"]["aspect"], "16:9")
        self.assertEqual(body["options"]["resolution"], "1K")  # "auto" leaves the model default
        self.assertEqual(len(body["imageUrls"]), 2)
        self.assertTrue(all(u["content_type"] == "image/png" and u["bytes"] == PNG for u in FAKE.uploads.values()))
        blobs = of(msgs, M.BLOB)
        self.assertEqual(len(blobs), 1)
        self.assertEqual(blobs[0].meta["mime_type"], "image/png")
        self.assertTrue(blobs[0].meta["filename"].endswith(".png"))
        v = variables(msgs)
        self.assertEqual(v["status"], "SUCCEEDED")
        self.assertEqual(len(v["urls"]), 1)
        self.assertEqual(of(msgs, M.JSON)[0].message.json_object["credits"], 8)

    def test_slow_video_returns_its_id_then_get_generation_fetches_it(self):
        FAKE.polls_needed = 3
        msgs = run(GenerateVideoTool, {"prompt": "a lighthouse", "model": "veo-3-1", "tier": "Quality", "aspect": "auto", "resolution": "auto",
                                       "duration": 8, "audio": "off", "start_image": dify_file("s.png", "image/png"), "wait_seconds": 0})
        body = FAKE.submissions[-1]
        self.assertEqual((body["options"]["tier"], body["options"]["duration"], body["options"]["audio"]), ("Quality", 8, False))
        self.assertEqual(len(body["imageUrls"]), 1)
        v = variables(msgs)
        self.assertEqual(v["status"], "PROCESSING")
        self.assertIn("Get Generation", of(msgs, M.TEXT)[0].message.text)
        self.assertEqual(of(msgs, M.BLOB), [])
        done = run(GetGenerationTool, {"generation_id": v["generation_id"], "wait_seconds": 120})
        self.assertEqual(variables(done)["status"], "SUCCEEDED")
        self.assertEqual(of(done, M.BLOB)[0].meta["mime_type"], "video/mp4")

    def test_audio_auto_sends_nothing(self):
        run(GenerateVideoTool, {"prompt": "a fox", "model": "veo-3-1", "audio": "auto", "tier": "auto", "wait_seconds": 30})
        self.assertNotIn("audio", FAKE.submissions[-1]["options"])
        self.assertEqual(FAKE.submissions[-1]["options"]["tier"], "Lite")

    def test_song_returns_both_takes(self):
        msgs = run(GenerateSongTool, {"prompt": "a birthday song for Ana", "mode": "Describe", "style": "acoustic pop", "title": "", "wait_seconds": 60})
        body = FAKE.submissions[-1]
        self.assertEqual((body["options"]["tier"], body["options"]["style"]), ("Describe", "acoustic pop"))
        self.assertEqual([b.meta["mime_type"] for b in of(msgs, M.BLOB)], ["audio/mpeg", "audio/mpeg"])
        self.assertEqual(of(msgs, M.JSON)[0].message.json_object["outputs"][0]["lyrics"], "la la")

    def test_app_uses_the_look_and_details(self):
        run(RunAppTool, {"app": "ai-pet-portrait-generator", "look": "royal", "photos": [dify_file("rex.png", "image/png")], "details": "Rex"})
        body = FAKE.submissions[-1]
        self.assertTrue(body["prompt"].startswith("Paint the pet as a monarch."))
        self.assertIn("Rex", body["prompt"])
        self.assertEqual(len(body["imageUrls"]), 1)

    def test_app_errors_point_to_list_apps(self):
        with self.assertRaisesRegex(RuntimeError, "List Apps"):
            run(RunAppTool, {"app": "no-such-app", "photos": []})
        with self.assertRaisesRegex(RuntimeError, "needs 1 photo"):
            run(RunAppTool, {"app": "ai-pet-portrait-generator", "photos": []})

    def test_list_apps(self):
        msgs = run(ListAppsTool, {"kind": "image"})
        row = of(msgs, M.JSON)[0].message.json_object["apps"][0]
        self.assertEqual(row["app"], "ai-pet-portrait-generator")
        self.assertEqual([l["look"] for l in row["looks"]], ["renaissance", "royal"])
        self.assertEqual(row["photos"], [{"label": "Pet photo", "required": True, "max": 1}])

    def test_failed_run_and_bad_key_raise(self):
        FAKE.fail_with = "moderation"
        with self.assertRaisesRegex(RuntimeError, "failed: moderation"):
            run(GenerateImageTool, {"prompt": "x", "model": "nano-banana-2"})
        with self.assertRaisesRegex(RuntimeError, "Check the API key"):
            run(GenerateImageTool, {"prompt": "x"}, key="sk_bad")

    def test_large_results_come_back_as_links(self):
        with mock.patch.object(common, "MAX_BLOB", 10):
            msgs = run(GenerateImageTool, {"prompt": "x", "model": "nano-banana-2"})
        self.assertEqual(of(msgs, M.BLOB), [])
        self.assertTrue(of(msgs, M.LINK)[0].message.text.endswith(".png"))


if __name__ == "__main__":
    unittest.main()
