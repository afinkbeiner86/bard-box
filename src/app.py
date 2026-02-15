import json
import logging
import os
from pathlib import Path
from typing import Any, Final

import pygame
from flask import Flask, Response, jsonify, render_template, request

BASE_DIR: Final[Path] = Path(__file__).parent.parent
DATA_DIR: Final[Path] = BASE_DIR / "data"
STATIC_DIR: Final[Path] = BASE_DIR / "static"
MUSIC_DIR: Final[Path] = STATIC_DIR / "music"
ICON_DIR: Final[Path] = STATIC_DIR / "icons"
MAP_FILE: Final[Path] = DATA_DIR / "mappings.json"

APP_NAME: Final[str] = "BardBox"

app: Flask = Flask(
    __name__, static_folder=str(STATIC_DIR), template_folder=str(BASE_DIR / "templates")
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger: logging.Logger = logging.getLogger("BardBox")

for folder in [MUSIC_DIR, ICON_DIR, DATA_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

pygame.mixer.init()


def load_mappings() -> dict[str, Any]:
    """Loads slot configurations from the JSON data file."""
    if not MAP_FILE.exists():
        data: dict[str, Any] = {
            "slots": [
                {"id": i, "label": f"Slot {i}", "filename": None, "icon": None}
                for i in range(1, 9)
            ]
        }
        save_mappings(data)
        return data
    with MAP_FILE.open("r") as f:
        return json.load(f)


def save_mappings(data: dict[str, Any]) -> None:
    """Persists slot configurations to the JSON data file."""
    with MAP_FILE.open("w") as f:
        json.dump(data, f, indent=4)


@app.route("/")
def index() -> str:
    return render_template("index.html", title=APP_NAME)


@app.route("/api/data", methods=["GET"])
def get_data() -> Response:
    music_files: list[str] = [
        f.name for f in MUSIC_DIR.glob("*") if f.suffix.lower() in (".mp3", ".wav")
    ]
    icon_files: list[str] = [
        f.name
        for f in ICON_DIR.glob("*")
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    ]
    return jsonify(
        {"slots": load_mappings()["slots"], "music": music_files, "icons": icon_files}
    )


@app.route("/api/play/<filename>")
def play_music(filename: str) -> Response | tuple[Response, int]:
    path: Path = MUSIC_DIR / filename
    if path.exists():
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play(-1)
        logger.info(f"Playback started: {filename}")
        return jsonify(status="playing")
    logger.error(f"File not found: {filename}")
    return jsonify(status="error"), 404


@app.route("/api/stop")
def stop_music() -> Response:
    pygame.mixer.music.stop()
    return jsonify(status="stopped")


@app.route("/api/volume/<float:level>")
def set_volume(level: float) -> Response:
    clamped: float = max(0.0, min(1.0, level))
    pygame.mixer.music.set_volume(clamped)
    return jsonify(status="volume_set", level=clamped)


@app.route("/api/rename_asset", methods=["POST"])
def rename_asset() -> Response | tuple[Response, int]:
    data: dict[str, Any] | None = request.json
    if not data:
        return jsonify(status="error", message="No data provided"), 400

    asset_type: str = data["type"]
    folder: Path = MUSIC_DIR if asset_type == "music" else ICON_DIR
    old_path: Path = folder / data["old_name"]

    suffix: str = old_path.suffix
    new_base: str = data["new_name"]
    new_name: str = (
        new_base if new_base.lower().endswith(suffix.lower()) else new_base + suffix
    )
    new_path: Path = folder / new_name

    if old_path.exists() and not new_path.exists():
        os.rename(str(old_path), str(new_path))
        curr_map: dict[str, Any] = load_mappings()
        for s in curr_map["slots"]:
            if asset_type == "music" and s["filename"] == data["old_name"]:
                s["filename"] = new_name
            elif asset_type in ["icons", "icon"] and s["icon"] == data["old_name"]:
                s["icon"] = new_name
        save_mappings(curr_map)
        logger.info(f"Renamed {asset_type}: {data['old_name']} -> {new_name}")
        return jsonify(status="renamed")
    return jsonify(status="error", message="Path conflict or missing source"), 400


@app.route("/api/map", methods=["POST"])
def map_to_slot() -> Response:
    d: dict[str, Any] = request.json or {}
    curr: dict[str, Any] = load_mappings()
    for s in curr["slots"]:
        if s["id"] == d.get("slot_id"):
            if "filename" in d:
                s["filename"] = d["filename"]
            if "label" in d:
                s["label"] = d["label"]
            if "icon" in d:
                s["icon"] = d["icon"]
    save_mappings(curr)
    return jsonify(status="mapped")


@app.route("/api/unmap/<int:slot_id>", methods=["POST"])
def unmap(slot_id: int) -> Response:
    curr: dict[str, Any] = load_mappings()
    for s in curr["slots"]:
        if s["id"] == slot_id:
            s["filename"], s["icon"], s["label"] = None, None, f"Slot {slot_id}"
    save_mappings(curr)
    return jsonify(status="unmapped")


@app.route("/api/upload_music", methods=["POST"])
def upload_music() -> Response | tuple[Response, int]:
    file = request.files.get("file")
    if file and file.filename:
        file.save(str(MUSIC_DIR / file.filename))
        return jsonify(status="uploaded")
    return jsonify(status="error"), 400


@app.route("/api/upload_icon", methods=["POST"])
def upload_icon() -> Response | tuple[Response, int]:
    file = request.files.get("file")
    if file and file.filename:
        file.save(str(ICON_DIR / file.filename))
        return jsonify(status="uploaded")
    return jsonify(status="error"), 400


@app.route("/api/delete_asset", methods=["POST"])
def delete_asset() -> Response | tuple[Response, int]:
    d: dict[str, Any] = request.json or {}
    asset_type: str = d.get("type", "")
    folder: Path = MUSIC_DIR if asset_type == "music" else ICON_DIR
    target: Path = folder / d.get("filename", "")

    if target.exists():
        if asset_type == "music":
            pygame.mixer.music.unload()
        target.unlink()
        curr: dict[str, Any] = load_mappings()
        for s in curr["slots"]:
            if asset_type == "music" and s["filename"] == d["filename"]:
                s["filename"] = None
            if asset_type == "icons" and s["icon"] == d["filename"]:
                s["icon"] = None
        save_mappings(curr)
        logger.info(f"Deleted {asset_type}: {d['filename']}")
        return jsonify(status="deleted")
    return jsonify(status="error"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
