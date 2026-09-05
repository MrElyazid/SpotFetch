import yt_dlp
import os
import shutil
import requests
import tagger
from mutagen.mp3 import MP3
from mutagen.id3._frames import APIC, TALB, TPE1, TPE2, TDRC, TIT2, TRCK, USLT
from mutagen.id3 import ID3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
import csv
import re
import typing
from rich import print


def download_from_url(
    url, format: typing.Literal["mp3", "m4a", "flac"], output_path=".",
    cookiefile=None, tag=False, acoustid_key="", lyrics=False,
):

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": format,
                "preferredquality": "0",
            },
            {
                "key": "FFmpegMetadata",
                "add_chapters": True,
                "add_metadata": True,
            },
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            },
        ],
        "embedthumbnail": True,
        "addmetadata": True,
        "verbose": False,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "cookiefile": cookiefile,
    }
    paths = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        info = ydl.extract_info(url, download=True)
        if info is None:
            return paths
        for entry in info.get("entries") or [info]:  # plain video or playlist
            if entry is None:
                continue
            path = os.path.splitext(ydl.prepare_filename(entry))[0] + f".{format}"
            if not os.path.exists(path):
                continue
            if tag:
                tagged = tagger.tag_file(path, acoustid_key, lyrics)
                if tagged:
                    print(f"[TAG] {tagged}")
                else:
                    print(f"[TAG] no MusicBrainz match for {os.path.basename(path)}")
            paths.append(path)
    return paths


def download_from_query(
    song,
    format: typing.Literal["mp3", "m4a", "flac"],
    output_path=".",
    cookiefile=None,
    platform="youtube",
):

    search_query = f"{song['track_name']} by {song['artist_name']}"

    if platform == "ytmusic":
        search_input = (
            f"https://music.youtube.com/search?q={search_query.replace(' ', '+')}"
        )
    else:
        search_input = f"ytsearch1:{search_query}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": format,
                "preferredquality": "0",
            },
            {
                "key": "FFmpegMetadata",
                "add_chapters": True,
                "add_metadata": True,
            },
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            },
        ],
        "embedthumbnail": True,
        "playlist_items": "1",
        "addmetadata": True,
        "verbose": False,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "cookiefile": cookiefile,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        ydl.download([search_input])


