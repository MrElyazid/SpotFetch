import re
import requests
from functions import sanitize_string


class SpotifyAPIError(Exception):
    pass


PLAYLIST_URL_PATTERN = re.compile(r'playlist/([a-zA-Z0-9]+)')


def extract_playlist_id(url):
    match = PLAYLIST_URL_PATTERN.search(url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract playlist ID from URL: {url}")


def _check_response(resp):
    if resp.status_code == 429:
        raise SpotifyAPIError("Spotify API rate limit exceeded. Try again later.")
    if not resp.ok:
        detail = resp.text
        raise SpotifyAPIError(
            f"{resp.status_code} {resp.reason}: {detail}"
        )


def fetch_playlist_name(playlist_id, access_token):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(url, headers=headers, timeout=30)
    _check_response(resp)
    data = resp.json()
    return data.get('name', 'Unknown Playlist')


def fetch_playlist_tracks(playlist_id, access_token):
    tracks = []
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {'Authorization': f'Bearer {access_token}'}

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        _check_response(resp)
        data = resp.json()

        for item in data.get('items', []):
            track = item.get('track')
            if track and track.get('id'):
                tracks.append(track)

        url = data.get('next')

    return tracks


def fetch_user_id(access_token):
    url = "https://api.spotify.com/v1/me"
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(url, headers=headers, timeout=30)
    _check_response(resp)
    return resp.json()['id']


def fetch_user_playlists(access_token):
    playlists = []
    url = "https://api.spotify.com/v1/me/playlists?limit=50"
    headers = {'Authorization': f'Bearer {access_token}'}

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        _check_response(resp)
        data = resp.json()

        for item in data.get('items', []):
            playlists.append({
                'id': item['id'],
                'name': item['name'],
                'tracks_total': item['tracks']['total'],
                'public': item['public'],
                'owner': item['owner']['display_name'],
            })

        url = data.get('next')

    return playlists


def fetch_liked_songs(access_token):
    tracks = []
    url = "https://api.spotify.com/v1/me/tracks?limit=50"
    headers = {'Authorization': f'Bearer {access_token}'}

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        _check_response(resp)
        data = resp.json()

        for item in data.get('items', []):
            track = item.get('track')
            if track and track.get('id'):
                tracks.append(track)

        url = data.get('next')

    return tracks


def track_to_metadata(spotify_track):
    return {
        'track_name': sanitize_string(spotify_track.get('name', 'Unknown Track')),
        'artist_names': [
            sanitize_string(a.get('name', 'Unknown Artist'))
            for a in spotify_track.get('artists', [])
        ],
        'album_name': sanitize_string(
            spotify_track.get('album', {}).get('name', 'Unknown Album')
        ),
        'album_artist_names': [
            sanitize_string(a.get('name', 'Unknown Artist'))
            for a in spotify_track.get('album', {}).get('artists', [])
        ],
        'track_duration_ms': spotify_track.get('duration_ms', 0),
        'album_release_date': sanitize_string(
            spotify_track.get('album', {}).get('release_date', '')
        ),
        'genres': [],
    }
