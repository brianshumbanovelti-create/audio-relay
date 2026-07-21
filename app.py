import os
import subprocess
import threading
import time
import shlex
from flask import Flask, request, jsonify, Response, send_from_directory

app = Flask(__name__)

# ---- Global state (single-user tool, so simple globals are fine) ----
state = {
    "process": None,       # shell subprocess running yt-dlp | ffmpeg
    "yt_url": None,        # current YouTube URL being relayed
    "status": "stopped",   # stopped | starting | running | error
    "error": None,
    "started_at": None,
    "log_tail": [],        # last few lines of stderr from the pipeline, for debugging
}
state_lock = threading.Lock()

FIFO_PATH = "/tmp/audio_relay_fifo"
LOG_TAIL_MAX = 40


def _reader_thread(proc):
    """
    Continuously reads stderr from the yt-dlp/ffmpeg pipeline so we can
    surface real errors (bad URL, not live, geo-block, etc.) to the
    control page instead of failing silently.
    """
    try:
        for raw_line in iter(proc.stderr.readline, b""):
            line = raw_line.decode(errors="replace").rstrip()
            if not line:
                continue
            with state_lock:
                state["log_tail"].append(line)
                if len(state["log_tail"]) > LOG_TAIL_MAX:
                    state["log_tail"] = state["log_tail"][-LOG_TAIL_MAX:]
    except Exception:
        pass
    finally:
        exit_code = proc.poll()
        with state_lock:
            if state["process"] is proc and exit_code not in (None, 0, -15):
                state["status"] = "error"
                tail = "\n".join(state["log_tail"][-8:])
                state["error"] = f"Relay stopped unexpectedly (exit {exit_code}). {tail}"


def _cleanup_fifo():
    if os.path.exists(FIFO_PATH):
        try:
            os.remove(FIFO_PATH)
        except OSError:
            pass


def _start_relay(youtube_url: str):
    """
    Starts yt-dlp piping into ffmpeg, transcoding to a 32kbps MP3
    written into a named pipe (FIFO) that /stream.mp3 reads from.
    """
    _cleanup_fifo()
    os.mkfifo(FIFO_PATH)

    # yt-dlp extracts the best available audio-only stream URL, then
    # pipes raw audio into ffmpeg, which transcodes down to 32kbps CBR
    # mono MP3 -- this is the only part of the pipeline your phone
    # will ever download.
    cmd = (
        f"yt-dlp -f bestaudio -o - {shlex.quote(youtube_url)} "
        f"| ffmpeg -re -i pipe:0 -vn -ac 1 -c:a libmp3lame -b:a 32k "
        f"-f mp3 {FIFO_PATH}"
    )

    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # own process group, so we can kill cleanly
    )

    with state_lock:
        state["process"] = proc
        state["yt_url"] = youtube_url
        state["status"] = "running"
        state["error"] = None
        state["started_at"] = time.time()
        state["log_tail"] = []

    threading.Thread(target=_reader_thread, args=(proc,), daemon=True).start()


def _stop_relay():
    with state_lock:
        proc = state["process"]
        state["process"] = None
        state["status"] = "stopped"
        state["yt_url"] = None
        state["started_at"] = None

    if proc is not None:
        try:
            os.killpg(os.getpgid(proc.pid), 15)  # SIGTERM to whole group
        except ProcessLookupError:
            pass
    _cleanup_fifo()


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def status():
    with state_lock:
        return jsonify({
            "status": state["status"],
            "yt_url": state["yt_url"],
            "error": state["error"],
            "log_tail": state["log_tail"][-15:],
        })


@app.route("/api/start", methods=["POST"])
def start():
    data = request.get_json(force=True, silent=True) or {}
    youtube_url = (data.get("url") or "").strip()

    if not youtube_url:
        return jsonify({"ok": False, "error": "Paste a YouTube URL first."}), 400

    with state_lock:
        if state["status"] == "running":
            return jsonify({"ok": False, "error": "Already running. Stop it first."}), 400

    try:
        _start_relay(youtube_url)
        return jsonify({"ok": True})
    except Exception as e:
        with state_lock:
            state["status"] = "error"
            state["error"] = str(e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stop", methods=["POST"])
def stop():
    _stop_relay()
    return jsonify({"ok": True})


@app.route("/stream.mp3")
def stream():
    with state_lock:
        running = state["status"] == "running"

    if not running:
        return jsonify({"error": "Stream not running. Start it from the control page first."}), 409

    # The FIFO may exist on disk before ffmpeg has actually opened it for
    # writing. Opening it for reading blocks until a writer connects, so
    # give it a bounded amount of time rather than hanging forever if the
    # pipeline failed to start writing at all.
    waited = 0.0
    while not os.path.exists(FIFO_PATH) and waited < 15:
        time.sleep(0.5)
        waited += 0.5

    if not os.path.exists(FIFO_PATH):
        return jsonify({"error": "Stream did not start producing audio in time. Check the URL and try again."}), 504

    def generate():
        try:
            # Non-blocking open with a manual retry loop avoids hanging
            # the whole request if ffmpeg is slow to attach as a writer.
            fd = os.open(FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
            fifo = os.fdopen(fd, "rb")
            try:
                while True:
                    with state_lock:
                        still_running = state["status"] == "running"
                    if not still_running:
                        break
                    try:
                        chunk = fifo.read(4096)
                    except BlockingIOError:
                        time.sleep(0.1)
                        continue
                    if not chunk:
                        time.sleep(0.1)
                        continue
                    yield chunk
            finally:
                fifo.close()
        except Exception:
            return

    return Response(generate(), mimetype="audio/mpeg")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)
