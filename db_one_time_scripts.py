import utils
from pprint import pprint
import requests


def change_singles_to_albums(sp, db, cursor):
    cursor.execute('SELECT id, name from albums where type = "single" and source = "sp" and id > 273 order by id')

    albums = cursor.fetchall()

    for single_id, single_name in albums:
        print(single_id)
        print(single_name)
        cursor.execute('select track, artist, track_id from track_album_main_artist where album_id = %s', [single_id])
        tracks = cursor.fetchall()
        for (single_track, single_artist, single_track_id) in tracks:
            print(f'track: {single_track} artist: {single_artist}')
            possible_tracks = sp.search(q=f'track:{single_track} artist:{single_artist}', type='track', limit=10)['tracks']['items']
            skip = True
            for track in possible_tracks:
                if track['name'] == single_track:
                    if track['album']['album_type'] == 'album':
                        print(f"Track: {track['name']} Album {track['album']['name']}. url is {track['external_urls']['spotify']}")
                        skip = False

                    if track['album']['name'] != single_name:
                        cursor.execute('select id from albums where uri = %s', [track['album']['id']])
                        if cursor.fetchall():
                            print("WE GOT A HIT IN THE DB THIS IS GOOD")
                            skip = False

            if skip:
                continue

            url = input('Which url?')

            if not url:
                continue

            good_track = sp.track(url)
            print(good_track)
            uri = good_track['id']

            cursor.execute('select id from tracks where uri = %s', [uri])
            old_record = cursor.fetchone()
            if old_record:
                utils.merge_tracks(old_record[0], single_track_id, db, cursor)
                continue

            album_uri = good_track['album']['id']

            cursor.execute('select id from albums where uri = %s', [album_uri])
            old_album = cursor.fetchone()
            if old_album:
                album_id = old_album[0]
            else:
                input(f"about to put in a new album: {good_track['album']['name']}")
                cursor.execute('INSERT INTO albums (uri, name, type, source, image) VALUES (%s, %s, %s, %s, %s)', (album_uri, good_track['album']['name'], good_track['album']['album_type'], 'sp', good_track['album']['images'][0]['url'][24:]))
                album_id = cursor.lastrowid

            cursor.execute('update tracks set uri = %s, album_id = %s where id = %s', (url, album_id, single_track_id))
            db.commit()


def swap_out_clean_versions_of_albums(sp, db, cursor):
    sp_albums = utils.sp_albums(sp, cursor)

    for sp_album in sp_albums:
        if not utils.album_explicit_and_few_artists(sp_album):
            print(f'Album {sp_album['name']} is clean')
            title = sp_album['name']
            artist = sp_album['artists'][0]['name']
            other_versions = sp.search(f'album:{title} artist:{artist}', limit=5, type='album')['albums']['items']
            if type(other_versions) is list:
                for album in other_versions:
                    if not album['external_urls']['spotify'] == sp_album['external_urls']['spotify'] and album['name'] == sp_album['name']:
                        print(album['external_urls']['spotify'])
                        if not input('Maybe this one would be better?'):
                            cursor.execute('insert into albums (url, title, type) values (%s, %s, %s)', [album['external_urls']['spotify'], album['name'], album['album_type']])
                            cursor.execute('update tracks set album = %s where album = %s', [album['external_urls']['spotify'], sp_album['external_urls']['spotify']])
                            db.commit()


def add_popularity_scores(sp, db, cursor):
    sp_tracks = utils.sp_tracks(sp, cursor)

    for track in sp_tracks:
        print(f'{track['name']}\n{track['popularity']}')
        cursor.execute('update tracks set popularity = %s where url = %s', [track['popularity'], track['external_urls']['spotify']])

    db.commit()


def add_album_art(sp, db, cursor):
    albums = utils.sp_albums(sp, cursor)

    for album in albums:
        cursor.execute('update albums set image = %s where uri = %s', [album['images'][0]['url'], album['id']])

    db.commit()

    cursor.execute('SELECT id, url FROM albums WHERE url like "%youtu.be%"')
    rows = cursor.fetchall()

    THUMBNAIL_SIZES = ['maxres', 'standard', 'high', 'medium', 'default']

    for row in rows:
        db_id = row[0]
        yt_id = row[1][17:]
        r = requests.get(f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={yt_id}&key={utils.YOUTUBE_API_KEY}')
        pprint(r.json())
        thumbnails = r.json()['items'][0]['snippet']['thumbnails']
        for size in THUMBNAIL_SIZES:
            if size in thumbnails:
                cursor.execute('UPDATE albums SET image = %s where id = %s', [thumbnails[size]['url'], db_id])
                db.commit()
                break

    cursor.execute('SELECT id, url FROM albums WHERE url like "%youtube.com/playlist%"')
    rows = cursor.fetchall()

    THUMBNAIL_SIZES = ['maxres', 'standard', 'high', 'medium', 'default']

    for row in rows:
        db_id = row[0]
        yt_id = row[1][38:]
        r = requests.get(f'https://www.googleapis.com/youtube/v3/playlists?part=snippet&id={yt_id}&key={utils.YOUTUBE_API_KEY}')
        thumbnails = r.json()['items'][0]['snippet']['thumbnails']
        for size in THUMBNAIL_SIZES:
            if size in thumbnails:
                cursor.execute('UPDATE albums SET image = %s where id = %s', [thumbnails[size]['url'], db_id])
                db.commit()
                break
