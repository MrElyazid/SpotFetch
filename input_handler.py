import csv
import os
import re

import url_lookup

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
                

        song['track_url'] = url_lookup.get_song_url(song)
  
    return songs_list