import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
from dotenv import load_dotenv
import os

load_dotenv()
spotifyID = os.getenv('SPOTIFY_CLIENT_ID')
spotifySecret = os.getenv('SPOTIFY_CLIENT_SECRET')

scope = 'user-library-read playlist-modify-public playlist-read-private'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotifyID,
                                               client_secret=spotifySecret,
                                               redirect_uri="http://localhost:1234",
                                               scope=scope))

playlist_ids = [
    ["5Lh62TlIAUHgaFYo6IE2cZ", "1ciFrlllVeEBETOkvFn4qN"],  # bangers
    ["5MS4Z0D5HDugNZspLDs9uU", "6JJn8w2iqrxIFXUczrmT86"],  # thonkers
    ["42C2EObXUN25rSCzM99QTK", "1hNFjAax1k8n36HYIqT8V2"]   # vibes
]

for pair in playlist_ids:
    old_id = pair[0]
    new_id = pair[1]

    playlist = sp.playlist(old_id)
    total_tracks = playlist['tracks']['total']
    print(total_tracks)

    offset = 0
    tracks = []
    while offset < total_tracks:
        print(f"Getting tracks {offset}-{offset+99}")
        tracks.extend(sp.playlist_tracks(old_id, offset=offset)['items'])
        offset += 100

    trackIds = []
    for track in tracks:
        trackId = track['track']['uri']
        trackIds.append(trackId)

    random.shuffle(trackIds)

    sp.playlist_replace_items(new_id, trackIds[0:100])
    offset = 100
    while offset < len(trackIds):
        sp.playlist_add_items(new_id, trackIds[offset:offset+100])
        offset += 100
