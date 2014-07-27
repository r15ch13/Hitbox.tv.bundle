"""
Hitbox.tv Plugin

@author Richard Kuhnt (r15ch13)
@link https://github.com/r15ch13/Hitbox.tv.bundle
@license MIT License (http://r15ch13.mit-license.org/)
"""

import re
import urllib2

PLUGIN_TITLE    = "Hitbox.tv"
PLUGIN_PREFIX   = "/video/hitbox.tv"

ART             = "art-default.png"
ICON            = "icon-default.png"

API_BASE        = "http://api.hitbox.tv/"
STATIC_BASE     = "http://edge.hitbox.tv"
PLAYER_API      = "http://www.hitbox.tv/api/player/config/{0}/{1}?embed=false&showHidden=true"
SWF_BASE        = "http://edge.vie.hitbox.tv/static/player/flowplayer/"
SWF_URL         = SWF_BASE + "flowplayer.commercial-3.2.16.swf"
RTMP_URL        = "rtmp://fml.B6BF.edgecastcdn.net/20B6BF"


def Start():

    Plugin.AddViewGroup('InfoList', viewMode = 'InfoList', mediaType = 'items')
    Plugin.AddViewGroup('List', viewMode = 'List', mediaType = 'items')

    ObjectContainer.title1 = L(PLUGIN_TITLE)
    ObjectContainer.art = R(ART)
    ObjectContainer.view_group = 'List'

    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)


@handler(PLUGIN_PREFIX, L(PLUGIN_TITLE), thumb=ICON, art=ART)
def MainMenu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(Popular), title=L("Popular")))
    oc.add(DirectoryObject(key=Callback(Following), title=L("Following")))
    oc.add(DirectoryObject(key=Callback(GamesList), title=L("Games")))
    oc.add(PrefsObject(title=L('Preferences')))
    return oc


def ValidatePrefs():

    Logout()
    Login()

    if IsLoggedIn():
        Log.Info("Hitbox.bundle ----> Login successful!")
        return MessageContainer(L(PLUGIN_TITLE), "Login successful!")
    else:
        Log.Error("Hitbox.bundle ----> Login: Username or password wrong! Try again...")
        return MessageContainer(L(PLUGIN_TITLE), "Username or password wrong! Try again...")


def Login():
    if 'authToken' not in Dict and 'userId' not in Dict:
        json = ""
        try:
            json = JSON.ObjectFromURL(
                url = API_BASE + "auth/token",
                values = {
                    "login": Prefs['username'],
                    "pass": Prefs['password'],
                    "app": "desktop",
                }
            )
        except(urllib2.HTTPError, ValueError), err:
            Log.Error("Hitbox.bundle ----> Username or password wrong! Try again...")
            return MessageContainer(L(PLUGIN_TITLE), "Username or password wrong! Try again...")

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


def LoadUserId():
    json = ""
    try:
        json = JSON.ObjectFromURL(url = API_BASE + "user/" + Prefs['username'] + "?authToken=" + GetAuthToken() + "&nocache=true")
    except(urllib2.HTTPError, ValueError), err:
        Log.Error("Hitbox.bundle ----> invalid auth token")

    if 'user_id' in json:
        return json['user_id']
    return ""


def Logout():
    if 'authToken' in Dict:
        del Dict['authToken']
    if 'userId' in Dict:
        del Dict['userId']


def GetAuthToken():
    if 'authToken' in Dict:
        return Dict['authToken']
    return ""


def GetUserId():
    if 'userId' in Dict:
        return Dict['userId']
    return ""


def IsLoggedIn():
    return ('authToken' in Dict and Dict['authToken'] != "" and 'userId' in Dict and Dict['userId'] != "")


@route(PLUGIN_PREFIX+'/games')
def GamesList():

    oc = ObjectContainer(view_group = "List", title2 = L("Games"))

    try:
        json = JSON.ObjectFromURL(url = API_BASE + "games?liveonly=true", cacheTime = 30)
    except(urllib2.HTTPError, ValueError), err:
        Log.Error(err)
        return MessageContainer(L(PLUGIN_TITLE), L("No games found."))

    for game in json['categories']:
        oc.add(TVShowObject(
            key = Callback(
                GamesLive,
                category_name = game['category_name'],
                category_id = game['category_id']
            ),
            rating_key = game['category_id'],
            title = game['category_name'],
            thumb = STATIC_BASE + game['category_logo_large']
        ))
    return oc


