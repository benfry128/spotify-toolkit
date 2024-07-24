import io
import mysql.connector
import os
import re
import requests
import spotipy
import time
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()
LAST_FM_API_KEY = os.getenv('LAST_FM_API_KEY')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
MYSQL_PWD = os.getenv('MYSQL_PWD')

LAST_FM_FIRST_DAY = datetime(2024, 1, 2)
FIRST_DAY_SECONDS = int(LAST_FM_FIRST_DAY.timestamp())


def printDict(d):
    for key in d.keys():
        print(f'{key}: {d[key]}')


def spotipySetup():
    scope = 'ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public  user-follow-modify user-follow-read user-read-playback-position user-top-read user-read-recently-played user-library-modify user-library-read user-read-email user-read-private'
    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                                     client_secret=SPOTIFY_CLIENT_SECRET,
                                                     redirect_uri="http://localhost:1234",
                                                     scope=scope),
                           requests_timeout=10,
                           retries=0)


def db_setup():
    db = mysql.connector.connect(
        host='localhost',
        user='root',
        password=MYSQL_PWD,
        database='spotify_toolkit'
    )
    cursor = db.cursor()
    return (db, cursor)


def update_db(sp, db, cursor):

    def get_bridge_code(title, artist, album):
        return re.sub(r'\W+', '', title + artist + album).lower()

    def remove_apostrophe(str):
        return re.sub("'", '', str).lower()

    cursor.execute('SELECT MAX(utc) FROM scrobbles')

    db_max_time = cursor.fetchone()[0]
    if db_max_time:
        db_max_time += 1
    else:
        db_max_time = FIRST_DAY_SECONDS

    for t in range(db_max_time, int(time.time()), 86400):
        result = requests.get(f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=benfry128&api_key={LAST_FM_API_KEY}&format=json&from={t}&to={t + 86400}&limit=200")
        tracks = result.json()['recenttracks']['track']

        if type(tracks) is dict:
            tracks = [tracks]

        playback = sp.current_playback()
        if playback and playback['is_playing']:
            del tracks[0]  # every lastfm api call returns the currently playing track, so remove if currently playing

        date_str = datetime.fromtimestamp(t).strftime('%m/%d/%Y')
        print(f'Collecting lastfm data around {date_str} ...Got {len(tracks)} tracks')

        for track in tracks:
            utc = int(track['date']['uts']) - 1
            artist = track['artist']['#text']
            album = track['album']['#text']
            title = track['name']

            utc_taken = True
            while utc_taken:
                utc += 1
                cursor.execute(f'SELECT utc FROM scrobbles WHERE utc = "{utc}"')
                utc_taken = cursor.fetchone()

            bridge_code = get_bridge_code(title, artist, album)

            cursor.execute(f'SELECT track_id FROM last_fm_str_tracks WHERE last_fm_str = "{bridge_code}"')
            results = cursor.fetchone()

            if results:
                track_id = results[0]
            else:
                uri = None
                possible_tracks = sp.search(q=f'track:{remove_apostrophe(title)} artist:{remove_apostrophe(artist)}', type='track', limit=5)['tracks']['items']
                if possible_tracks:
                    for track in possible_tracks:
                        if bridge_code == get_bridge_code(track['name'], track['artists'][0]['name'], track['album']['name']):
                            uri = track['uri']
                            title = track['name']
                            artist = track['artists'][0]['name']
                            album = track['album']['name']
                            break

                if not uri:
                    print(f'Any ideas? Track is {title} by {artist} off {album}.')
                    if possible_tracks:
                        print("here are some possible tracks")
                        for track in possible_tracks:
                            print(f"{track['name']} by {track['artists'][0]['name']} off {track['album']['name']}. uri is {track['uri']}")
                    while True:
                        uri = input('\nIf you can find the song, enter the uri. If not, press enter. ')
                        if not uri:
                            break
                        try:
                            track = sp.track(uri)
                        except Exception:
                            print("Yeah that uri didn't work. Try again or press enter to go on")
                            continue
                        else:
                            if input(f"You chose {track['name']} by {track['artists'][0]['name']} off {track['album']['name']} You good with this track?\nPress enter to accept or anything to reject "):
                                print("Ok no go. Try again or press enter to go on")
                                continue
                            else:
                                url = track['external_urls']['spotify']
                                title = track['name']
                                artist = track['artists'][0]['name']
                                album = track['album']['name']
                                break

                if uri:
                    cursor.execute(f'SELECT id FROM tracks WHERE url = "{url}"')
                    results = cursor.fetchone()
                    if results:
                        track_id = results[0]
                    else:
                        cursor.execute('INSERT INTO tracks (name, artist, album, url) VALUES (%s, %s, %s, %s)', (title, artist, album, uri))
                        track_id = cursor.lastrowid
                else:
                    cursor.execute('INSERT INTO tracks (name, artist, album) VALUES (%s, %s, %s)', (title, artist, album))
                    track_id = cursor.lastrowid
                cursor.execute('INSERT INTO last_fm_str_tracks (last_fm_str, track_id) VALUES (%s, %s)', (bridge_code, track_id))

            cursor.execute('INSERT INTO scrobbles (utc, track_id) VALUES (%s, %s)', (utc, track_id))

            print(f'Just added ("{title}", "{artist}", "{album}"), utc was {utc}')
            db.commit()


def merge_tracks(good_track, bad_track, db, cursor):
    # move all scrobbles from bad to good
    cursor.execute(f'UPDATE scrobbles SET track_id = {good_track} WHERE track_id = {bad_track}')
    # move all lastfm str records from bad to good
    cursor.execute(f'UPDATE last_fm_str_tracks SET track_id = {good_track} WHERE track_id = {bad_track}')

    cursor.execute(f'DELETE FROM tracks WHERE id = {bad_track}')

    db.commit()


def delete_track(id, db, cursor):
    cursor.execute(f'DELETE FROM scrobbles WHERE track_id = {id}')
    cursor.execute(f'DELETE FROM last_fm_str_tracks WHERE track_id = {id}')
    cursor.execute(f'DELETE FROM tracks WHERE id = {id}')
    db.commit()


def getRecentTracks(start_days_back, end_days_back, sp, db, cursor):
    update_db(sp, db, cursor)

    sql = 'SELECT utc, name, artist, album FROM scrobbles INNER JOIN tracks ON id = track_id WHERE utc > %s AND utc < %s'
    cursor.execute(sql, ((int((time.time()-14400) / 86400) - start_days_back) * 86400 + 14400, (int((time.time()-14400) / 86400) - end_days_back + 1) * 86400 + 14400))
    recents_dicts = [
        {
            'utc': recent[0],
            'name': recent[1],
            'artist': recent[2],
            'album': recent[3]
        } for recent in cursor.fetchall()
    ]
    return recents_dicts


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

    print(f'Retrieved {len(tracks)}')

    print('Now digging through to find good versions')
    real_tracks = []
    for track in tracks:
        if not track['is_local'] and track['track'] and track['track']['type'] == 'track':
            if 'US' in track['track']['available_markets']:
                real_tracks.append(track['track'])
            else:
                alt = trackDownTrack(track['track'], sp)
                if alt:
                    real_tracks.append(alt)

    print(f'Finished, retrieved {len(real_tracks)} tracks in the end')
    return real_tracks


def trackDownTrack(track, sp):
    goodName = track['name'].lower()
    goodArtist = track['artists'][0]['name'].lower()
    isrc = track['external_ids']['isrc']

    good_tracks = sp.search(q=f'isrc:{isrc}', type='track')['tracks']['items']
    if good_tracks:
        return good_tracks[0]

    good_tracks = sp.search(q=f'track:{goodName} artist:{goodArtist}', type='track')['tracks']['items']
    if good_tracks:
        newName = good_tracks[0]['name'].lower()
        newArtist = good_tracks[0]['artists'][0]['name'].lower()

        if goodName == newName and goodArtist == newArtist:
            return good_tracks[0]
    return None


def compile_image(to_a_side, size, image_urls):
    bigImage = Image.new("RGB", (size * to_a_side, size * to_a_side))

    for id, url in enumerate(image_urls):
        print('Building image...')
        response = requests.get(url, stream=True)
        image = Image.open(io.BytesIO(response.content))
        x = (id % to_a_side) * size
        y = (id // to_a_side) * size
        bigImage.paste(image, (x, y))
        del image
        del response

    bigImage.show()
