import utils
import time

sp = utils.spotipySetup('playlist-read-private playlist-read-collaborative user-read-playback-state')

days = int(input("How many days back would you like to go? "))

recents = []

currently_playing = sp.current_playback()['is_playing']

while days > 0:
    startTime = int((time.time()-14400) / 86400) * 86400 + 14400 - (86400 * days)
    endTime = startTime + 86400
    nextSet = utils.getRecentTracks(startTime, endTime)
    print(f'Collecting lastfm data... Got {len(nextSet)} tracks from {days} days back')
    if nextSet:
        recents.extend(utils.getRecentTracks(startTime, endTime)[1 if currently_playing else 0:])  # every lastfm api call returns the currently playing track, so remove if currently playing
    days -= 1

recentDict = {}
for recent in recents:
    nameAndArtist = f'{recent['name']}~{recent['artist']['#text']}'.lower()
    if nameAndArtist in recentDict:
        recentDict[nameAndArtist] += 1
    else:
        recentDict[nameAndArtist] = 1

# for key in recentDict:
#     splitKey = key.split('~')
#     if len(splitKey) > 2:
#         print(f"Song has tilde WHY. Anyway it's {key} and you listened to it {recentDict[key]} times.")
#     else:
#         print(f'Listened to {splitKey[0]} by {splitKey[1]} {recentDict[key]} time{"" if recentDict[key] == 1 else "s"}.')

playlists = sp.current_user_playlists()
offset = 50
while offset < playlists['total']:
    playlists.extend(sp.current_user_playlists(offset=offset))

for playlist in playlists['items']:
    print("~" * 200)
    print("~" * 200)
    name = playlist['name']
    uri = playlist['uri']

    analyze = input(f'Analyze playlist "{name}"? (y/n/s to skip all) ')
    while analyze != 'y' and analyze != 'n' and analyze != 's':
        analyze = input(f'You idiot.\nAnalyze playlist "{name}"? (y/n/s to skip all) ')

    if analyze == 's':
        break
    elif analyze == 'n':
        continue

    total_tracks = sp.playlist_items(uri)['total']

    offset = 0
    tracks = []
    while offset < total_tracks:
        print(f"Getting tracks {offset}-{offset+99} from {name}")
        tracks.extend(sp.playlist_tracks(uri, offset=offset)['items'])
        offset += 100

    print(f"Analyzing {len(tracks)} tracks from playlist{name}")

    leastPlays = 1000000
    mostPlays = 0
    leastList = []
    mostList = []

    for track in tracks:
        trackName = track['track']['name']
        trackArtist = track['track']['artists'][0]['name']
        trackId = track['track']['uri']
        code = f'{trackName}~{trackArtist}'.lower()
        if code in recentDict:
            frequency = recentDict[code]
            if frequency > mostPlays:
                mostPlays = frequency
                mostList = [f'{trackName} by {trackArtist}']
            elif frequency == mostPlays:
                mostList.append(f'{trackName} by {trackArtist}')
            if frequency < leastPlays:
                leastPlays = frequency
                leastList = [f'{trackName} by {trackArtist}']
            elif frequency == leastPlays:
                leastList.append(f'{trackName} by {trackArtist}')
        else:
            if leastPlays > 0:
                leastList = [f'{trackName} by {trackArtist}']
            else:
                leastList.append(f'{trackName} by {trackArtist}')
            leastPlays = 0
    print(f'The most times any song was played was {mostPlays}\nThose were: ')
    for track in mostList:
        print(track)
    print(f'The least times any song was played was {leastPlays}\nThose were: ')
    for track in leastList:
        print(track)