@route(PLUGIN_PREFIX+'/games/live')
def GamesLive(category_name, category_id):

    oc = ObjectContainer(view_group = "List", title2 = category_name)

    try:
        json = JSON.ObjectFromURL(url = API_BASE + "media/live/list?game=" + category_id, cacheTime = 30)
    except(urllib2.HTTPError, ValueError), err:
        Log.Error(err)
        return MessageContainer(L(PLUGIN_TITLE), L("No live streams found."))

    for stream in json['livestream']:
        oc.add(DirectoryObject(
            key = Callback(
                PlayStream,
                category_name = stream['category_name'],
                media_display_name = stream['media_display_name'],
                media_status = stream['media_status'],
                media_name = stream['media_name'],
                media_thumbnail = STATIC_BASE + stream['media_thumbnail'],
                media_views = stream['media_views'],
                video_url = RTMP_URL
            ),
            title = stream['media_display_name'],
            summary = stream['media_status'],
            thumb = STATIC_BASE + stream['channel']['user_logo']
        ))

    return oc


@route(PLUGIN_PREFIX+'/popular')
def Popular():

    oc = ObjectContainer(view_group = "InfoList", title2=L("Popular"))

    try:
        json = JSON.ObjectFromURL(url = API_BASE + "media/live/list", cacheTime = 30)
    except(urllib2.HTTPError, ValueError), err:
        Log.Error(err)
        return MessageContainer(L(PLUGIN_TITLE), L("No live streams found."))

    for stream in json['livestream']:

        oc.add(VideoClipObject(
            key = Callback(
                PlayStream,
                category_name = stream['category_name'],
                media_display_name = stream['media_display_name'],
                media_status = stream['media_status'],
                media_name = stream['media_name'],
                media_thumbnail = STATIC_BASE + stream['media_thumbnail'],
                media_views = stream['media_views'],
                video_url = RTMP_URL
            ),
            rating_key=stream['media_name'],
            title = str(stream['category_name']) + ": " + stream['media_display_name'],
            tagline = stream['media_status'],
            summary="<u>"+str(stream['category_name']) + "</u>\n\n" + L("Live with %s Viewers" % stream['media_views']),
            thumb = STATIC_BASE + stream['media_thumbnail']
        ))

    return oc


@route(PLUGIN_PREFIX+'/following')
def Following():

    if not IsLoggedIn():
        return MessageContainer(L(PLUGIN_TITLE), L("Please provide your login credentials in the plugin preferences."))

    oc = ObjectContainer(view_group = "InfoList", title2=L("Following"))

    try:
        json = JSON.ObjectFromURL(url = API_BASE + "media/live/list?follower_id=" + GetUserId() + "&media=true&size=mid", cacheTime = 30)
    except(urllib2.HTTPError, ValueError), err:
        Log.Error(err)
        return MessageContainer(L(PLUGIN_TITLE), L("No live streams found."))

    for stream in json['livestream']:

        oc.add(VideoClipObject(
            key = Callback(
                PlayStream,
                category_name = stream['category_name'],
                media_display_name = stream['media_display_name'],
                media_status = stream['media_status'],
                media_name = stream['media_name'],
                media_thumbnail = STATIC_BASE + stream['media_thumbnail'],
                media_views = stream['media_views'],
                video_url = RTMP_URL
            ),
            rating_key=stream['media_name'],
            title = str(stream['category_name']) + ": " + stream['media_display_name'],
            tagline = stream['media_status'],
            summary="<u>"+str(stream['category_name']) + "</u>\n\n" + L("Live with %s Viewers" % stream['media_views']),
            thumb = STATIC_BASE + stream['media_thumbnail']
        ))

    return oc


@route(PLUGIN_PREFIX+'/play')
def PlayStream(video_url, category_name, media_name, media_display_name = '', media_status = '', media_thumbnail = '', media_views = 0):

    oc = ObjectContainer(title2 = media_display_name)

    call_args = {
        "category_name": category_name,
        "media_display_name": media_display_name,
        "media_status": media_status,
        "media_name": media_name,
        "media_thumbnail": media_thumbnail,
        "media_views": media_views,
        "video_url": video_url,
    }

    rtmpVid = RTMPVideoURL(url=video_url, clip=media_name, swf_url=SWF_URL, live=True)

    vco = VideoClipObject(
        key=Callback(PlayStream, **call_args),
        rating_key=media_name,
        title = str(category_name) + ": " + media_display_name,
        tagline = media_status,
        summary="<u>"+str(category_name) + "</u>\n\n" + L("Live with %s Viewers" % media_views),
        thumb=media_thumbnail,
        items=[
            MediaObject(
                parts=[
                    PartObject(
                        key=rtmpVid
                    )
                ]
            )
        ]
    )

    oc.add(vco)
    return oc
