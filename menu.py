import functions



art = r"""
  ____              _   _____    _       _     
 / ___| _ __   ___ | |_|  ___|__| |_ ___| |__  
 \___ \| '_ \ / _ \| __| |_ / _ \ __/ __| '_ \ 
  ___) | |_) | (_) | |_|  _|  __/ || (__| | | |
 |____/| .__/ \___/ \__|_|  \___|\__\___|_| |_|
       |_|                                     
                                                                                            
"""


print("Welcome to SpotFetch! \n")
print("visit https://exportify.app/ to export your Spotify playlist as a CSV file. \n")
print("If YouTube asks for login bypass it using a cookies file, read : https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp \n")
print("choose an option from the menu (1-5) \n")
 
cookie_path = None
while True:
    
    cookie_option = f"(already using the file at {cookie_path})" if cookie_path else ""


    print(art)
    print("\n1. Download Spotify playlist using csv file.")
    print("2. Download song or playlist using YouTube URL.")
    print("3. Search then Download a song from YouTube.")
    print(f"4. Use a cookies file for other operations. {cookie_option}")
    print("5. Exit the program.\n")

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
                    functions.download_spotify_song(output_path=output_path, metadata=songs_list[i], cookie_file=cookie_path)

            print("All songs processed successfully. \n")
            print("Going back to menu ... ")
            continue
                   
        except Exception as e:
            print(f"Some error occured : {e}")


    elif choice == 2:
        print(f"Enter the video or playlist URL: \n")

        url = input().strip()
        
        print("Enter output directory ( leave empty for current directory) \n")
        output_path = input().strip()

        try:
            functions.download_youtube_audio(url, output_path=output_path, cookiefile=cookie_path)
        except Exception as e:
            print(f"The following error occured : {e}")

        print("Going back to menu ... \n")
        continue


    elif choice == 3:
        print("Enter Search Query: \n")
        query = input().strip()

        url = functions.search_song(query)
        
        if url:
            print(f"Proceed with the download ? (y/n)\n")
            ans = input().strip()

            if ans == "y":
                output_path = input("Enter save location ( leave empty for current directory )\n")
                functions.download_youtube_audio(url, output_path=output_path, cookiefile=cookie_path)
            elif ans == "n":
                print("Aborting ... \n")
                print("Going back to menu..")
                continue

    elif choice == 4:
        print("Enter the path to cookie.txt \n")
        cookie_path = input().strip()
        print(f"cookies file at {cookie_path} will be used for other options, going back to menu...\n")
        continue

    elif choice == 5:
        print("Bye Bye!")
        break

    else:
        print("Please enter a valid choice (1-5)")












