"""Shared by every Tanvo tool: the client, input files, waiting and turning a run into Dify messages."""
from __future__ import annotations

import mimetypes
import time
from collections.abc import Callable, Generator, Iterable
from typing import Any

import requests
import tanvo

MAX_WAIT = 240  # seconds; a Dify plugin request is cut off at five minutes
MAX_BLOB = 25 * 1024 * 1024  # larger results are returned as links
TIMEOUT = (10, 120)
USER_AGENT = "dify-tanvo/0.0.1"


def client_for(credentials: dict[str, Any]) -> tanvo.Client:
    return tanvo.Client((credentials.get("tanvo_api_key") or "").strip() or None, timeout=60)


def friendly(e: Exception) -> str:
    """An API error as one line for the user, with what to do about the common ones."""
    if isinstance(e, tanvo.TanvoError):
        text = f"Tanvo: {e.code}: {e}"
        if e.issues:
            text += f" ({'; '.join(e.issues)})"
        if e.code == "credits":
            text += " Top up at https://tanvo.ai/pricing."
        elif e.code in ("invalid_api_key", "unauthorized"):
            text += " Check the API key in the plugin's authorization settings."
        return text
    return f"Tanvo: {e}"


def upload_files(c: tanvo.Client, files: Iterable[Any] | None) -> list[str]:
    """Dify files (photos or clips) uploaded to Tanvo, in order, as URLs a run can use. Dify's own file URLs are
    usually not reachable from the internet, so the bytes are fetched here and uploaded."""
    urls: list[str] = []
    for f in files or []:
        if f is None:
            continue
        r = requests.get(f.url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        mime = f.mime_type or mimetypes.guess_type(f.filename or "")[0] or r.headers.get("Content-Type", "").split(";")[0]
        if not mime:
            raise ValueError(f"Cannot tell the type of {f.filename or 'an input file'}.")
        urls.append(c.upload(r.content, mime=mime))
    return urls


def wait_seconds(params: dict[str, Any]) -> float:
    value = params.get("wait_seconds")
    return MAX_WAIT if value is None or value == "" else float(value)


def wait(c: tanvo.Client, g: tanvo.Generation, seconds: float, sleep: Callable[[float], None] = time.sleep) -> tanvo.Generation:
    """Polls until the run finishes or `seconds` pass; then returns the latest state (possibly still running)."""
    deadline = time.monotonic() + max(0.0, min(float(seconds), MAX_WAIT))
    every = 6 if g.kind == "video" else 3
    while not g.done and time.monotonic() + every <= deadline:
        sleep(every)
        try:
            g = c.get(g.id)
        except tanvo.ServiceError:
            pass  # one failed read is not a failed run
    return g


def summary(g: tanvo.Generation) -> dict[str, Any]:
    return {
        "generation_id": g.id,
        "status": g.status,
        "kind": g.kind,
        "model": g.model,
        "credits": g.cost,
        "error": g.error,
        "outputs": [
            {k: v for k, v in {"url": o.url, "mime": o.mime, "title": o.title, "lyrics": o.lyrics, "seconds": o.seconds, "cover": o.cover}.items() if v is not None}
            for o in g.outputs
        ],
    }


def _fetch(url: str) -> tuple[bytes | None, str | None]:
    """The file's bytes and type, or (None, None) when it is too large to hand to Dify as a file."""
    with requests.get(url, timeout=TIMEOUT, stream=True, headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        if int(r.headers.get("Content-Length") or 0) > MAX_BLOB:
            return None, None
        buf = bytearray()
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > MAX_BLOB:
                return None, None
        return bytes(buf), (r.headers.get("Content-Type") or "").split(";")[0] or None


def respond(tool: Any, g: tanvo.Generation) -> Generator[Any, None, None]:
    """A run as Dify messages: JSON and variables always; the files when it succeeded; a hint when still running."""
    data = summary(g)
    yield tool.create_json_message(data)
    yield tool.create_variable_message("generation_id", g.id)
    yield tool.create_variable_message("status", g.status)
    yield tool.create_variable_message("urls", [o.url for o in g.outputs])
    if not g.done:
        yield tool.create_text_message(
            f"Still running on Tanvo ({g.status.lower()}). Call Get Generation with generation_id {g.id} to fetch the result."
        )
        return
    if not g.succeeded:
        raise RuntimeError(f"Tanvo run {g.id} {g.status.lower()}: {g.error or 'no reason given'}. Failed runs cost nothing.")
    for i, o in enumerate(g.outputs):
        blob, mime = _fetch(o.url)
        if blob is None:
            yield tool.create_link_message(o.url)
            continue
        mime = o.mime or mime or "application/octet-stream"
        ext = mimetypes.guess_extension(mime) or ""
        yield tool.create_blob_message(blob=blob, meta={"mime_type": mime, "filename": f"tanvo-{g.id}-{i}{ext}"})
