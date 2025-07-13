
# SpotFetch :

A very simple python script to download spotify playlists using yt-dlp after exporting the playlist as a CSV file from [Exportify](https://exportify.app/).

- Simply get the CSV and start downloading
- No rate limiting since we dont use the spotify API
- Album cover art and metdata are embedded to the mp3 files
- Can resume downloads if stopped

# Installation :

### ffmpeg :

- First make sure you have ffmpeg installed on your machine [Dowbload here](https://ffmpeg.org/download.html).

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

- Thats it, now run `main.py` :

```bash
python3 main.py
# or python main.py
```