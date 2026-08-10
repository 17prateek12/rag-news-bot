import json
import uuid
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def multipart_upload(path: str, token: str, filename: str, content_type: str, data: bytes) -> tuple[int, dict | str]:
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def main() -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(BASE + "/speech/transcribe", method="POST"), timeout=10)
    except urllib.error.HTTPError as exc:
        print("no_auth", exc.code)

    login = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                BASE + "/auth/login",
                data=json.dumps({"email": "user@test.com", "password": "password123"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=30,
        ).read()
    )
    token = login["access_token"]

    code, payload = multipart_upload("/speech/transcribe", token, "empty.webm", "audio/webm", b"")
    print("empty_audio", code, payload)

    code, payload = multipart_upload("/speech/transcribe", token, "x.txt", "text/plain", b"hello")
    print("bad_mime", code, payload)

    sample_url = "https://storage.googleapis.com/cloud-samples-data/generative-ai/audio/pixel.mp3"
    audio_bytes = urllib.request.urlopen(sample_url, timeout=60).read()
    print("sample_bytes", len(audio_bytes))

    code, payload = multipart_upload("/speech/transcribe", token, "pixel.mp3", "audio/mpeg", audio_bytes)
    print("transcribe", code)
    if isinstance(payload, dict):
        print("model", payload.get("model"))
        print("text_preview", (payload.get("text") or "")[:160])

    session = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                BASE + "/chat/sessions",
                data=b"{}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST",
            ),
            timeout=30,
        ).read()
    )
    sid = session["id"]

    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="pixel.mp3"\r\n'
        f"Content-Type: audio/mpeg\r\n\r\n"
    ).encode() + audio_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="limit"\r\n\r\n'
        f"3\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/chat/sessions/{sid}/messages/audio",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            out = json.loads(resp.read())
            print("chat_audio", resp.status, out.get("input_mode"), out.get("transcript", "")[:100])
    except urllib.error.HTTPError as exc:
        print("chat_audio_fail", exc.code, exc.read().decode()[:500])


if __name__ == "__main__":
    main()
