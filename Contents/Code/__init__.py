"""
Hitbox.tv Plugin

@author Richard Kuhnt (r15ch13)
@link https://github.com/r15ch13/Hitbox.tv.bundle
@license MIT License (http://r15ch13.mit-license.org/)
"""

import re
import urllib2
import urllib2_new

NAME            = "Hitbox.tv"
ART             = "art-default.png"
ICON            = "icon-default.png"

HITBOX_PAGE_URL     = "https://www.hitbox.tv"
HITBOX_STATIC_URL   = "https://edge.sf.hitbox.tv"
HITBOX_AUTH_TOKEN   = "https://api.hitbox.tv/auth/token"
HITBOX_USER_INFO    = "https://api.hitbox.tv/user"
HITBOX_TEAMS        = "https://api.hitbox.tv/teams"
HITBOX_TEAM         = "https://api.hitbox.tv/team"
HITBOX_TOP_GAMES    = "https://api.hitbox.tv/games"
HITBOX_LIVE_LIST    = "https://api.hitbox.tv/media/live/list"
HITBOX_VIDEO_LIST   = "https://api.hitbox.tv/media/video/list"

PAGE_LIMIT = 50
SEARCH_LIMIT = 30

####################################################################################################
def Start():
    ObjectContainer.title1 = NAME
    ObjectContainer.art = R(ART)
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)

    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36'
    HTTP.CacheTime = 120

####################################################################################################
@handler('/video/hitbox', NAME)
def MainMenu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(PopularStreamsMenu), title=L("Popular Streams"), summary=L("Browse Popular Streams")))
    oc.add(DirectoryObject(key=Callback(GamesMenu), title=L("Games"), summary=L("Browse Live Streams by Game")))
    oc.add(DirectoryObject(key=Callback(FollowingMenu), title=L("Following"), summary=L("Browse Live Streams you're following (Login required)")))
    oc.add(DirectoryObject(key=Callback(TeamsMenu), title=L("My Teams"), summary=L("Browse Live Streams of your Teams (Login required)")))
    oc.add(DirectoryObject(key=Callback(RecordingsMenu), title=L("Recordings"), summary=L("Recordings from last week")))
    oc.add(InputDirectoryObject(key=Callback(SearchResults), title="Search", prompt="Search for a Stream", summary="Search for a Stream"))
    oc.add(PrefsObject(title=L('Preferences')))
    Log.Info('MainMenu')
    return oc

