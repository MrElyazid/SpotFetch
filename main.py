"""The main file the user runs"""


import functions

def main():
   
    art = r"""
  ____              _   _____    _       _     
 / ___| _ __   ___ | |_|  ___|__| |_ ___| |__  
 \___ \| '_ \ / _ \| __| |_ / _ \ __/ __| '_ \ 
  ___) | |_) | (_) | |_|  _|  __/ || (__| | | |
 |____/| .__/ \___/ \__|_|  \___|\__\___|_| |_|
       |_|                                     
                                                                                            
"""
   
    print(art)
    print("Welcome to SpotFetch! \n")
    print("First visit https://exportify.app/ to export your Spotify playlist as a CSV file. \n")
   
    csv_file_path = input("Please enter the path to the CSV file: ").strip()
    output_path = input("\n\nPlease enter the output path for downloaded files (default is current directory): ").strip() or '.'
    
    try:
        print(f"getting URLs for songs in {csv_file_path}, please wait...\n")
        songs_list = functions.read_csv_file(csv_file_path)
    except FileNotFoundError as e:
        print(f"The following error occurred: {e}, are you sure the file exists?")
        return
 
    i = 1
    n = len(songs_list)
    for song in songs_list:
        print(f"\nProcessing song number : {i}/{n}, {song['track_name']} by {', '.join(song['artist_names'])}\n")
        functions.download_spotify_song(output_path=output_path, metadata=song)
        print(f"Finished processing song: {song['track_name']} by {', '.join(song['artist_names'])}\n\n")
        i += 1
        
    print("All songs processed successfully, Check the output directory for your downloaded files.\n")
if __name__ == "__main__":
    main()
