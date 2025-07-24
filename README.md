
# SpotFetch :


![SpotFetch Demo](./.github/demo.png)


A very simple python script to download spotify playlists using yt-dlp after exporting the playlist as a CSV file from [Exportify](https://exportify.app/), alongside some useful yt-dlp aliases to use instead of manual commands.

- Simply get the CSV and start downloading
- No rate limiting since we dont use the spotify API
- Album cover art and metdata are embedded to the mp3 files
- Can resume downloads if stopped
- Possibility to use a cookies.txt file in case YouTube asks for login.
- Other useful yt-dlp tasks done quick : Search then download a song, download a song or a playlist using a URL.


# Installation :

### ffmpeg :

- First make sure you have ffmpeg installed on your machine [Download here](https://ffmpeg.org/download.html).

### setup :

- Clone this repository :

```bash
git clone https://github.com/MrElyazid/SpotFetch.git
```

- then :

```bash
cd SpotFetch
```

- Install `requirements.txt` ( preferably use a new virtual environement ):

```bash
pip install -r requirements.txt
```

- Thats it, now run `menu.py` :

```bash
python3 menu.py
# or python menu.py
```