def sanitize_string(string: str) -> str:
    """Removes illegal characters from a filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", string)


def read_tunemymusic_csv_file(file_path: str) -> list:
    """Reads a tunemymusic CSV file and returns its content as a list"""

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} doesnt exist.")

    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        songs_list = [row for row in reader]

    for song in songs_list:
        try:
            song["track_name"] = sanitize_string(song["Track name"])
            song["artist_name"] = sanitize_string(song["Artist name"])

            del song["Track name"], song["Artist name"]

        except Exception as e:
            raise Exception(f"some error occured : {e}")

    return songs_list


def read_download_custom_csv(
    file_path: str,
    format: typing.Literal["mp3", "m4a", "flac"],
    output_path=".",
    cookiefile=None,
    platform="youtube",
) -> None:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"the file {file_path} doesnt exist.")

    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        songs_list = [row for row in reader]
    n = len(songs_list)
    for i, song in enumerate(songs_list, 1):
        try:
            song["track_name"] = sanitize_string(song["name"])
            song["artist_name"] = sanitize_string(song["artist"])

            del song["name"], song["artist"]
            print(
                f"{i}/{n} - Downloading {song['track_name']} by {song['artist_name']}"
            )
            download_from_query(song, format, output_path, cookiefile, platform)
        except Exception as e:
            print(f"{i}/{n} - Failed to download {song.get('track_name', 'Unknown')}: {e}")
            continue


def read_download_urls_txt(
    file_path: str,
    format: typing.Literal["mp3", "flac", "m4a"],
    output_path=".",
    cookiefile=None,
    tag=False,
    acoustid_key="",
    lyrics=False,
) -> None:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"the file {file_path} doesnt exist.")

    with open(file_path, mode="r", encoding="utf-8") as txt_file:
        lines = txt_file.readlines()
    n = len(lines)
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            print(f"Downloading {line} url {i}/{n}")
            download_from_url(line, format, output_path, cookiefile, tag, acoustid_key, lyrics)
        except Exception as e:
            print(f"Failed to download {line}: {e}")
            continue


EXPORTIFY_REQUIRED_COLUMNS = {
    "Track Name",
    "Artist Name(s)",
    "Album Name",
    "Album Artist Name(s)",
    "Album Release Date",
    "Album Image URL",
    "Track Duration (ms)",
}


def read_exportify_csv_file(file_path: str) -> list:
    """Reads an Exportify (.app) CSV file and returns one song dict per track."""

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        missing = EXPORTIFY_REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"unsupported CSV header, missing column(s): {', '.join(sorted(missing))}"
                " — export your playlist from https://exportify.app"
            )
        rows = list(reader)

    songs_list = []
    for row in rows:
        try:
            songs_list.append(
                {
                    "track_name": sanitize_string(row["Track Name"]),
                    "artist_names": [
                        sanitize_string(artist).strip()
                        for artist in row["Artist Name(s)"].split(",")
                    ],
                    "album_name": sanitize_string(row["Album Name"]),
                    "album_artist_names": [
                        sanitize_string(artist).strip()
                        for artist in row["Album Artist Name(s)"].split(",")
                        if artist
                    ],
                    "album_release_date": row["Album Release Date"],
                    "album_image_url": row["Album Image URL"],
                    "track_duration_ms": (
                        int(row["Track Duration (ms)"])
                        if row["Track Duration (ms)"].isdigit()
                        else 0
                    ),
                    "isrc": row.get("ISRC", ""),
                    "track_number": row.get("Track Number", ""),
                }
            )
        except Exception as e:
            raise Exception(
                f"error parsing metadata for song {row.get('Track Name', 'Unknown')}: {e}"
            )

    return songs_list


def embed_spotify_metadata_mutagen(
    audiofile, metadata, format: typing.Literal["mp3", "m4a", "flac"], cover=None,
    lyrics=None,
):
    track_number = metadata.get("track_number", "")
    try:
        if format == "mp3":
            audio = MP3(audiofile, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()

            # linter keeps crying about this
            assert audio.tags is not None

            track_name = metadata["track_name"]
            artist_names_str = ", ".join(metadata["artist_names"])

            for frame in ("COMM", "TXXX", "TCON", "TRCK", "TDRC"):  # yt-dlp junk
                audio.tags.delall(frame)
            audio.tags.add(TIT2(encoding=3, text=track_name))
            audio.tags.add(TPE1(encoding=3, text=artist_names_str))
            if metadata.get("album_name"):
                audio.tags.add(TALB(encoding=3, text=metadata["album_name"]))
            if metadata.get("album_artist_names"):
                audio.tags.add(
                    TPE2(encoding=3, text=", ".join(metadata["album_artist_names"]))
                )
            if metadata.get("album_release_date"):
                audio.tags.add(TDRC(encoding=3, text=metadata["album_release_date"]))
            if str(track_number).isdigit():
                audio.tags.add(TRCK(encoding=3, text=str(track_number)))
            if lyrics:
                audio.tags.delall("USLT")
                audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
            if cover:
                audio.tags.delall("APIC")  # drop the yt-dlp thumbnail
                audio.tags.add(
                    APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover)
                )

            audio.save()

        elif format == "m4a":
            audio = MP4(audiofile)

            if audio.tags is None:
                audio.add_tags()

            assert audio.tags is not None

            track_name = metadata["track_name"]
            artist_names_str = ", ".join(metadata["artist_names"])

            for key in ("\xa9cmt", "desc", "ldes", "\xa9gen", "trkn", "\xa9day"):  # yt-dlp junk
                audio.tags.pop(key, None)
            audio.tags["\xa9nam"] = [track_name]
            audio.tags["\xa9ART"] = [artist_names_str]
            if metadata.get("album_name"):
                audio.tags["\xa9alb"] = [metadata["album_name"]]
            if metadata.get("album_artist_names"):
                audio.tags["aART"] = [", ".join(metadata["album_artist_names"])]
            if metadata.get("album_release_date"):
                audio.tags["\xa9day"] = [metadata["album_release_date"]]
            if str(track_number).isdigit():
                audio.tags["trkn"] = [(int(track_number), 0)]
            if lyrics:
                audio.tags["\xa9lyr"] = [lyrics]
            if cover:
                audio.tags["covr"] = [MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)]

            audio.save()

        elif format == "flac":
            audio = FLAC(audiofile)

            if audio.tags is None:
                audio.add_tags()

            track_name = metadata["track_name"]
            artist_names_str = ", ".join(metadata["artist_names"])

            assert audio.tags is not None

            junk = (  # yt-dlp junk, case-insensitive: ffmpeg writes lowercase keys
                "COMMENT", "DESCRIPTION", "SYNOPSIS", "PURL", "GENRE",
                "TRACKNUMBER", "DATE",
            )
            for key in [k for k in audio.tags.keys() if k.upper() in junk]:
                del audio.tags[key]
            audio.tags["TITLE"] = [track_name]  # type: ignore
            audio.tags["ARTIST"] = [artist_names_str]  # type: ignore
            if metadata.get("album_name"):
                audio.tags["ALBUM"] = [metadata["album_name"]]  # type: ignore
            if metadata.get("album_artist_names"):
                audio.tags["ALBUMARTIST"] = [", ".join(metadata["album_artist_names"])]  # type: ignore
            if metadata.get("album_release_date"):
                audio.tags["DATE"] = [metadata["album_release_date"]]  # type: ignore
            if str(track_number).isdigit():
                audio.tags["TRACKNUMBER"] = [str(track_number)]  # type: ignore
            if lyrics:
                audio.tags["LYRICS"] = [lyrics]  # type: ignore
            if cover:
                audio.clear_pictures()  # drop the yt-dlp thumbnail
                picture = Picture()
                picture.type = 3
                picture.mime = "image/jpeg"
                picture.data = cover
                audio.add_picture(picture)
            audio.save()

    except Exception as e:
        track_name = metadata.get("track_name", "Unknown")
        print(
            f"An error occurred during metadata embedding for track {track_name}: {e}"
        )


def download_spotify_song(
    format: typing.Literal["mp3", "flac", "m4a"],
    metadata,
    output_path=".",
    cookiefile=None,
    platform="youtube",
    tolerance=2,
    tag=False,
    acoustid_key="",
    lyrics=False,
):
    if metadata is None:
        print("no song metadata, skipping song...")
        return

    duration_ms = metadata["track_duration_ms"]

    duration_s = duration_ms * 0.001  # type: ignore

    tolerance_s = tolerance * 60

    def check_duration(info, *, incomplete):
        duration = info.get("duration")
        if duration is None:
            return None

        if abs(duration - duration_s) > tolerance_s:

            with open(
                os.path.join(output_path, "failed.txt"), "a", encoding="utf-8"
            ) as f:
                f.write(f"{search_query}\n")

            raise Exception(
                f"[FAIL]Duration mismatch: got {duration}s, expected {duration_s}s"
            )

        return None  # allow download

    # metadata
    track_name = metadata.get("track_name", "Unknown Track")
    artist_names = metadata.get("artist_names", ["Unknown Artist"])
    artist_names_str = ", ".join(artist_names)

    # final naming
    final_audio_file_path = os.path.join(
        output_path, f"{track_name} - {artist_names_str}.{format}"
    )

    if os.path.exists(final_audio_file_path):
        print(f"File {final_audio_file_path} already exists. Skipping download.")
        return

    search_query = f"{track_name} by {artist_names}"

    if platform == "ytmusic":
        search_input = (
            f"https://music.youtube.com/search?q={search_query.replace(' ', '+')}"
        )
    else:
        search_input = f"ytsearch1:{search_query}"

    temp_filename = f"{track_name} - {artist_names_str}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_path, f"{temp_filename}.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": format,
                "preferredquality": "0",
            },
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            },
        ],
        "verbose": False,
        "playlist_items": "1",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "cookiefile": cookiefile,
        "writethumbnail": True,
        "match_filter": check_duration,
    }

    # audio download
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
            ydl.download([search_input])

        downloaded_file_path = os.path.join(output_path, f"{temp_filename}.{format}")

        if not os.path.exists(downloaded_file_path):
            raise Exception(
                f"Expected downloaded file not found at {downloaded_file_path}"
            )

    except Exception as e:
        raise Exception(
            f"\nAn error occurred during audio download for the track {track_name}: {e}"
        )

    # embedding metadata and album image
    if downloaded_file_path and os.path.exists(downloaded_file_path):
        cover = download_album_cover(metadata.get("album_image_url"), track_name)
        lyrics_text = lyrics.fetch(
            artist=(metadata.get("artist_names") or [""])[0],
            track=metadata["track_name"],
            album=metadata.get("album_name"),
            duration_s=metadata.get("track_duration_ms", 0) / 1000,
        ) if lyrics else None
        embed_spotify_metadata_mutagen(
            downloaded_file_path, metadata, format, cover, lyrics_text
        )

        if os.path.exists(downloaded_file_path):
            shutil.move(downloaded_file_path, final_audio_file_path)

    # optional MusicBrainz re-tagging (overrides spotify tags when it identifies)
    if tag and os.path.exists(final_audio_file_path):
        tagged = tagger.tag_file(final_audio_file_path, acoustid_key, lyrics)
        if tagged:
            print(f"[TAG] {tagged}")
        else:
            print(f"[TAG] no MusicBrainz match, kept spotify metadata")


def download_album_cover(image_url, track_name):
    """Fetches the spotify album cover bytes, or None on failure."""
    if not image_url:
        return None
    try:
        r = requests.get(image_url, timeout=30)
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        print(f"WARNING : error downloading album cover for {track_name}: {e}")
        return None
