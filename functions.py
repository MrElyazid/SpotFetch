import yt_dlp
import requests
import os
from mutagen.mp3 import MP3
from mutagen.id3._frames import APIC, TALB, TPE1, TPE2, TDRC, TRCK, TPOS, TIT2
from mutagen.id3._util import error as MutagenError
from mutagen.id3 import ID3
import csv
import os
import re




def search_song(query: str) -> str | None:
    """Searches for a youtube song using the provided query."""
    search_query = f"{query} Music Video"

    # minimal options for yt-dlp since the goal is to just get the URL and not to download
    ydl_opts = {
        'quiet': True,              
        'extract_flat': True,       
        'force_generic_extractor': True, 
        'noplaylist': True,          
        'default_search': 'ytsearch',
        'max_downloads': 1,        
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)

            if info and 'entries' in info and len(info['entries']) > 0:  
                video_url = info['entries'][0].get('url')
                video_title = info['entries'][0].get('channel')
                video_channel = info['entries'][0].get('title')
                print(f"Video found for the query is {video_channel} from the channel {video_title}")
                return video_url
            else:
                print(f"No results found for the query: {search_query}")
                return None

        except yt_dlp.DownloadError as e:
            print(f"An error occurred with yt-dlp: {e}")
            return None
 

def download_youtube_audio(url, output_path=".", cookiefile=None):
    """
    Downloads audio from a YouTube video or playlist in MP3 format with metadata and a cover.

    Args:
        url (str or list): The URL of the YouTube video or playlist, or a list of URLs.
        output_path (str, optional): The path to save the downloaded files. Defaults to the current directory.
        cookiefile (str, optional): Path to a cookies file. Defaults to None.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }, {
            'key': 'EmbedThumbnail',
        }, {
            'key': 'FFmpegMetadata',
        }],
        'writethumbnail': True,
        'cookiefile': cookiefile,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def get_song_url(song_dict: dict) -> str | None:
    """
    Constructs a Youtube query and returns the URL of the best matching video.

    Args:
        song_dict (dict): A dictionary containing 'track_name' and 'artist_names' (list).

    Returns:
        str | None: The URL of the best matching YouTube video, or None if an error occurs.
    """
    if 'artist_names' not in song_dict or 'track_name' not in song_dict:
        print("Error: song_dict must contain 'track_name' and 'artist_names'.")
        return None

    # query construction
    track_name = song_dict["track_name"]
    artist_namess = " ".join(song_dict["artist_names"])
    search_query = f"{track_name} {artist_namess} Music Video"

    # minimal options for yt-dlp since the goal is to just get the URL and not to download
    ydl_opts = {
        'quiet': True,              
        'extract_flat': True,       
        'force_generic_extractor': True, 
        'noplaylist': True,          
        'default_search': 'ytsearch',
        'max_downloads': 1,        
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)

            if info and 'entries' in info and len(info['entries']) > 0:
                video_url = info['entries'][0].get('url')
                print(f"Found video URL: {video_url} for query: {search_query}\n")
                return video_url
            else:
                print(f"No results found for the query: {search_query}, using default URL.")
                return 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        except yt_dlp.DownloadError as e:
            print(f"An error occurred with yt-dlp: {e}")
            return None
 
def sanitize_string(string: str) -> str:
    """Removes illegal characters from a filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', string)


def read_csv_file(file_path: str) -> list:
    """Reads a CSV file and returns its content as a list of dictionaries."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        songs_list = [ row for row in reader ]
        
    for song in songs_list:
        
        song['track_name'] = sanitize_string(song['Track Name'])
        song['artist_names'] = [sanitize_string(artist) for artist in song['Artist Name(s)'].split(',')]
        song['album_name'] = sanitize_string(song['Album Name'])
        song['album_artist_names'] = [sanitize_string(artist) for artist in song['Album Artist Name(s)'].split(',')]
        song['album_release_date'] = song['Album Release Date']
        song['album_image_url'] = song['Album Image URL']
        song['disc_number'] = song['Disc Number']
        song['track_number'] = song['Track Number']
        song['track_duration_ms'] = int(song['Track Duration (ms)']) if song['Track Duration (ms)'].isdigit() else 0
        
        keys_to_remove = [
            "Track URI", "Artist URI(s)", "Album URI", "Album Artist URI(s)",
            "Track Preview URL", "Explicit", "Popularity", "ISRC", "Added By", "Added At"
        ]
        
        
        
        for key in keys_to_remove:
                del song[key]
        
        # we already replaced these with the sanitized versions, lets remove them too
        keys_modifed_to_remove = [
            "Track Name", "Artist Name(s)", "Album Name", "Album Artist Name(s)", "Album Release Date",
            "Album Image URL", "Disc Number", "Track Number", "Track Duration (ms)"
        ] 
        
        for key in keys_modifed_to_remove:
                del song[key]
                

        song['track_url'] = get_song_url(song)
  
    return songs_list






def download_spotify_song(output_path='.', metadata=None, cookie_file=None):
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
            'preferredquality': '320',
        }],
        'outtmpl': temp_audio_file_path_template,
        'noplaylist': True,
        'quiet': False,
    }


    if cookie_file:
        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
        else:
            print(f"No cookie file was found at {cookie_file}")


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
            
if __name__ == "__main__":
    query = "Wind of change by scorpions"
    download_youtube_audio("https://www.youtube.com/watch?v=Gpwt7R9pGuo")
