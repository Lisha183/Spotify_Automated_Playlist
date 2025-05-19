import os
from dotenv import load_dotenv
import tkinter as tk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from youtubesearchpython import VideosSearch
import webbrowser
import csv
import threading
import time
from tkinter import Scrollbar

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-library-read playlist-modify-public playlist-read-private",
    open_browser=True
))

user = sp.current_user()
print(f"Authenticated as {user['display_name']}")

playlist_images = []

def get_tracks_by_genre(genre, loading_label):
    loading_label.config(text="Searching tracks...")
    root.update()
    print(f"Searching for tracks in genre: {genre}")
    results = sp.search(q=f"genre:{genre}", type="track", limit=7)
    tracks = results.get('tracks', {}).get('items', [])
    if not tracks:
        print("No tracks found for this genre. Using your top tracks instead.")
        loading_label.config(text="No tracks found. Using top tracks...")
        root.update()
        time.sleep(1)
        loading_label.destroy()
        return get_user_top_tracks(limit=7)
    loading_label.destroy()
    return [track['id'] for track in tracks]

def get_user_top_tracks():
    print("Fetching your top tracks...")
    results = sp.current_user_top_tracks(limit=30)
    tracks = results.get('items', [])
    if not tracks:
        print("You have no top tracks.")
        return []
    return [track['id'] for track in tracks]

def create_playlist(track_ids, playlist_name, loading_label):
    loading_label.config(text=f"Creating playlist '{playlist_name}'...")
    root.update()
    user_id = sp.current_user()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
    sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist['id'], tracks=track_ids[:100])
    print(f"Playlist '{playlist_name}' created!")
    loading_label.destroy()
    return playlist_name

def save_playlist(playlist_name, track_ids, loading_label):
    loading_label.config(text="Saving playlist...")
    root.update()
    track_data = []
    for track_id in track_ids:
        track = sp.track(track_id)
        track_data.append(track)

    filename = f"{playlist_name.replace(' ','_')}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Track Name", "Artists", "Spotify URL"])
        for track in track_data:
            name = track['name']
            artists = ", ".join([artist['name'] for artist in track['artists']])
            url = track['external_urls']['spotify']
            writer.writerow([name, artists, url])
        print(f"Saved playlist to {filename}")
    loading_label.destroy()

def play_track_on_youtube(track_name, artists):
    query = f"{track_name} {artists} audio"
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
    if result['result']:
        video_url = result['result'][0]['link']
        webbrowser.open(video_url)
    else:
        print("No YouTube result found for:", query)

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def generate_playlist():
    genre = genre_entry.get()
    mood = mood_entry.get()
    energy = energy_entry.get()
    playlist_name = playlist_name_entry.get()

    try:
        mood = float(mood)
        if not 0.0 <= mood <= 1.0:
            raise ValueError
    except ValueError:
        mood = 0.5

    try:
        energy = float(energy)
        if not 0.0 <= energy <= 1.0:
            raise ValueError
    except ValueError:
        energy = 0.5

    loading_label = tk.Label(form_frame, text="Loading tracks...", bg="black", fg="white", font=("Helvetica", 10))
    loading_label.pack(pady=5)
    root.update()

    track_ids = get_tracks_by_genre(genre, loading_label)
    if not track_ids:
        print(f"No tracks found.")
        return

    loading_label_create = tk.Label(form_frame, text="Creating playlist...", bg="black", fg="white", font=("Helvetica", 10))
    loading_label_create.pack(pady=5)
    root.update()
    created_name = create_playlist(track_ids, playlist_name, loading_label_create)

    loading_label_save = tk.Label(form_frame, text="Saving playlist...", bg="black", fg="white", font=("Helvetica", 10))
    loading_label_save.pack(pady=5)
    root.update()
    save_playlist(created_name, track_ids, loading_label_save)

    form_frame.pack_forget()
    playlists_frame.pack_forget()

    clear_frame(songs_frame)
    songs_frame.pack(fill="both", expand=True)

    title = tk.Label(songs_frame, text=f"Playlist: {created_name}", bg="black", fg="white", font=("Helvetica", 14))
    title.pack(pady=10)

    for track_id in track_ids:
        track = sp.track(track_id)
        name = track['name']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        album_img_url = track['album']['images'][1]['url']

        response = requests.get(album_img_url)
        img_data = Image.open(BytesIO(response.content)).resize((60, 60))
        img = ImageTk.PhotoImage(img_data)

        container = tk.Frame(songs_frame, bg="black")
        container.pack(fill="x", pady=5, padx=10)
        container.bind("<Button-1>", lambda event, t_name=name, t_artists=artists: play_track_on_youtube(t_name, t_artists))
        container.config(cursor="hand2")

        img_label = tk.Label(container, image=img, bg="black")
        img_label.image = img
        img_label.pack(side="left")

        text_label = tk.Label(container, text=f"{name} - {artists}", fg="white", bg="black", font=("Helvetica", 10))
        text_label.pack(side="left", padx=10)

