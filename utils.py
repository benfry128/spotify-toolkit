from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests

load_dotenv()
lastFMApiKey = os.getenv('LAST_FM_API_KEY')
spotifyID = os.getenv('SPOTIFY_CLIENT_ID')
spotifySecret = os.getenv('SPOTIFY_CLIENT_SECRET')


def printDict(d):
    for key in d.keys():
        print(f'{key}: {d[key]}')


def spotipySetup(scope):
    load_dotenv()
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotifyID,
                                                   client_secret=spotifySecret,
                                                   redirect_uri="http://localhost:1234",
                                                   scope=scope))
    return sp


def getRecentTracks(startTime, endTime):
    r = requests.get(f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=benfry128&api_key={lastFMApiKey}&format=json&from={startTime}&to={endTime}&limit=200")
    recents = r.json()['recenttracks']['track']
    return recents


def getAllPlaylists(user_id, sp):
    total_playlists = sp.user_playlists(user_id)['total']

    offset = 0
    playlists = []
    while offset < total_playlists:
        playlists.extend(sp.user_playlists(user_id)['items'])
        offset += 50

    return playlists


def getAllTracks(playlist_id, sp):
    print("Getting tracks 0-99")
    result = sp.playlist_tracks(playlist_id)
    total_tracks = result['total']

    offset = 100
    tracks = result['items']
    while offset < total_tracks:
        print(f"Getting tracks {offset}-{offset+99}")
        tracks.extend(sp.playlist_tracks(playlist_id, offset=offset)['items'])
        offset += 100

    return tracks
