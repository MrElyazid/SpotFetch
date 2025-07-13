
import yt_dlp

def get_song_url(song_dict: dict) -> str | None:
    """
    Constructs a Youtube query and returns the URL of the best matching video.

    Args:
        song_dict (dict): A dictionary containing 'track_name' and 'artist_names' (list).

    Returns:
        str | None: The URL of the best matching YouTube video, or None if no results are found or an error occurs.
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
        'max_downloads': 1,         }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)

            if info and 'entries' in info and len(info['entries']) > 0:
                video_url = info['entries'][0].get('url')
                print(f"Found video URL: {video_url} for query: {search_query}\n")
                return video_url
            else:
                print(f"No results found for the query: {search_query}, using default URL.")
                return 'https://music.youtube.com/watch?v=lYBUbBu4W08&si=QVvMflpkWojLjsKK'
        except yt_dlp.DownloadError as e:
            print(f"An error occurred with yt-dlp: {e}")
            return None