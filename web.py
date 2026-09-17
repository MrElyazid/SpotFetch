"""Minimal Flask web UI for SpotFetch: trigger a download by URL, saved on the host.

One download runs at a time; each is a background job the page polls.
"""

import threading
import uuid

import files.config as config
import files.functions as functions
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DEFAULTS = {
    "format": "mp3",
    "output_path": ".",
    "cookie_file": None,
    "tag_youtube": True,
    "acoustid_key": "",
    "lyrics": False,
}
settings = dict(DEFAULTS)
settings.update(config.load_settings())

FORMATS = ("mp3", "m4a", "flac")
JOB_KEEP = 10

_jobs = {}            # job id -> Job
_jobs_lock = threading.Lock()


class Job:
    def __init__(self, url, fmt, tag, lyrics):
        self.id = uuid.uuid4().hex[:8]
        self.url = url
        self.fmt = fmt
        self.tag = tag
        self.lyrics = lyrics
        self.status = "running"
        self.files = []
        self.error = None


def _prune_jobs():
    running = [j for j in _jobs.values() if j.status == "running"]
    done = [j for j in _jobs.values() if j.status != "running"]
    _jobs.clear()
    for j in running + done[-JOB_KEEP:]:
        _jobs[j.id] = j


def _downloader(job):
    try:
        paths = functions.download_from_url(
            job.url, job.fmt, settings["output_path"], settings["cookie_file"],
            job.tag, settings["acoustid_key"], job.lyrics,
        )
        with _jobs_lock:
            job.status = "done" if paths else "error"
            job.error = None if paths else "no files produced"
            job.files = paths
    except Exception as e:
        with _jobs_lock:
            job.status = "error"
            job.error = str(e)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    fmt = data.get("format", settings["format"])
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "url must start with http(s)://"}), 400
    if fmt not in FORMATS:
        return jsonify({"error": f"format must be one of {FORMATS}"}), 400

    with _jobs_lock:
        if any(j.status == "running" for j in _jobs.values()):
            return jsonify({"error": "a download is already running"}), 409
        _prune_jobs()
        job = Job(url, fmt, bool(data.get("tag", settings["tag_youtube"])),
                  bool(data.get("lyrics", settings["lyrics"])))
        _jobs[job.id] = job
    threading.Thread(target=_downloader, args=(job,), daemon=True).start()
    return jsonify({"job_id": job.id}), 201


@app.get("/jobs/<job_id>")
def job(job_id):
    j = _jobs.get(job_id)
    if j is None:
        return jsonify({"error": "unknown job"}), 404
    return jsonify({"status": j.status, "files": j.files, "error": j.error})


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8021")), threaded=True)