def play_first_song():
    genre = genre_entry.get()

    loading_label = tk.Label(form_frame, text="Loading...", bg="black", fg="white", font=("Helvetica", 10))
    loading_label.pack(pady=5)
    root.update()

    track_ids = get_tracks_by_genre(genre, loading_label)
    if not track_ids:
        return
    first_track = sp.track(track_ids[0])
    track_name = first_track['name']
    artists = ", ".join([artist['name'] for artist in first_track['artists']])
    play_track_on_youtube(track_name, artists)

def show_playlists():
    global playlist_images
    playlist_images.clear()
    form_frame.pack_forget()
    songs_frame.pack_forget()
    clear_frame(playlists_list_frame)
    playlists_frame.pack(fill="both", expand=True)
    playlists_list_frame.config(bg="black")
    canvas = tk.Canvas(playlists_frame, bg="black", highlightthickness=0) 
    scrollbar = Scrollbar(playlists_frame, orient="vertical", command=canvas.yview)  
    scrollable_frame = tk.Frame(canvas, bg="black")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")  
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw") 
    canvas.configure(yscrollcommand=scrollbar.set)

    loading_label = tk.Label(playlists_frame, text="Loading playlists...", bg="black", fg="white", font=("Helvetica", 10))
    loading_label.pack(pady=10)
    root.update()

    def fetch_playlists():
        playlists = sp.current_user_playlists(limit=50)['items']
        columns = 3
        for index, playlist in enumerate(playlists):
            pl_name = playlist['name']
            image_url = playlist['images'][0]['url'] if playlist['images'] else None

            if image_url:
                response = requests.get(image_url)
                try:
                    img_data = response.content
                    img = Image.open(BytesIO(img_data))
                    img = img.resize((80, 80))
                    photo = ImageTk.PhotoImage(img)
                except Exception as e:
                    print(f"Error loading image for {pl_name}: {e}")
                    photo = ImageTk.PhotoImage(Image.new("RGB", (80, 80), color="black"))
            else:
                photo = ImageTk.PhotoImage(Image.new("RGB", (80, 80), color="black"))

            playlist_images.append(photo)

            item_container = tk.Frame(playlists_list_frame, bg="#282828")
            item_container.grid(row=index // columns, column=index % columns, padx=10, pady=10, sticky="nsew")

            img_label = tk.Label(item_container, image=photo, bg="#282828")
            img_label.pack(side="top")

            name_label = tk.Label(item_container, text=pl_name, bg="#282828", fg="white", font=("Helvetica", 10), wraplength=80, justify="center")
            name_label.pack(side="bottom", fill="x")

            item_container.bind("<Button-1>", lambda event, pid=playlist['id'], pname=pl_name: show_songs(pid, pname))
            item_container.config(cursor="hand2")

        for i in range(columns):
            playlists_list_frame.grid_columnconfigure(i, weight=1)
        loading_label.destroy()

    threading.Thread(target=fetch_playlists).start()

def show_songs(playlist_id, playlist_name):
    playlists_frame.pack_forget()
    form_frame.pack_forget()
    songs_frame.pack(fill="both", expand=True)
    clear_frame(songs_frame)

    loading_label = tk.Label(songs_frame, text="Loading songs...", bg="black", fg="white", font=("Helvetica", 10))
    loading_label.pack(pady=10)
    root.update()

    def fetch_songs():
        tracks = sp.playlist_tracks(playlist_id)['items']

        title = tk.Label(songs_frame, text=f"Playlist: {playlist_name}", bg="black", fg="white", font=("Helvetica", 14))
        title.pack(pady=10)

        for item in tracks:
            track = item['track']
            name = track['name']
            artists = ", ".join([artist['name'] for artist in track['artists']])
            album_img_url = track['album']['images'][1]['url']

            response = requests.get(album_img_url)
            try:
                img_data = Image.open(BytesIO(response.content)).resize((60, 60))
                img = ImageTk.PhotoImage(img_data)
            except Exception as e:
                print(f"Error loading image for {name}: {e}")
                img = ImageTk.PhotoImage(Image.new("RGB", (60, 60), color="black"))

            container = tk.Frame(songs_frame, bg="black")
            container.pack(fill="x", pady=5, padx=10)
            container.bind("<Button-1>", lambda event, t_name=name, t_artists=artists: play_track_on_youtube(t_name, t_artists))
            container.config(cursor="hand2")

            img_label = tk.Label(container, image=img, bg="black")
            img_label.image = img
            img_label.pack(side="left")

            text_label = tk.Label(container, text=f"{name} - {artists}", fg="white", bg="black", font=("Helvetica", 10))
            text_label.pack(side="left", padx=10)
        loading_label.destroy()

    threading.Thread(target=fetch_songs).start()

def show_form():
    playlists_frame.pack_forget()
    songs_frame.pack_forget()
    form_frame.pack(padx=10, pady=10)
    play_button.pack(pady=5)
    genre_entry.focus_set()

root = tk.Tk()
root.title("JUNO")
root.configure(background="black")
root.geometry("900x600")

sidebar_frame = tk.Frame(root, bg="#121212", width=180)
sidebar_frame.pack(side="left", fill="y")

button_params = {
    "bd": 0,
    "highlightthickness": 0,
    "relief": "flat"
}

btn_show_playlists = tk.Button(sidebar_frame, text="Your Playlists", bg="#1DB954", fg="black",
                               command=show_playlists, **button_params)
btn_show_playlists.pack(fill="x", pady=10, padx=10)

btn_create_playlist = tk.Button(sidebar_frame, text="Create Playlist", bg="#1DB954", fg="black",
                                command=show_form, **button_params)
btn_create_playlist.pack(fill="x", pady=10, padx=10)

btn_go_back = tk.Button(sidebar_frame, text="Go Back", bg="#1DB954", fg="black",
                        command=show_playlists, **button_params)
btn_go_back.pack(fill="x", pady=10, padx=10)

main_frame = tk.Frame(root, bg="black")
main_frame.pack(side="left", fill="both", expand=True)

form_frame = tk.Frame(main_frame, bg="black")
songs_frame = tk.Frame(main_frame, bg="black")
playlists_frame = tk.Frame(main_frame, bg="black")
playlists_list_frame = tk.Frame(playlists_frame, bg="black")
playlists_list_frame.pack(fill="both", expand=True)

# Input fields
label_font = ("Helvetica", 12)
entry_width = 30

tk.Label(form_frame, text="Genre:", bg="black", fg="white", font=label_font).pack()
genre_entry = tk.Entry(form_frame, width=entry_width)
genre_entry.pack(pady=5)

tk.Label(form_frame, text="Mood (0 to 1):", bg="black", fg="white", font=label_font).pack()
mood_entry = tk.Entry(form_frame, width=entry_width)
mood_entry.pack(pady=5)

tk.Label(form_frame, text="Energy (0 to 1):", bg="black", fg="white", font=label_font).pack()
energy_entry = tk.Entry(form_frame, width=entry_width)
energy_entry.pack(pady=5)

tk.Label(form_frame, text="Playlist Name:", bg="black", fg="white", font=label_font).pack()
playlist_name_entry = tk.Entry(form_frame, width=entry_width)
playlist_name_entry.pack(pady=5)

play_button = tk.Button(form_frame, text="Generate Playlist", command=generate_playlist, bg="#1DB954", fg="black")
play_button.pack(pady=5)

show_playlists()
root.mainloop()

