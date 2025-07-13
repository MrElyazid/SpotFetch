import yt_dlp
import requests
import os
from mutagen.mp3 import MP3
from mutagen.id3._frames import APIC, TALB, TPE1, TPE2, TDRC, TRCK, TPOS, TIT2
from mutagen.id3._util import error as MutagenError
from mutagen.id3 import ID3


def download_and_embed_audio(output_path='.', metadata=None):
    """
    Downloads audio from a YouTube URL, downloads an image from a URL in the metadata,
    embeds the metadata and image as album art into the audio file,
    and renames the audio file to 'track_name - artist_names.mp3'.
    Args:
        
        output_path (str): The directory where the audio and image files will be temporarely saved, then merged.
        metadata (dict): a dictionary in the format:

        {'track_name': 'str', 'artist_names': 'array of strings', 'album_name': 'string',
        'album_artist_names': 'array of strings', 'album_release_date': 'date in the format YYYY-MM-DD',
        'album_image_url': 'string', 'disc_number': 'int', 'track_number': 'int', 'track_duration_ms': 'int', 'track_url': 'string'}
        
        
    """
    if metadata is None:
        metadata = {}

    # metadata
    track_name = metadata.get('track_name', 'Unknown Track')
    artist_names = metadata.get('artist_names', ['Unknown Artist'])
    image_url = metadata.get('album_image_url')
    video_url = metadata.get('track_url')
    artist_names_str = ', '.join(artist_names)
    file_name_base = f"{track_name} - {artist_names_str}"
    
    
    # temporary naming
    temp_audio_file_path_template = os.path.join(output_path, 'temp_audio_download')
    final_audio_file_path = os.path.join(output_path, f"{file_name_base}.mp3")
    

    if os.path.exists(final_audio_file_path):
        print(f"File {final_audio_file_path} already exists. Skipping download.")
        return
    
    image_file_path = os.path.join(output_path, "temp_cover.jpg")


    # getting the image
    if image_url:
        try:
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            with open(image_file_path, 'wb') as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    out_file.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"WARNING : Error downloading image for track {track_name}: {e}")
            image_file_path = None
    else:
        image_file_path = None

    # yt-dlp options for audio download
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': temp_audio_file_path_template,
        'noplaylist': True,
        'quiet': False,
    }

    # audio download
    downloaded_file_path = f"{temp_audio_file_path_template}.mp3"
    try:
        print(f"\nDownloading audio for {file_name_base} from: {video_url}\n")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)

    except Exception as e:
        print(f"\nAn error occurred during audio download for the track {track_name}: {e}")
        if image_file_path and os.path.exists(image_file_path):
            os.remove(image_file_path)
        return

    # embedding metadata and album image
    try:
        audio = MP3(downloaded_file_path, ID3=ID3)
        
        
        if audio.tags is None:
            audio.add_tags()

        # linter keeps crying about this
        assert audio.tags is not None
        
        if image_file_path and os.path.exists(image_file_path):
            with open(image_file_path, 'rb') as art:
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=art.read()))


        audio.tags.add(TIT2(encoding=3, text=track_name))
        audio.tags.add(TPE1(encoding=3, text=artist_names_str))
        if metadata.get('album_name'):
            audio.tags.add(TALB(encoding=3, text=metadata['album_name']))
        if metadata.get('album_artist_names'):
            audio.tags.add(TPE2(encoding=3, text=', '.join(metadata['album_artist_names'])))
        if metadata.get('album_release_date'):
            audio.tags.add(TDRC(encoding=3, text=metadata['album_release_date']))
        if metadata.get('track_number'):
            audio.tags.add(TRCK(encoding=3, text=str(metadata['track_number'])))
        if metadata.get('disc_number'):
            audio.tags.add(TPOS(encoding=3, text=str(metadata['disc_number'])))
        
        audio.save()


    except (FileNotFoundError, MutagenError) as e:
        print(f"An error occurred during metadata embedding for track {track_name}: {e}")
    finally:
        # clean up and rename file
        if image_file_path and os.path.exists(image_file_path):
            os.remove(image_file_path)
            
        if os.path.exists(downloaded_file_path):
            os.rename(downloaded_file_path, final_audio_file_path)
            

