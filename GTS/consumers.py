import json
import random
import time
from threading import Timer

import numpy as np
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from rest_framework.authtoken.models import Token

from .models import Pub


class ChatConsumer(WebsocketConsumer):

    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.consumer_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = 'chat_%s' % self.room_name

        if hasattr(self.channel_layer, "consumers"):
            if self.consumer_id in self.channel_layer.consumers:
                print("Kicked", self.consumer_id)
                self.accept()
                return
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.initialize()
        self.accept()
        if not hasattr(self.channel_layer, "timer"):
            self.channel_layer.timer = Timer(1, self.repeating_timer, args=[1, self.ping_clients]).start()

    def disconnect(self, close_code):
        # Leave room group
        if self.consumer_id in self.channel_layer.consumers:
            self.channel_layer.consumers.remove(self.consumer_id)
        print("Consumer", self.consumer_id, "disconnected", self.channel_layer.consumers)
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
        if hasattr(self, "user"):
            self.handle_disconnect()

    def receive(self, text_data):
        # Receive message from WebSocket
        text_data_json = json.loads(text_data)
        text = text_data_json['message']
        type = text_data_json['type']
        if type == "message":
            self.send_chat_message(text)
        elif type == "identify":
            self.handle_identify(text)
        elif type == "guess" and not self.channel_layer.round_over and not self.channel_layer.paused:
            self.handle_guess(text)
        elif type == "pause":
            self.channel_layer.paused = "true" in str(text).lower()
            self.update_pause_message()

    def update_score(self):
        score_board = []
        for user, points in self.channel_layer.user_score_dict.items():
            username = "Error"
            for u in self.channel_layer.users:
                if u["id"] == user:
                    username = u['username']
            score_board.append(
                {
                    "user": username,
                    "song": self.channel_layer.user_scored[user]['song'],
                    "artist": self.channel_layer.user_scored[user]['artist'],
                    "first": self.channel_layer.user_scored[user]['first'],
                    "confetti": self.channel_layer.user_scored[user]['confetti'],
                    "points": points,
                    "time": self.channel_layer.user_scored[user]['time']

                })
            self.channel_layer.user_scored[user]['confetti'] = False
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_points',
                'score_board': score_board,
            }
        )

    def jaccard_distance(self, word1, word2):
        set1 = set(word1)
        set2 = set(word2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        distance = 1.0 - intersection / union
        return distance

    def chat_message(self, event):
        text = event['message']
        self.send(text_data=json.dumps({
            'message': text,
            'type': 'chat_message'

        }))

    def game_update(self, event):
        text = event['message']
        round_over = event['round_over']
        self.send(text_data=json.dumps({
            'message': text,
            'type': 'game_update',
            'round_over': round_over

        }))

    def update_user_list(self, event):
        text = event['message']
        self.send(text_data=json.dumps({
            'message': text,
            'type': 'update_user_list'
        }))

    def update_guess_list(self, event):
        text = event['message']
        self.send(text_data=json.dumps({
            'message': text,
            'type': 'update_guess_list'
        }))

    def new_song(self, event):
        preview_url = event['preview_url']
        song = event['song']
        artists = event['artists']

        self.send(text_data=json.dumps({
            'song': song,
            'artists': artists,
            "preview_url": preview_url,
            'type': 'new_song'
        }))

    def correct_guess(self, event):
        song = event['song']
        artists = event['artists']
        user_id = event['userId']

        self.send(text_data=json.dumps({
            'song': song,
            'artists': artists,
            'type': 'correct_guess',
            'userId': user_id
        }))

    def end_round(self, event):
        song = event['song']
        artists = event['artists']
        fastest_guesser = event['fastest_guesser']
        fastest_guess = event['fastest_guess']
        album_cover = event['album_cover']

        self.send(text_data=json.dumps({
            'song': song,
            'artists': artists,
            'fastest_guesser': fastest_guesser,
            'fastest_guess': fastest_guess,
            'album_cover': album_cover,

            'type': 'end_round',
        }))

    def round_info(self, event):
        current_round = event['current_round']
        max_rounds = event['max_rounds']
        game_over = event['game_over']
        self.send(text_data=json.dumps({
            'current_round': current_round,
            'max_rounds': max_rounds,
            'game_over': game_over,
            'type': 'round_info'
        }))

    def update_points(self, event):
        score_board = event['score_board']

        self.send(text_data=json.dumps({
            'score_board': score_board,
            'type': 'update_points',
        }))

    def status_update(self, event):
        text = event['text']
        status = event['status']

        self.send(text_data=json.dumps({
            'text': text,
            'status': status,
            'type': 'status_update',
        }))

    def update_game_message(self, time, round_over):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'game_update',
                'message': time,
                'round_over': round_over

            }
        )

    def update_song_message(self):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'new_song',
                'preview_url': str(self.channel_layer.preview_url),
                'song': str(self.replace_letters_with_underscores(self.channel_layer.song)),
                'artists': [self.replace_letters_with_underscores(artist) for artist in
                            self.channel_layer.artists]
            }
        )

    def update_guess_list_message(self):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_guess_list',
                'message': [member for member in self.channel_layer.users if
                            member not in self.channel_layer.users_left_guessing],
            }
        )

    def end_round_message(self):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'end_round',
                'song': str(self.channel_layer.display_name),
                'album_cover': str(self.channel_layer.album_cover),
                'artists': [str(artist) for artist in
                            self.channel_layer.artists],
                'fastest_guesser': self.channel_layer.fastest_guesser,
                'fastest_guess': self.channel_layer.fastest_guess,
            }
        )

    def round_info_message(self):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'current_round': self.channel_layer.current_round,
                'max_rounds': self.channel_layer.pub.rounds,
                'game_over': self.channel_layer.current_round > self.channel_layer.pub.rounds,
                'type': "round_info"
            }
        )

    def update_user_list_message(self, pub):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_user_list',
                'message': [member.username for member in pub.members.all()],
            }
        )

    def send_chat_message(self, text):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': text,
            }
        )

    def correct_guess_message(self, song, artists):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'correct_guess',
                'song': song,
                'artists': artists,
                'userId': self.user.id
            }
        )

    def status_update_message(self, text, status):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'status_update',
                'text': text,
                'status': status,
            }
        )

    def score_users(self):
        song = str(self.replace_letters_with_underscores(self.channel_layer.song,
                                                         self.channel_layer.user_correct_guess_dict[
                                                             self.user.id]))
        artists = [self.replace_letters_with_underscores(artist, self.channel_layer.user_correct_guess_dict[
            self.user.id]) for artist in self.channel_layer.artists]
        self.correct_guess_message(song, artists)
        if "_" not in self.replace_letters_with_underscores(self.channel_layer.song.replace("_", ""),
                                                            self.channel_layer.user_correct_guess_dict[
                                                                self.user.id]) and not \
                self.channel_layer.user_scored[self.user.id]['song']:
            self.channel_layer.user_score_dict[self.user.id] += 1
            self.channel_layer.user_scored[self.user.id]['song'] = True
        guessed_all_artists = True
        for artist in self.channel_layer.artists:
            if "_" not in self.replace_letters_with_underscores(artist.replace("_", ""),
                                                                self.channel_layer.user_correct_guess_dict[
                                                                    self.user.id]):
                pass
            else:
                guessed_all_artists = False
        if guessed_all_artists and not self.channel_layer.user_scored[self.user.id]['artist']:
            self.channel_layer.user_score_dict[self.user.id] += 1
            self.channel_layer.user_scored[self.user.id]['artist'] = True
        if self.channel_layer.user_scored[self.user.id]['artist'] and \
                self.channel_layer.user_scored[self.user.id]['song'] and not \
                self.channel_layer.user_scored[self.user.id]['both']:
            self.channel_layer.user_scored[self.user.id]['both'] = True
            self.channel_layer.user_score_dict[self.user.id] += 2
            guess_time = np.round((time.time() * 1000) - (self.channel_layer.round_start_time * 1000))
            self.channel_layer.user_scored[self.user.id]['time'] = str(guess_time) + "ms"
            if self.channel_layer.first == True:
                self.channel_layer.user_scored[self.user.id]['first'] = True
                self.channel_layer.user_scored[self.user.id]['confetti'] = True
                guess_time = np.round((time.time() * 1000) - (self.channel_layer.round_start_time * 1000))
                if guess_time < self.channel_layer.fastest_guess:
                    print("New Record: " + self.user.username + " guessed in " + str(guess_time) + "ms")
                    self.channel_layer.song_object.fastest_guess = guess_time
                    self.channel_layer.song_object.fastest_guesser = self.user
                    self.channel_layer.fastest_guesser = self.user.username
                    self.channel_layer.fastest_guess = guess_time
                    self.channel_layer.song_object.save()
                    self.status_update_message(
                        "New Record: " + self.user.username + " guessed in " + str(guess_time) + "ms", "WARNING")
                self.channel_layer.user_score_dict[self.user.id] += 1
                self.channel_layer.first = False
        self.update_score()

    def handle_guess(self, text):
        song_parts = [self.channel_layer.song.lower()]
        if " " in self.channel_layer.song.strip():
            song_parts = self.channel_layer.song.lower().split(" ")
        for artist in self.channel_layer.artists:
            artist_parts = [artist.lower()]
            if " " in artist.lower():
                artist_parts = artist.split(" ")
            song_parts.extend(artist_parts)
        word_parts = [text.lower()]
        if (" " in text.strip().lower()):
            word_parts = text.split(" ")
        for word_part in word_parts:
            word_part = word_part.lower()
            for song_part in song_parts:
                distance = self.jaccard_distance(word_part.lower(), song_part.lower())
                if distance <= 0.4:
                    self.channel_layer.user_correct_guess_dict[self.user.id].append(song_part.lower())
        if len(self.channel_layer.user_correct_guess_dict[self.user.id]) > 0:
            self.score_users()

    def handle_identify(self, text):
        self.stopped = False
        for token in Token.objects.all():
            if str(token) == text:
                pub = Pub.objects.get(id=self.room_name)
                if len([member.username for member in pub.members.all()]) == 0 or not hasattr(self.channel_layer,
                                                                                              "admin"):
                    self.channel_layer.admin = token.user
                    print(token.user, "Adminized")
                pub.members.add(token.user)
                self.user = token.user
                print(self.user, "identified itself")
                self.channel_layer.user_correct_guess_dict[self.user.id] = []
                self.channel_layer.user_scored[self.user.id] = {"song": False, "artist": False, "both": False,
                                                                "first": False, "time": "-", "confetti": False}
                if self.user.id not in self.channel_layer.user_score_dict:
                    self.channel_layer.user_score_dict[self.user.id] = 0

                self.update_score()
                self.channel_layer.pub = pub
                print(token.user.username, "Joined")
                self.channel_layer.users.append({'username': token.user.username, "id": token.user.id})
                if token.user.username not in self.channel_layer.users_left_guessing:
                    self.channel_layer.users_left_guessing.append(token.user.username)
                self.update_user_list_message(pub)
                self.user = token.user
                self.round_info_message()
                if hasattr(self.channel_layer, "song") and hasattr(self.channel_layer,
                                                                   "round_over") and not self.channel_layer.round_over:
                    self.seek_to_song_message()
                    self.update_song_message()

        if not hasattr(self, "user"):
            print("Kicked someone")
            self.disconnect(1)

    def handle_disconnect(self):
        print(self.user, "Left")
        if self.user.id in self.channel_layer.user_score_dict:
            self.channel_layer.user_score_dict.pop(self.user.id)
        index = [user['username'] for user in self.channel_layer.users].index(self.user.username)

        del self.channel_layer.users[index]
        pub = Pub.objects.get(id=self.room_name)
        pub.members.remove(self.user)

        self.update_user_list_message(pub)

        self.update_score()
        if self.user == self.channel_layer.admin:
            if len(pub.members.all()) == 0:
                self.channel_layer.stopped = True
                self.stopped = True
                if hasattr(self.channel_layer, "timer"):
                    del self.channel_layer.timer
            else:
                self.channel_layer.admin = pub.members.all()[0]
                print(pub.members.all()[0], "Adminized")

    def initialize(self):
        self.stopped = False
        if not hasattr(self.channel_layer, 'round_over'):
            self.channel_layer.round_over = False
            self.channel_layer.paused = False
        if not hasattr(self.channel_layer, 'time_left'):
            self.channel_layer.time_left = 5
        self.channel_layer.stopped = False
        if not hasattr(self.channel_layer, "users"):
            self.channel_layer.users = []
        if not hasattr(self.channel_layer, "users_left_guessing"):
            self.channel_layer.users_left_guessing = []
        if not hasattr(self.channel_layer, "user_correct_guess_dict"):
            self.channel_layer.user_correct_guess_dict = {}
        if not hasattr(self.channel_layer, "user_score_dict"):
            self.channel_layer.user_score_dict = {}
            self.channel_layer.first = True
            self.channel_layer.user_scored = {}
            self.channel_layer.consumers = []
            self.channel_layer.history = []
            self.channel_layer.current_round = 1
        self.channel_layer.consumers.append(self.consumer_id)

    def get_new_song(self):
        print("Generating new song")
        if not hasattr(self.channel_layer, "pub"):
            print("Can't find the pub")
            return

        self.status_update_message("Picking a new song", "SUCCESS")

        song = random.sample(list(self.channel_layer.pub.track_list.all()), 1)[0]
        counter = 0
        while song.name in self.channel_layer.history:
            song = random.sample(list(self.channel_layer.pub.track_list.all()), 1)[0]
            if counter == 20:
                break
        self.channel_layer.history.append(song.name)
        self.channel_layer.song = song.name.replace("_", "")
        self.channel_layer.display_name = song.display_name
        self.channel_layer.fastest_guess = song.fastest_guess
        self.channel_layer.song_object = song
        if song.fastest_guesser:
            self.channel_layer.fastest_guesser = song.fastest_guesser.username
        else:
            self.channel_layer.fastest_guesser = ""
        self.channel_layer.artists = [artist.name for artist in song.artists.all()]
        self.channel_layer.preview_url = song.preview_url
        self.channel_layer.album_cover = song.album_cover

        self.channel_layer.first = True
        for user in self.channel_layer.users:
            self.channel_layer.user_correct_guess_dict[user['id']] = []
            self.channel_layer.user_scored[user['id']] = {"song": False, "artist": False, "both": False, "first": False,
                                                          "confetti": False, "time": "-"}

        print("New song:", self.channel_layer.song, " |-| ", " |-| ".join(self.channel_layer.artists))
        self.update_guess_list_message()

    def repeating_timer(self, interval, function):
        if self.channel_layer.pub and str(self.channel_layer.pub.owner.username) in [user['username'] for user in
                                                                                     self.channel_layer.users] and not self.stopped and not self.channel_layer.stopped:
            function()
        else:
            self.update_game_message("0", "True")
            self.status_update_message("Owner not in the Pub", "ERROR")

        if not self.channel_layer.stopped and len(
                list(self.channel_layer.pub.members.all())) > 0 and not self.stopped and not self.channel_layer.stopped:
            self.channel_layer.timer = Timer(interval, self.repeating_timer, args=[interval, function]).start()
        elif hasattr(self.channel_layer, "timer"):
            del self.channel_layer.timer

    def ping_clients(self):
        if self.channel_layer.pub.owner.username in [user['username'] for user in
                                                     self.channel_layer.users] and not self.channel_layer.paused:
            self.channel_layer.time_left -= 1
        if self.channel_layer.time_left < 0 and not self.channel_layer.round_over:
            self.channel_layer.round_over = True
            self.channel_layer.time_left = 5
            if hasattr(self.channel_layer, "song"):
                self.channel_layer.current_round += 1
                self.end_round_message()
                self.round_info_message()

                if self.channel_layer.current_round > self.channel_layer.pub.rounds:
                    self.channel_layer.current_round = 1
                    self.channel_layer.time_left = 10

                    self.reset_server()
                    self.channel_layer.paused = True
                    self.update_pause_message()
            self.get_new_song()
        if self.channel_layer.round_over:
            if self.channel_layer.time_left < 0:
                self.round_info_message()
                self.channel_layer.time_left = 30
                self.channel_layer.round_over = False
                self.channel_layer.round_start_time = time.time()
                if hasattr(self.channel_layer, "preview_url"):
                    self.update_song_message()
                    self.update_score()
                self.status_update_message("New song picked! Good luck!", "SUCCESS")
        self.update_game_message(str(self.channel_layer.time_left), str(self.channel_layer.round_over))

    def replace_letters_with_underscores(self, input_string, exclude_words=None):
        if exclude_words is None:
            exclude_words = []
        exclude_words = [eword.lower() for eword in exclude_words]
        words = input_string.split()
        result = []
        for word in words:
            inner_result = []
            if word.lower() in exclude_words:
                result.append(word)
            else:
                for letter in word:
                    if letter.isalpha():
                        inner_result.append("_")
                    else:
                        inner_result.append(letter)
            result.append(''.join(inner_result))
        cleaned_text = ' '.join(result)
        return cleaned_text

    def update_pause_message(self):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_pause',
                'paused': self.channel_layer.paused,
            }
        )

    def update_pause(self, event):
        paused = event['paused']
        self.send(text_data=json.dumps({
            'type': 'update_pause',
            'paused': paused
        }))

    def reset_server(self):
        self.channel_layer.user_correct_guess_dict = {}
        self.channel_layer.first = True
        for key in self.channel_layer.user_correct_guess_dict.keys():
            self.channel_layer.user_correct_guess_dict[key] = []
        for key in self.channel_layer.user_scored.keys():
            self.channel_layer.user_scored[key] = {"song": False, "artist": False, "both": False,
                                                   "first": False, "time": "-", "confetti": False}
        for key in self.channel_layer.user_score_dict.keys():
            self.channel_layer.user_score_dict[key] = 0
        self.channel_layer.current_round = 1

    def seek_to_song_message(self):
        print(self.user)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'seek_to_song',
                'paused': self.channel_layer.paused,
                'preview_url': self.channel_layer.preview_url,
                'seek': self.channel_layer.time_left,
                'user_id': self.user.id
            }
        )

    def seek_to_song(self, event):
        paused = event['paused']
        preview_url = event['preview_url']
        seek = event['seek']
        userId = event['user_id']
        self.send(text_data=json.dumps({
            'type': 'seek_to_song',
            'paused': paused,
            'preview_url': preview_url,
            'seek': seek,
            'user_id': userId
        }))
