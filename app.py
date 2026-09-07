import os
import re
import uuid
import shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

ALLOWED_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}

def is_valid_tiktok_url(url):
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    pattern = r"^https?://([a-zA-Z0-9.-]+\.)?tiktok\.com/"

    return bool(re.match(pattern, url))


def safe_filename(filename):
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    return filename[:150] or "video.mp4"


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/download")
def download_video():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not is_valid_tiktok_url(url):
        return jsonify({
            "ok": False,
            "error": "Please enter a valid TikTok URL."
        }), 400

    job_id = uuid.uuid4().hex
    job_dir = DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        import yt_dlp

        output_template = str(job_dir / "%(title).100s.%(ext)s")

        options = {
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
            "merge_output_format": "mp4",
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        files = list(job_dir.glob("*"))

        video_files = [
            f for f in files
            if f.is_file() and f.suffix.lower() in {
                ".mp4", ".webm", ".mkv", ".mov"
            }
        ]

        if not video_files:
            raise RuntimeError("No video file was produced.")

        video_file = video_files[0]

        if video_file.stat().st_size > MAX_FILE_SIZE:
            raise RuntimeError("Video is larger than the 200 MB limit.")

        filename = safe_filename(video_file.name)

        final_file = job_dir / filename

        if video_file != final_file:
            video_file.rename(final_file)

        return jsonify({
            "ok": True,
            "job_id": job_id,
            "filename": filename,
            "download_url": f"/api/file/{job_id}/{filename}"
        })

    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)

        return jsonify({
            "ok": False,
            "error": "Unable to download this video. Make sure the video is publicly accessible and the URL is correct."
        }), 500


@app.get("/api/file/<job_id>/<filename>")
def get_file(job_id, filename):
    job_dir = DOWNLOAD_DIR / job_id

    if not job_dir.exists():
        return jsonify({
            "ok": False,
            "error": "File expired or no longer exists."
        }), 404

    requested_file = job_dir / filename

    try:
        requested_file.resolve().relative_to(job_dir.resolve())
    except ValueError:
        return jsonify({
            "ok": False,
            "error": "Invalid file path."
        }), 400

    if not requested_file.exists() or not requested_file.is_file():
        return jsonify({
            "ok": False,
            "error": "File not found."
        }), 404

    return send_file(
        requested_file,
        as_attachment=True,
        download_name=requested_file.name
    )


@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "ok": False,
        "error": "Request is too large."
    }), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
