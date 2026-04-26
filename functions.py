import yt_dlp
import os
import shutil
from mutagen.mp3 import MP3
from mutagen.id3._frames import TALB, TPE1, TPE2, TDRC, TIT2
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
import csv
import re
import typing
from rich import print


def download_from_url(
    url, format: typing.Literal["mp3", "m4a", "flac"], output_path=".", cookiefile=None
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
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        ydl.download([url])


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
) -> None:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} doesnt exist.")

    with open(file_path, mode="r", encoding="utf-8") as txt_file:
        lines = txt_file.readlines()
    n = len(lines)
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            print(f"Downloading {line} url {i}/{n}")
            download_from_url(line, format, output_path, cookiefile)
        except Exception as e:
            print(f"Failed to download {line}: {e}")
            continue


def read_exportify_csv_file(file_path: str) -> list:
    """Reads an Exportify CSV file and returns its content as a list of dictionaries."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        songs_list = [row for row in reader]

    for song in songs_list:
        try:
            song["track_name"] = sanitize_string(song["Track Name"])
            song["artist_names"] = [
                sanitize_string(artist) for artist in song["Artist Name(s)"].split(",")
            ]
            song["album_name"] = sanitize_string(song["Album Name"])
            song["album_release_date"] = song["Release Date"]
            song["track_duration_ms"] = (
                int(song["Duration (ms)"]) if song["Duration (ms)"].isdigit() else 0
            )
            song["genres"] = sanitize_string(song["Genres"])
            keys_to_remove = [
                "Track Name",
                "Album Name",
                "Artist Name(s)",
                "Release Date",
                "Explicit",
                "Popularity",
                "Genres",
                "Added By",
                "Added At",
                "Energy",
                "Record Label",
                "Key",
                "Liveness",
                "Loudness",
                "Valence",
                "Time Signature",
                "Instrumentalness",
                "Speechiness",
                "Acousticness",
                "Tempo",
                "Mode",
                "Duration (ms)",
                "Danceability",
            ]

            for key in keys_to_remove:
                del song[key]
        except Exception as e:
            raise Exception(
                f"some error occured when handling metadata for song {song['track_name']}, error {e} skipping the song."
            )

    return songs_list


def embed_spotify_metadata_mutagen(
    audiofile, metadata, format: typing.Literal["mp3", "m4a", "flac"]
):
    try:
        if format == "mp3":
            audio = MP3(audiofile, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()

            # linter keeps crying about this
            assert audio.tags is not None

            track_name = metadata["track_name"]
            artist_names_str = ", ".join(metadata["artist_names"])

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

            audio.save()

        elif format == "m4a":
            audio = MP4(audiofile)

            if audio.tags is None:
                audio.add_tags()

            assert audio.tags is not None

            track_name = metadata["track_name"]
            artist_names_str = ", ".join(metadata["artist_names"])

            audio.tags["\xa9nam"] = [track_name]
            audio.tags["\xa9ART"] = [artist_names_str]
            if metadata.get("album_name"):
                audio.tags["\xa9alb"] = [metadata["album_name"]]
            if metadata.get("album_artist_names"):
                audio.tags["aART"] = [", ".join(metadata["album_artist_names"])]
            if metadata.get("album_release_date"):
                audio.tags["\xa9day"] = [metadata["album_release_date"]]

            audio.save()

        elif format == "flac":
            audio = FLAC(audiofile)

            if audio.tags is None:
                audio.add_tags()

            track_name = metadata["track_name"]
            artist_names_str = ", ".join(metadata["artist_names"])

            assert audio.tags is not None

            audio.tags["TITLE"] = [track_name]  # type: ignore
            audio.tags["ARTIST"] = [artist_names_str]  # type: ignore
            if metadata.get("album_name"):
                audio.tags["ALBUM"] = [metadata["album_name"]]  # type: ignore
            if metadata.get("album_artist_names"):
                audio.tags["ALBUMARTIST"] = [", ".join(metadata["album_artist_names"])]  # type: ignore
            if metadata.get("album_release_date"):
                audio.tags["DATE"] = [metadata["album_release_date"]]  # type: ignore
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
        embed_spotify_metadata_mutagen(downloaded_file_path, metadata, format)

        if os.path.exists(downloaded_file_path):
            shutil.move(downloaded_file_path, final_audio_file_path)
