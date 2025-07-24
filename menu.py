

import functions



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
print("visit https://exportify.app/ to export your Spotify playlist as a CSV file. \n")
print("choose an option from the menu (1-3) \n")


while True:
    print("1. Download Spotify playlist using csv file.\n")
    print("2. Download song or playlist using YouTube URL.\n")
    print("3. Search then Download a song from YouTube.\n")
    print("4. Exit the program.\n")

    choice = int(input().strip())

    if choice == 1:
        print("Enter csv file path : \n")
        csv_file_path = input().strip()
        
        print("Enter output folder path: \n")
        output_path = input().strip()

        try:
            print("Processing songs ... \n")
            songs_list = functions.read_csv_file(csv_file_path)

            n = len(songs_list)

            for i in range(n):
                    print(f"Downloading Song {i+1}/{n} ... \n")
                    functions.download_spotify_song(output_path=output_path, metadata=songs_list[i])

            print("All songs processed successfully. \n")
            print("Go back to menu ? (y/n) (n to exit the program)\n")

            ans = input().strip()

            if ans == "y":
                    continue
            elif ans == "n":
                    print("Bye Bye !!")
                    break
        except Exception as e:
            print(f"Some error occured : {e}")


    elif choice == 2:
        print(f"Enter the video or playlist URL: \n")

        url = input().strip()
        
        print("Enter output directory ( leave empty for current directory) \n")
        output_path = input().strip()

        try:
            functions.download_youtube_audio(url, output_path=output_path)
        except Exception as e:
            print(f"The following error occured : {e}")

        print("Go back to menu ? (y/n) (n to exit the program)\n")

        ans = input().strip()

        if ans == "y":
                    continue
        elif ans == "n":
                    print("Bye Bye !!")
                    break
    elif choice == 3:
        print("Enter Search Query: \n")
        query = input().strip()

        url = functions.search_song(query)
        
        if url:
            print(f"Proceed with the download ? (Y/n)\n")
            ans = input().strip()

            if ans == "y":
                functions.download_youtube_audio(url)
            elif ans == "n":
                print("Aborting ... \n")
                print("Going back to menu..")
                continue

    elif choice == 4:
        break

    else:
        print("Please enter a valid choice (1-4)")












