import utils
import random

sp = utils.spotipySetup('playlist-read-private playlist-read-collaborative user-read-playback-state playlist-modify-public')

# SETTINGS
EXCLUDE_COLLAB_PLAYLISTS = True
EXCLUDE_OTHERS_PLAYLISTS = True
EXPLICIT_ALLOWED = False
USER_ID = input("User id? ")

result = sp.user_playlists(USER_ID)

playlists = utils.getAllPlaylists(USER_ID, sp)

letters = 'abcdefghijklmnopqrstuvwxyz'
letter_list = list(letters)
letterDict = {}

for letter in letters:
    letterDict[letter] = {}

for playlist in playlists:
    if (EXCLUDE_COLLAB_PLAYLISTS and playlist['collaborative']) or (EXCLUDE_OTHERS_PLAYLISTS and not playlist['owner']['id'] == USER_ID):
        print(f"{playlist['name']} EXCLUDED")
        continue
    readPlaylist = input(f"Include playlist {playlist['name']}? (y/n/s to skip the rest) ")
    if readPlaylist == 's':
        break
    elif readPlaylist != 'y':
        continue
    print(playlist['name'])
    tracks = utils.getAllTracks(playlist['uri'], sp)

    for track in tracks:
        if not track['track'] or (track['track']['explicit'] and not EXPLICIT_ALLOWED):
            continue
        track_name = track['track']['name']
        track_id = track['track']['uri']
        first_letter = 0
        for letter in track_name:
            if letter.lower() in letter_list:
                first_letter = letter.lower()
                break
        if not first_letter:
            continue
        # track_artist = track['track']['artists'][0]['name']

        if track_id in letterDict[first_letter]:
            letterDict[first_letter][track_id] += 1
        else:
            letterDict[first_letter][track_id] = 1

# loop through letter dict to choose a song from

allLetters = True
for letter in letterDict:
    if not letterDict[letter].keys():
        allLetters = False
        break

final_uris = []

if allLetters or input("Playlist will not be complete, continue? (y/n)") == 'y':
    for letter in letterDict:
        maxFreq = 0
        uris = []

        for uri in letterDict[letter]:
            uris.append(uri)
        # for uri in letterDict[letter]:
        #     if letterDict[letter][uri] > maxFreq:
        #         maxFreq = letterDict[letter][uri]
        #         uris = [uri]
        #     elif letterDict[letter][uri] == maxFreq:
        #         uris.append(uri)
        if uris:
            final_uris.append(uris[random.randint(0, len(uris) - 1)])

for uri in final_uris:
    track = sp.track(uri)
    print(track['name'])
