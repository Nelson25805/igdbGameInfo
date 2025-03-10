# This python script is a GUI video game search engine interface from the IDGDB website database.
# After searching for all the video games the user searched for, you have the option to save the searches in an excel file.
# Each game has the name, release date, rating, genres, storyline, summary, platforms, cover url for its record.

# Author: Nelson McFadyen
# Last Updated: Jan, 07,2025

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox, PhotoImage
import pandas as pd
import os, sys
import requests
import time
from dotenv import load_dotenv
import threading

import random

from datetime import datetime, timezone

import ttkbootstrap as tb
from ttkbootstrap.constants import *


from PIL import Image, ImageTk
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

# Enviorment variables for client, token, and url
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
IGDB_BASE_URL = 'https://api.igdb.com/v4'

# Check if CLIENT_ID and CLIENT_SECRET are defined
if not CLIENT_ID and not CLIENT_SECRET:
    print('Error: Both the client ID and client secret are missing. Please add them to your .env file.')
    sys.exit()
elif not CLIENT_ID:
    print('Error: The client ID is missing. Please add it to your .env file.')
    sys.exit()
elif not CLIENT_SECRET:
    print('Error: The client secret is missing. Please add it to your .env file.')
    sys.exit()

# Get a new access token
params = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'grant_type': 'client_credentials'
}

try:
    # Request a new access token
    response = requests.post(TOKEN_URL, params=params)

    if response.status_code == 200:
        ACCESS_TOKEN = response.json().get('access_token')
    else:
        # Attempt to parse the response JSON to extract error details
        try:
            error_info = response.json()
            error_message = error_info.get('message', '')

            # Handle specific error scenarios based on status codes and error message
            if response.status_code == 400:
                if 'invalid client' in error_message:
                    print('Error: Your client ID is invalid or both the client ID and client secret are incorrect. Please correct them in your .env file.')
            elif response.status_code == 403:
                if 'invalid client secret' in error_message:
                    print('Error: Your client secret is invalid. Please correct it in your .env file.')
            else:
                # General fallback for unexpected errors
                print(f"Unexpected error: {error_message}")
        except ValueError:
            # Handle cases where the response is not valid JSON
            print('Error: The server response was not in JSON format.')
            print(f"Response: {response.text}")

        print('Program terminating due to error.')
        sys.exit()

except requests.exceptions.RequestException as e:
    # Handle network-related exceptions
    print(f"Network error occurred: {e}")
    print('Please check your internet connection or API endpoint URL.')
    sys.exit()

# Authorization header for searches
HEADERS = {
    'Client-ID': CLIENT_ID,
    'Authorization': f'Bearer {ACCESS_TOKEN}'
}

