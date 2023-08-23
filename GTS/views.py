import json
import re

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Pub, Track, Artist


def pub_list(request):
    pubs = Pub.objects.all()
    pub_data = []
    for pub in pubs:
        member_count = pub.members.count()
        pub_data.append({
            'id': pub.id,
            'name': pub.name,
            'member_count': member_count,
            'max_members': pub.max_members,
            'game_type': pub.get_type_display(),
            'teams': pub.teams,
            'owner': pub.owner.username,
            'rounds': pub.rounds
        })

    return JsonResponse(pub_data, safe=False)


@api_view(['GET'])
def get_pub(request, pubId):  # Notice the parameter name change
    try:
        pub = Pub.objects.get(id=pubId)
        returnObject = {
            'id': pub.id,
            'name': pub.name,
            'game_type': pub.get_type_display(),
            'teams': pub.teams,
            'owner': pub.owner.username,
        }
        return JsonResponse(returnObject)
    except Pub.DoesNotExist:
        return JsonResponse({'error': 'Pub not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_pub(request):
    data = json.loads(request.body)
    pub_id = data.get('id')
    password = data.get('password')
    try:
        pub = Pub.objects.get(id=pub_id)
        if pub.password == password:
            return JsonResponse({'isAuthenticated': True, "userId": request.user.id})
    except:
        pass
    return JsonResponse({'isAuthenticated': False})


def remove_text(text):
    # Remove content within parentheses
    text = re.sub(r'\([^)]*\)', '', text)  # Remove content within ()
    text = re.sub(r'\[[^\]]*\]', '', text)  # Remove content within []
    text = re.sub(r'\{[^\}]*\}', '', text)  # Remove content within {}
    # Remove text after '-'
    text = text.split('-', 1)[0].strip()
    return text


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_pub(request):
    data = json.loads(request.body)
    pub_id = data.get("id")
    try:
        pub = Pub.objects.get(id=pub_id)  # Replace instance_id with the actual instance's ID you want to delete
        pub.delete()
    except Pub.DoesNotExist:
        pass
    return JsonResponse({'isAuthenticated': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_pub(request):
    data = json.loads(request.body)
    pub_name = data.get("name")
    pub_password = data.get('password')
    pub_type = data.get("type")
    pub_teams = data.get("teams")
    rounds = data.get("rounds")
    max_members = data.get("maxMembers")
    owner = request.user
    track_list = data.get("trackList")
    all_tracks = []
    for i, track in enumerate(track_list):
        track_object = None
        try:
            track_object = Track.objects.get(id=track['id'])
        except:
            pass
        if track_object:
            all_tracks.append(track_object)
            continue
        all_artists = []
        for artist in track['artists']:
            artist_object = None
            try:
                artist_object = Artist.objects.get(id=artist['id'])
            except:
                pass
            if artist_object:
                all_artists.append(artist_object)
                continue
            artist_object = Artist(id=artist['id'], name=artist['name'])
            artist_object.save()
            all_artists.append(artist_object)
        song_name = remove_text(track['name'])
        if len(song_name.strip()) < 1:
            song_name = [track['name']]

        album_cover = track['albumCover']['url']
        track_object = Track(id=track['id'], name=song_name, display_name=track['name'],
                             preview_url=track['previewUrl'], album_cover=album_cover)

        track_object.save()
        track_object.artists.set(all_artists)
        all_tracks.append(track_object)

    pub = Pub(name=pub_name, password=pub_password, type=pub_type, teams=pub_teams, owner=owner,
              max_members=max_members, rounds=rounds)
    try:
        pub.save()
        pub.track_list.set(all_tracks)
        print("Finished creating pub", pub.name, "returning", pub.id)
        return JsonResponse({'success': True, 'id': pub.id})
    except Exception as e:
        print(e)
    return JsonResponse({'success': False})


@api_view(['POST'])
def create_user(request):
    data = json.loads(request.body)
    username = data.get("username")
    password = data.get('password')
    user = User.objects.create_user(username=username, password=password)
    try:
        user.save()
        return JsonResponse({'success': True, 'id': user.id})
    except Exception as e:
        print(e)
    return JsonResponse({'success': False})


@api_view(['POST'])
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return JsonResponse({'message': 'Login successful', 'token': token.key})
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)


@api_view(['GET'])
def get_records(request):
    top_users = User.objects.annotate(num_fastest_guesser=Count('track')).order_by('-num_fastest_guesser')[:10]
    results = []
    for tu in top_users:
        results.append({"username": tu.username, "records": tu.num_fastest_guesser})
    return JsonResponse({"records": results})


@api_view(['GET'])
def get_time_records(request):
    lowest_values = Track.objects.order_by('fastest_guess')[:10]
    results = []
    for lv in lowest_values:
        results.append(
            {"username": lv.fastest_guesser.username, "song": lv.display_name, "artist": lv.artists.all()[0].name,
             "time": str(lv.fastest_guess) + "ms"})
    return JsonResponse({"records": results})