####################################################################################################
@route('/video/hitbox/popular')
def PopularStreamsMenu():

    oc = ObjectContainer(title2=L("Popular Streams"), no_cache=True)

    try:
        if Prefs['countryFilterPopular']:
            json = JSON.ObjectFromURL("%s?limit=%s&countries=%s" % (HITBOX_LIVE_LIST, PAGE_LIMIT, Prefs['countryFilter']))
        else:
            json = JSON.ObjectFromURL("%s?limit=%s" % (HITBOX_LIVE_LIST, PAGE_LIMIT))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No live streams found."))

    for stream in json['livestream']:
        channel_link = stream['channel']['channel_link']
        display_name = stream['media_display_name']
        game = stream['category_name']
        status = stream['media_status']
        viewers = stream['media_views']

        thumb = ""
        if stream['media_thumbnail'] is not None:
            thumb = HITBOX_STATIC_URL + stream['media_thumbnail']

        countries = ""
        if stream['media_countries'] is not None:
            countries = ", ".join(stream['media_countries'])

        title = '%s - %s' % (display_name, game)
        if countries is not "":
            title = '%s - %s [%s]' % (display_name, game, countries)

        oc.add(VideoClipObject(
            url = channel_link,
            title = title,
            summary = '%s\n\n%s Viewers' % (status, viewers),
            tagline = status,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    return oc

####################################################################################################
@route('/video/hitbox/following')
def FollowingMenu():

    if not IsLoggedIn():
        return MessageContainer(NAME, L("Please provide your login credentials in the plugin preferences."))

    oc = ObjectContainer(title2=L("Following"), no_cache=True)

    try:
        json = JSON.ObjectFromURL("%s?follower_id=%s&media=true&size=mid" % (HITBOX_LIVE_LIST, GetUserId()))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No live streams found."))

    for stream in json['livestream']:
        channel_link = stream['channel']['channel_link']
        display_name = stream['media_display_name']
        game = stream['category_name']
        status = stream['media_status']
        viewers = stream['media_views']

        thumb = ""
        if stream['media_thumbnail'] is not None:
            thumb = HITBOX_STATIC_URL + stream['media_thumbnail']

        oc.add(VideoClipObject(
            url = channel_link,
            title = '%s - %s' % (display_name, game),
            summary = '%s\n\n%s Viewers' % (status, viewers),
            tagline = status,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    return oc

####################################################################################################
@route('/video/hitbox/teams')
def TeamsMenu():

    if not IsLoggedIn():
        return MessageContainer(NAME, L("Please provide your login credentials in the plugin preferences."))

    oc = ObjectContainer(title2 = L("My Teams"), no_cache=True)

    try:
        json = JSON.ObjectFromURL("%s/%s?authToken=%s&nocache=true" % (HITBOX_TEAMS, Prefs['username'], GetAuthToken()))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No teams found."))

    for team in json['teams']:
        Log.Info(team)
        thumb = ""
        if team['info']['group_logo_large'] is not None:
            thumb = HITBOX_STATIC_URL + team['info']['group_logo_large']
        if team['info']['group_logo_small'] is not None:
            thumb = HITBOX_STATIC_URL + team['info']['group_logo_small']

        oc.add(TVShowObject(
            key = Callback(
                TeamStreamsMenu,
                group_display_name = team['info']['group_display_name'],
                group_name = team['info']['group_name'],
                group_id = team['info']['group_id']
            ),
            rating_key = team['info']['group_id'],
            title = team['info']['group_display_name'],
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))
    return oc

####################################################################################################
@route('/video/hitbox/team/streams')
def TeamStreamsMenu(group_display_name, group_name, group_id):

    oc = ObjectContainer(title2 = group_display_name, no_cache=True)

    try:
        json = JSON.ObjectFromURL("%s/%s?liveonly=true&media=true&media_name=list&media_type=live&size=mid" % (HITBOX_TEAM, group_name))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No live streams found."))

    for stream in json['media']['livestream']:
        channel_link = stream['channel']['channel_link']
        display_name = stream['media_display_name']
        game = stream['category_name']
        status = stream['media_status']
        viewers = stream['media_views']

        thumb = ""
        if stream['media_thumbnail'] is not None:
            thumb = HITBOX_STATIC_URL + stream['media_thumbnail']

        oc.add(VideoClipObject(
            url = channel_link,
            title = '%s: %s - %s' % (L('Live'), display_name, game),
            summary = '%s\n\n%s Viewers' % (status, viewers),
            tagline = status,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    for video in json['media']['video']:
        video_link = "%s/video/%s" % (HITBOX_PAGE_URL, video['media_id'])

        display_name = video['media_display_name']
        game = video['category_name']
        status = video['media_status']
        viewers = video['media_views']

        thumb = ""
        if video['media_thumbnail'] is not None:
            thumb = HITBOX_STATIC_URL + video['media_thumbnail']

        oc.add(VideoClipObject(
            url = video_link,
            title = '%s: %s - %s' % (L('Video'), display_name, game),
            summary = '%s\n\n%s Views' % (status, viewers),
            tagline = status,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))


    if len(oc) < 1:
        return MessageContainer(NAME, L("No streams or vidoes were found."))

    return oc

####################################################################################################
@route('/video/hitbox/games')
def GamesMenu():

    oc = ObjectContainer(title2 = L("Games"), no_cache=True)

    try:
        json = JSON.ObjectFromURL("%s?liveonly=true" % HITBOX_TOP_GAMES)
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No games found."))

    for game in json['categories']:
        thumb = ""
        if game['category_logo_large'] is not None:
            thumb = HITBOX_STATIC_URL + game['category_logo_large']

        oc.add(TVShowObject(
            key = Callback(
                GameStreamsMenu,
                category_name = game['category_name'],
                category_id = game['category_id']
            ),
            summary = '%s Viewers' % str(game['category_viewers']),
            rating_key = game['category_id'],
            title = game['category_name'],
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))
    return oc

####################################################################################################
@route('/video/hitbox/game/streams')
def GameStreamsMenu(category_name, category_id):

    oc = ObjectContainer(title2 = category_name, no_cache=True)

    try:
        if Prefs['countryFilterGames']:
            json = JSON.ObjectFromURL("%s?game=%s&countries=%s" % (HITBOX_LIVE_LIST, category_id, Prefs['countryFilter']))
        else:
            json = JSON.ObjectFromURL("%s?game=%s" % (HITBOX_LIVE_LIST, category_id))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No live streams found."))

    for stream in json['livestream']:
        channel_link = stream['channel']['channel_link']
        display_name = stream['media_display_name']
        game = stream['category_name']
        status = stream['media_status']
        viewers = stream['media_views']

        thumb = ""
        if stream['media_thumbnail'] is not None:
            thumb = HITBOX_STATIC_URL + stream['media_thumbnail']

        countries = ""
        if stream['media_countries'] is not None:
            countries = ", ".join(stream['media_countries'])

        title = '%s - %s' % (display_name, game)
        if countries is not "":
            title = '%s - %s [%s]' % (display_name, game, countries)

        oc.add(VideoClipObject(
            url = channel_link,
            title = title,
            summary = '%s\n\n%s Viewers' % (status, viewers),
            tagline = status,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    return oc

####################################################################################################
@route('/video/hitbox/recordings')
def RecordingsMenu():

    oc = ObjectContainer(title2=L("Recordings"), no_cache=True)

    try:
        json = JSON.ObjectFromURL("%s?limit=%s&filter=weekly" % (HITBOX_VIDEO_LIST, PAGE_LIMIT))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        return MessageContainer(NAME, L("No videos found."))

    for video in json['video']:

        video_link = "%s/video/%s" % (HITBOX_PAGE_URL, video['media_id'])
        display_name = video['media_display_name']
        game = video['category_name']
        status = video['media_status']
        viewers = video['media_views']

        thumb = ""
        if video['media_thumbnail'] is not None:
            thumb = HITBOX_STATIC_URL + video['media_thumbnail']

        countries = ""
        if video['media_countries'] is not None:
            countries = ", ".join(video['media_countries'])

        title = '%s - %s' % (display_name, status)
        if countries is not "":
            title = '%s - %s [%s]' % (display_name, status, countries)

        oc.add(VideoClipObject(
            url = video_link,
            title = title,
            summary = '%s\n%s\n\n%s Viewers' % (game, status, viewers),
            tagline = status,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    return oc

####################################################################################################
def SearchResults(query=''):

    oc = ObjectContainer(no_cache=True)

    stream_results = ""
    try:
        stream_results = JSON.ObjectFromURL("%s?filter=popular&limit=%s&media=true&search=%s&size=list" % (HITBOX_LIVE_LIST, SEARCH_LIMIT, String.Quote(query, usePlus=True)))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        pass

    if 'livestream' in stream_results:
        for stream in stream_results['livestream']:
            channel_link = stream['channel']['channel_link']
            display_name = stream['media_display_name']
            game = stream['category_name']
            status = stream['media_status']
            viewers = stream['media_views']

            thumb = ""
            if stream['media_thumbnail'] is not None:
                thumb = HITBOX_STATIC_URL + stream['media_thumbnail']

            oc.add(VideoClipObject(
                url = channel_link,
                title = '%s: %s - %s' % (L('Live'), display_name, game),
                summary = '%s\n\n%s Viewers' % (status, viewers),
                tagline = status,
                thumb = Resource.ContentsOfURLWithFallback(thumb)
            ))

    video_results = ""
    try:
        video_results = JSON.ObjectFromURL("%s?filter=popular&limit=%s&media=true&search=%s&size=list" % (HITBOX_VIDEO_LIST, SEARCH_LIMIT, String.Quote(query, usePlus=True)))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        pass

    if 'video' in video_results:
        for video in video_results['video']:
            video_link = "%s/video/%s" % (HITBOX_PAGE_URL, video['media_id'])

            display_name = video['media_display_name']
            game = video['category_name']
            status = video['media_status']
            viewers = video['media_views']

            thumb = ""
            if video['media_thumbnail'] is not None:
                thumb = HITBOX_STATIC_URL + video['media_thumbnail']

            oc.add(VideoClipObject(
                url = video_link,
                title = '%s: %s - %s' % (L('Video'), display_name, game),
                summary = '%s\n\n%s Views' % (status, viewers),
                tagline = status,
                thumb = Resource.ContentsOfURLWithFallback(thumb)
            ))


    if len(oc) < 1:
        return MessageContainer(NAME, L("No streams or vidoes were found that match your query."))

    return oc

####################################################################################################
def ValidatePrefs():

    Logout()
    Login()

    if IsLoggedIn():
        Log.Info("Hitbox.bundle ----> Login successful!")
        return MessageContainer(NAME, "Login successful!")
    else:
        Log.Error("Hitbox.bundle ----> Login: Username or password wrong! Try again...")
        return MessageContainer(NAME, "Username or password wrong! Try again...")

####################################################################################################
def Login():
    if 'authToken' not in Dict and 'userId' not in Dict:
        json = ""
        try:
            json = JSON.ObjectFromURL(
                url = HITBOX_AUTH_TOKEN,
                values = {
                    "login": Prefs['username'],
                    "pass": Prefs['password'],
                    "app": "desktop",
                }
            )
        except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
            Log.Error("Hitbox.bundle ----> Username or password wrong! Try again...")
            return MessageContainer(NAME, "Username or password wrong! Try again...")

        if 'authToken' in json:
            Dict['authToken'] = json['authToken']
            Dict.Save()

            Dict['userId'] = LoadUserId()
            Dict.Save()
        else:
            Logout()
            Log.Error("Hitbox.bundle ----> Something in the login process went wrong. Error response was: "+ str(json))
    else:
        Logout()
        Log.Error("Hitbox.bundle ----> Something in the login process went wrong.")

####################################################################################################
def LoadUserId():
    json = ""
    try:
        json = JSON.ObjectFromURL("%s/%s?authToken=%s&nocache=true" % (HITBOX_USER_INFO, Prefs['username'], GetAuthToken()))
    except(urllib2.HTTPError, urllib2_new.HTTPError, ValueError), err:
        Log.Error("Hitbox.bundle ----> invalid auth token")

    if 'user_id' in json:
        return json['user_id']
    return ""

####################################################################################################
def Logout():
    if 'authToken' in Dict:
        del Dict['authToken']
    if 'userId' in Dict:
        del Dict['userId']

####################################################################################################
def GetAuthToken():
    if 'authToken' in Dict:
        return Dict['authToken']
    return ""

####################################################################################################
def GetUserId():
    if 'userId' in Dict:
        return Dict['userId']
    return ""

####################################################################################################
def IsLoggedIn():
    return ('authToken' in Dict and Dict['authToken'] != "" and 'userId' in Dict and Dict['userId'] != "")