# Function to fetch data requests from IGDB API for game being searched
def fetch_data(endpoint, fields):
    response = requests.post(
        f"{IGDB_BASE_URL}/{endpoint}",
        headers=HEADERS,
        data=f"fields {fields}; limit 500;"
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data from {endpoint}: {response.status_code} - {response.text}")
        return []

# Function to fwtch voer image url for given cover_id
def fetch_cover_image(cover_id):
    if not cover_id:
        return "No cover available"
    
    response = requests.post(
        f"{IGDB_BASE_URL}/covers",
        headers=HEADERS,
        data=f"fields image_id; where id = {cover_id};"
    )
    if response.status_code == 200:
        cover_data = response.json()
        if cover_data and 'image_id' in cover_data[0]:
            image_id = cover_data[0]['image_id']
            return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
        else:
            return "Cover image not found"
    else:
        print(f"Error fetching cover data: {response.status_code} - {response.text}")
        return "Error fetching cover image"

# Function to convert genre id's to given names
def create_genre_map():
    genres = fetch_data('genres', 'id, name')
    return {genre['id']: genre['name'] for genre in genres}

# Function to convert platform id's to given names
def create_platform_map():
    platforms = fetch_data('platforms', 'id, name')
    return {platform['id']: platform['name'] for platform in platforms}

# Constants for genre and platform maps
GENRE_MAP = create_genre_map()
PLATFORM_MAP = create_platform_map()

# Function to fetch genre names 
def fetch_genre_names(genre_ids):
    if not genre_ids:
        return ["Not Available"]
    return [GENRE_MAP.get(genre_id, f"Unknown Genre {genre_id}") for genre_id in genre_ids]

# Function to fetch platform names
def fetch_platform_names(platform_ids):
    if not platform_ids:
        return ["Not Available"]
    return [PLATFORM_MAP.get(platform_id, f"Unknown Platform {platform_id}") for platform_id in platform_ids]

# Function to convert Unix timestamp to readable date format
def format_unix_timestamp(timestamp):
    if not timestamp:
        return "Not Available"
    return time.strftime('%Y-%m-%d', time.gmtime(timestamp))

# Function to fetch game data from the IGDB API search query
def get_game_data(access_token, client_id, query):
    response = requests.post(
        f"{IGDB_BASE_URL}/games",
        headers=HEADERS,
        data=query
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching game data: {response.status_code} - {response.text}")
        return []
    
# Function to add live count label, and update it with the unique games in the list
def update_live_count_label(label):
    label.config(text=f"Unique Games Added: {len(existing_game_ids)}")
    # Schedule the next update in 500 milliseconds (0.5 seconds)
    root.after(500, update_live_count_label, label)

# Function to fetch all game data from the given game title from user
def get_all_game_data(game_title):
    offset = 0
    all_game_data = []
    
    while True:
        # Construct the query with offset and limit of 500
        query = f"fields name, first_release_date, rating, genres, storyline, summary, platforms, cover; search \"{game_title}\"; limit 500; offset {offset};"
        game_data = get_game_data(ACCESS_TOKEN, CLIENT_ID, query)
        
        if not game_data:
            break  # Exit loop if no more data is returned
        
        all_game_data.extend(game_data)
        offset += 500  # Increase the offset for the next batch
        
        # If the number of results is less than 500, we've reached the end
        if len(game_data) < 500:
            break
    
    return all_game_data

games_list = []  # Combined list to store game information across searches
listbox_count = 0 # Keep track of the amount of full searches done

# Maintain a set of already added game IDs to avoid duplicates
existing_game_ids = set()  # We won't store the IDs in games_list

# Function to update progress bar with length left of current task
def update_progress_bar(progress_var, current, total):
    progress_var.set((current / total) * 100)
    root.update_idletasks()

# Function to handle the main search thread for games user has entered
def on_search():
    def search_thread():
        global listbox_count

        # Disable the buttons during the search
        search_button.config(state='disabled')
        save_button.config(state='disabled')

        game_title = entry.get().strip().lower()  # Normalize case for consistency
        if not game_title:
            messagebox.showwarning("Input Error", "Please enter a game title.")
            search_button.config(state='normal')  # Re-enable buttons if input is invalid
            save_button.config(state='normal')
            return

        # Check if the game title has already been searched
        if game_title in searched_titles:
            messagebox.showinfo("Duplicate Search", f"Search for '{game_title}' has already been done.")
            search_button.config(state='normal')
            save_button.config(state='normal')
            return

        # Add the listbox count, and add to listbox
        listbox_count += 1
        search_history_listbox.insert(0, f"{listbox_count}) {game_title}")
        searched_titles.add(game_title)

        # Fetch the game data
        game_data = get_all_game_data(game_title)
        if game_data:
            for i, game in enumerate(game_data):
                game_id = game.get('id')  # Get the game ID for uniqueness check

                # Skip if the game ID is already in the list
                if game_id in existing_game_ids:
                    continue

                game_name = game.get('name', 'Not Available')
                release_date = format_unix_timestamp(game.get('first_release_date'))
                rating = game.get('rating', 'Not Available')
                genres = ', '.join(fetch_genre_names(game.get('genres', [])))
                storyline = game.get('storyline', 'Not Available')
                summary = game.get('summary', 'Not Available')
                platforms = ', '.join(fetch_platform_names(game.get('platforms', [])))
                cover_url = fetch_cover_image(game.get('cover'))

                # Add the game to the list (without the ID)
                games_list.append({
                    "Name": game_name,
                    "Release Date": release_date,
                    "Rating": rating,
                    "Genres": genres,
                    "Storyline": storyline,
                    "Summary": summary,
                    "Platforms": platforms,
                    "Cover URL": cover_url
                })

                # Update the set of existing game IDs
                existing_game_ids.add(game_id)

                update_progress_bar(progress_var, i + 1, len(game_data))

            messagebox.showinfo("Success", f"Game data for '{game_title}' has been fetched.")

        else:
            messagebox.showinfo("No Results", "No data found for the specified game.")

        entry.delete(0, tk.END)  # Clear textbox entry
        progress_var.set(0)  # Reset progress bar after completion

        # Re-enable the buttons after the search completes
        search_button.config(state='normal')
        save_button.config(state='normal')

    # Run the search in a new thread
    threading.Thread(target=search_thread, daemon=True).start()



# Function to handle excel save functionality
def on_save():
    def simulate_save_progress(step=0):
        if step <= 100:
            update_progress_bar(progress_var, step, 100)
            root.after(10, simulate_save_progress, step + 1)  # Schedule next step
        else:
            # Save data after progress simulation
            df.to_excel(file_path, index=False, engine='openpyxl')
            messagebox.showinfo("Saved", f"Data has been saved to {file_path}")
            progress_var.set(0)  # Reset progress bar
            save_button.config(state='normal')  # Re-enable the save button

    save_button.config(state='disabled')

    if not games_list:
        messagebox.showwarning("Save Error", "No data available to save.")
        save_button.config(state='normal')  # Re-enable the button if nothing to save
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    if file_path:
        df = pd.DataFrame(games_list)
        simulate_save_progress()

# Initialize the GUI
root = tb.Window(themename="cyborg")
root.title("IGDB Game Searcher")

# Setting a custom icon
icon = PhotoImage(file="images/controller.png")
root.iconphoto(True, icon)

# Disable resizing of window
root.resizable(False,False)

# Configure columns for spacing
root.columnconfigure(0, weight=1)  # Left side (search history listbox)
root.columnconfigure(1, weight=1)  # Spacer column
root.columnconfigure(2, weight=1)  # Middle (game details frame)

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Create a frame for the Listbox and Scrollbar
listbox_frame = ttk.Frame(root)
listbox_frame.grid(row=1, column=0, padx=10, pady=10, sticky=(tk.S, tk.W))  # Bottom-left alignment

# Search history listbox
search_history_listbox = tk.Listbox(root)
search_history_listbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsw")  # Positioned on the left

# Create a Scrollbar widget and connect it to the Listbox
scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical', command=search_history_listbox.yview)
scrollbar.grid(row=0, column=1, sticky='ns')

# Link the Scrollbar to the Listbox
search_history_listbox.config(yscrollcommand=scrollbar.set)

# Adjust the Listbox size to expand with the window
listbox_frame.grid_rowconfigure(0, weight=1)
listbox_frame.grid_columnconfigure(0, weight=1)

# Set to keep track of searched game titles to avoid duplicates
searched_titles = set()

# Progress bar 
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
progress_bar.grid(row=2, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))

# Widgets
entry_label = ttk.Label(frame, text="Enter game title:")
entry_label.grid(row=0, column=0, padx=5, pady=5)
entry = ttk.Entry(frame, width=30)
entry.grid(row=0, column=1, padx=5, pady=5)
search_button = ttk.Button(frame, text="Search", command=on_search)
search_button.grid(row=0, column=2, padx=5, pady=5)
save_button = ttk.Button(frame, text="Save to Excel", command=on_save)
save_button.grid(row=1, column=0, columnspan=3, pady=10)

# Live count label
live_count_label = ttk.Label(frame, text="Unique Games Added: 0")
live_count_label.grid(row=3, column=0, columnspan=3, pady=10)

# Start the live count update in a separate thread
threading.Thread(target=update_live_count_label, args=(live_count_label,), daemon=True).start()

# Set focus on the entry widget
entry.focus_set()








# Create a frame to hold the game details
game_details_frame = ttk.Frame(root)
game_details_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

# Configure rows and columns in the frame
game_details_frame.columnconfigure(1, weight=1)  # Allow textboxes to stretch

# Game Name Label
game_name_label = ttk.Label(game_details_frame, text="Game Name:", font=("Arial", 12, "bold"))
game_name_label.grid(row=0, column=0, sticky="nw", pady=5)

# Game Name Textbox with Scrollbar
game_name_scrollbar = ttk.Scrollbar(game_details_frame, orient="vertical")
game_name_text = tk.Text(game_details_frame, height=2, wrap="word", yscrollcommand=game_name_scrollbar.set)
game_name_scrollbar.config(command=game_name_text.yview)
game_name_text.grid(row=0, column=1, sticky="ew", padx=(5, 0))
game_name_scrollbar.grid(row=0, column=2, sticky="ns")

# Summary Label
game_summary_label = ttk.Label(game_details_frame, text="Summary:", font=("Arial", 12, "bold"))
game_summary_label.grid(row=1, column=0, sticky="nw", pady=5)

# Summary Textbox with Scrollbar
summary_scrollbar = ttk.Scrollbar(game_details_frame, orient="vertical")
summary_text = tk.Text(game_details_frame, height=5, wrap="word", yscrollcommand=summary_scrollbar.set)
summary_scrollbar.config(command=summary_text.yview)
summary_text.grid(row=1, column=1, sticky="ew", padx=(5, 0))
summary_scrollbar.grid(row=1, column=2, sticky="ns")

# Platforms Label
game_platforms_label = ttk.Label(game_details_frame, text="Platforms:", font=("Arial", 12, "bold"))
game_platforms_label.grid(row=2, column=0, sticky="nw", pady=5)

# Platforms Textbox with Scrollbar
platforms_scrollbar = ttk.Scrollbar(game_details_frame, orient="vertical")
platforms_text = tk.Text(game_details_frame, height=3, wrap="word", yscrollcommand=platforms_scrollbar.set)
platforms_scrollbar.config(command=platforms_text.yview)
platforms_text.grid(row=2, column=1, sticky="ew", padx=(5, 0))
platforms_scrollbar.grid(row=2, column=2, sticky="ns")

# Genres Label
game_genres_label = ttk.Label(game_details_frame, text="Genres:", font=("Arial", 12, "bold"))
game_genres_label.grid(row=3, column=0, sticky="nw", pady=5)

# Genres Textbox with Scrollbar
genres_scrollbar = ttk.Scrollbar(game_details_frame, orient="vertical")
genres_text = tk.Text(game_details_frame, height=3, wrap="word", yscrollcommand=genres_scrollbar.set)
genres_scrollbar.config(command=genres_text.yview)
genres_text.grid(row=3, column=1, sticky="ew", padx=(5, 0))
genres_scrollbar.grid(row=3, column=2, sticky="ns")

# Release Dates Label
game_release_dates_label = ttk.Label(game_details_frame, text="Release Dates:", font=("Arial", 12, "bold"))
game_release_dates_label.grid(row=4, column=0, sticky="nw", pady=5)

# Release Dates Textbox with Scrollbar
release_dates_scrollbar = ttk.Scrollbar(game_details_frame, orient="vertical")
release_dates_text = tk.Text(game_details_frame, height=3, wrap="word", yscrollcommand=release_dates_scrollbar.set)
release_dates_scrollbar.config(command=release_dates_text.yview)
release_dates_text.grid(row=4, column=1, sticky="ew", padx=(5, 0))
release_dates_scrollbar.grid(row=4, column=2, sticky="ns")


# Example of filling textboxes with server data
def populate_game_details(game_data):
    game_name_text.delete("1.0", "end")
    summary_text.delete("1.0", "end")
    platforms_text.delete("1.0", "end")
    genres_text.delete("1.0", "end")
    release_dates_text.delete("1.0", "end")

    # Insert data into textboxes
    game_name_text.insert("1.0", game_data.get("name", "No Information"))
    summary_text.insert("1.0", game_data.get("summary", "No Information"))
    platforms_text.insert("1.0", "\n".join(game_data.get("platforms", ["No Information"])))
    genres_text.insert("1.0", "\n".join(game_data.get("genres", ["No Information"])))
    release_dates_text.insert("1.0", "\n".join(game_data.get("release_dates", ["No Information"])))

    # Disable editing for textboxes
    for textbox in [game_name_text, summary_text, platforms_text, genres_text, release_dates_text]:
        textbox.config(state="disabled")














# Function to fetch the total number of games
def get_total_games_count():
    response = requests.post(
        f"{IGDB_BASE_URL}/games/count",
        headers=HEADERS,
        data=""
    )
    if response.status_code == 200:
        count_data = response.json()
        return count_data.get('count', 0)
    else:
        print(f"Error fetching games count: {response.status_code} - {response.text}")
        return 0

# Function to fetch a random game based on the total countdef fetch_random_game_gui():
def fetch_random_game_gui():
    total_games = get_total_games_count()
    if total_games == 0:
        print("Unable to retrieve the total games count.")
        return

    # Clear the previous image
    game_image_label.config(image="", text="No Image Available")
    game_image_label.image = None  # Clear reference to the previous image

    random_offset = random.randint(0, total_games - 1)
    print(f"Fetching game at random offset: {random_offset}")
    
    response = requests.post(
        f"{IGDB_BASE_URL}/games",
        headers=HEADERS,
        data=f"fields name, summary, release_dates.date, genres.name, platforms.name, cover.image_id; offset {random_offset}; limit 1;"
    )
    if response.status_code == 200:
        game_data = response.json()
        if game_data:
            game = game_data[0]  # Get the first game from the response

            # Extract data or fallback to "No Information"
            game_name = game.get('name', 'No Information')
            game_summary = game.get('summary', 'No Information')
            game_platforms = ', '.join(platform['name'] for platform in game.get('platforms', [])) or 'No Information'
            game_genres = ', '.join(genre['name'] for genre in game.get('genres', [])) or 'No Information'

            # Convert release dates to human-readable format
            release_dates_raw = game.get('release_dates', [])
            if release_dates_raw:
                readable_release_dates = []
                for date_entry in release_dates_raw:
                    unix_timestamp = date_entry.get('date')
                    if unix_timestamp:
                        readable_date = datetime.fromtimestamp(unix_timestamp, timezone.utc).strftime('%Y-%m-%d')
                        readable_release_dates.append(readable_date)
                game_release_dates = ', '.join(readable_release_dates) or 'No Information'
            else:
                game_release_dates = 'No Information'

            # Update textboxes in the GUI
            game_name_text.config(state="normal")
            summary_text.config(state="normal")
            platforms_text.config(state="normal")
            genres_text.config(state="normal")
            release_dates_text.config(state="normal")
            
            game_name_text.delete("1.0", "end")
            summary_text.delete("1.0", "end")
            platforms_text.delete("1.0", "end")
            genres_text.delete("1.0", "end")
            release_dates_text.delete("1.0", "end")

            game_name_text.insert("1.0", game_name)
            summary_text.insert("1.0", game_summary)
            platforms_text.insert("1.0", game_platforms)
            genres_text.insert("1.0", game_genres)
            release_dates_text.insert("1.0", game_release_dates)

            # Make textboxes read-only after updating
            for textbox in [game_name_text, summary_text, platforms_text, genres_text, release_dates_text]:
                textbox.config(state="disabled")
            
            # Fetch and display the game cover image
            cover_image_id = game.get('cover', {}).get('image_id')
            if cover_image_id:
                image_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{cover_image_id}.jpg"
                try:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        image_data = Image.open(BytesIO(image_response.content))
                        image_data = image_data.resize((300, 400))  # Resize image for larger display
                        game_image = ImageTk.PhotoImage(image_data)
                        game_image_label.config(image=game_image, text="")  # Clear placeholder text
                        game_image_label.image = game_image  # Keep a reference to avoid garbage collection
                    else:
                        game_image_label.config(text="Image not available")
                except Exception as e:
                    print(f"Error loading image: {e}")
                    game_image_label.config(text="Image not available")
            else:
                game_image_label.config(text="No Image Available")
        else:
            print("No game data found.")
    else:
        print(f"Error fetching random game: {response.status_code} - {response.text}")




# Add a button to the GUI
random_game_button = ttk.Button(frame, text="Random Game", command=fetch_random_game_gui)
random_game_button.grid(row=5, column=0, pady=10)

# Create a Label for the game image
game_image_label = ttk.Label(game_details_frame, text="No Image Available", font=("Arial", 12, "italic"))
game_image_label.grid(row=5, column=0, columnspan=3, pady=10)






# Start main program
root.mainloop()
