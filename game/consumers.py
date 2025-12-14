import json
from channels.generic.websocket import AsyncWebsocketConsumer

# GLOBAL STATE
ROOMS = {}
class BattleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name'].upper()
        self.room_group_name = f'battle_{self.room_name}'
        self.user = self.scope["user"]

        if self.room_name not in ROOMS:
            ROOMS[self.room_name] = {
                "config": {"difficulty": "medium", "topics": ["mixed"], "mode": "timetrial"},
                "game_active": False,
                "players": {}
            }
        
        # capacity
        if len(ROOMS[self.room_name]["players"]) >= 5:
            await self.close()
            return

        # Join 
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        room = ROOMS.get(self.room_name)
        if room:
            if self.user.username in room["players"]:
                del room["players"][self.user.username]           
            if not room["players"]:
                del ROOMS[self.room_name]
            else:
                await self.broadcast_room_update()

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        room = ROOMS.get(self.room_name)

        if not room: return

        if action == 'join_lobby':
            is_first_player = (len(room["players"]) == 0)
            
            room["players"][self.user.username] = {
                "is_host": is_first_player,
                "is_ready": False,
                "score": 0,
                "hp": 60
            }
            
            await self.broadcast_room_update()
            await self.send_json({'type': 'settings_update', 'config': room['config']})

        elif action == 'update_status':
            is_ready = data.get('is_ready', False)
            if self.user.username in room["players"]:
                room["players"][self.user.username]['is_ready'] = is_ready
                await self.broadcast_room_update()

        elif action == 'update_settings':
            player_data = room["players"].get(self.user.username)
            if player_data and player_data['is_host']:
                room['config'] = data.get('config')
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'settings_propagate',
                        'config': room['config']
                    }
                )

        elif action == 'start_game':
            player_data = room["players"].get(self.user.username)
            print(f"[START_GAME] User: {self.user.username}, is_host: {player_data.get('is_host') if player_data else 'N/A'}")
            if player_data and player_data['is_host']:
                room['game_active'] = True
                print(f"[START_GAME] Broadcasting game_start_signal to room {self.room_name}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'game_start_signal'}
                )
            else:
                print(f"[START_GAME] Denied - Not host or player not found")

        elif action == 'attack':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_game_event',
                    'event': 'damage',
                    'attacker': self.user.username
                }
            )

        elif action == 'hp_update':
            hp = data.get('hp')
            if self.user.username in room["players"]:
                room["players"][self.user.username]['hp'] = hp
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_game_event',
                        'event': 'hp_sync',
                        'player': self.user.username,
                        'hp': hp
                    }
                )

        elif action == 'player_died':
            if self.user.username in room["players"]:
                room["players"][self.user.username]['is_dead'] = True
            
            print(f"[PLAYER_DIED] {self.user.username} died")
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_game_event',
                    'event': 'player_eliminated',
                    'player': self.user.username
                }
            )

            alive_players = [user for user, p in room["players"].items() if not p.get('is_dead', False)]
            print(f"[ALIVE_PLAYERS] {alive_players}")
            
            if len(alive_players) <= 1:
                # Game Over
                winner_name = alive_players[0] if alive_players else "No one"
                print(f"[GAME_OVER] Winner: {winner_name}")
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_game_event',
                        'event': 'game_over',
                        'winner': winner_name
                    }
                )
                
    #asybc calls to broadcast updates

    async def broadcast_room_update(self):
        room = ROOMS.get(self.room_name)
        if not room: return        
        player_list = []
        for username, p_data in room["players"].items():
            player_list.append({
                'username': username,
                'isHost': p_data['is_host'],
                'isReady': p_data['is_ready']
            })

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'room_state_message',
                'players': player_list
            }
        )

    async def room_state_message(self, event):
        await self.send_json({
            'type': 'room_update',
            'players': event['players']
        })

    async def settings_propagate(self, event):
        await self.send_json({
            'type': 'settings_update',
            'config': event['config']
        })

    async def game_start_signal(self, event):
        print(f"[GAME_START_SIGNAL] Sending to {self.user.username}")
        await self.send_json({'type': 'game_start'})

    async def broadcast_game_event(self, event):
        await self.send_json({
            'type': event['event'],
            'attacker': event.get('attacker'),
            'loser': event.get('loser'),
            'player': event.get('player'),
            'hp': event.get('hp'),
            'winner': event.get('winner')
        })

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))