import json
import re
from pathlib import Path
from urllib.parse import quote

from mutagen import File


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "music-manifest.json"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}
TAG_NAMES = {
    "title": ("title", "TIT2", "INAM"),
    "artist": ("artist", "TPE1", "IART"),
    "album": ("album", "TALB", "IPRD"),
    "genre": ("genre", "TCON", "IGNR"),
    "date": ("date", "year", "TDRC", "TDOR", "TDRL", "ICRD"),
}


def tag_text(tags, names):
    if not tags:
        return None

    normalized_tags = {str(key).casefold(): value for key, value in tags.items()}
    for name in names:
        value = normalized_tags.get(name.casefold())
        if value is None:
            continue

        value = getattr(value, "text", value)
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        if value is None:
            continue

        text = str(value).strip()
        if text:
            return text

    return None


def title_from_path(path):
    title = Path(path).stem.replace("_", " ").replace("-", " ")
    title = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", title)
    return re.sub(r"\s+", " ", title).strip().capitalize()


def date_sort_key(date, path):
    if date:
        match = re.match(r"^(\d{4})(?:[-/.](\d{1,2}))?(?:[-/.](\d{1,2}))?", date)
        if match:
            year, month, day = match.groups()
            return (0, year, (month or "01").zfill(2), (day or "01").zfill(2), path)
        return (1, date.casefold(), "", "", path)
    return (2, "", "", "", path)


def build_track(path):
    relative_path = path.relative_to(ROOT).as_posix()
    audio = File(path)
    tags = audio.tags if audio else None
    track = {
        "path": relative_path,
        "src": (
            "https://raw.githubusercontent.com/joshxviii/my-music/main/tracks/"
            + "/".join(quote(part, safe="") for part in relative_path.split("/"))
        ),
        "title": tag_text(tags, TAG_NAMES["title"]) or title_from_path(relative_path),
    }

    for field in ("artist", "album", "genre", "date"):
        value = tag_text(tags, TAG_NAMES[field])
        if value:
            track[field] = value

    if audio and audio.info:
        duration = getattr(audio.info, "length", None)
        if isinstance(duration, (int, float)) and duration >= 0:
            track["durationSeconds"] = round(duration)

    return track


def main():
    paths = sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and path.suffix.casefold() in AUDIO_EXTENSIONS
            and ".git" not in path.relative_to(ROOT).parts
        ),
        key=lambda path: path.relative_to(ROOT).as_posix().casefold(),
    )
    tracks = [build_track(path) for path in paths]
    tracks.sort(key=lambda track: date_sort_key(track.get("date"), track["path"]))

    manifest = {"tracks": tracks}
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(tracks)} tracks to {OUTPUT.name}")


if __name__ == "__main__":
    main()
