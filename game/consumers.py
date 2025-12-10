import json
from channels.generic.websocket import AsyncWebsocketConsumer

ROOM_COUNTS = {}

class BattleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'battle_{self.room_name}'
        self.user = self.scope["user"]

        current_count = ROOM_COUNTS.get(self.room_name, 0)
        if current_count >= 2:
            await self.close()
            return

        ROOM_COUNTS[self.room_name] = current_count + 1
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        if current_count == 0:
            await self.send(text_data=json.dumps({'type': 'status', 'message': 'waiting'}))
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_start_signal',
                    'opponent': self.user.username 
                }
            )

    async def disconnect(self, close_code):
        if self.room_name in ROOM_COUNTS:
            ROOM_COUNTS[self.room_name] -= 1
            if ROOM_COUNTS[self.room_name] <= 0:
                del ROOM_COUNTS[self.room_name]
        
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'attack':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_attack',
                    'attacker': self.user.username
                }
            )
        
        elif action == 'hp_update':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_hp_update',
                    'player': self.user.username,
                    'hp': data.get('hp', 60)
                }
            )
        
        elif action == 'player_died':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_game_over',
                    'loser': self.user.username
                }
            )

    async def game_start_signal(self, event):
        await self.send(text_data=json.dumps({'type': 'game_start'}))

    async def broadcast_attack(self, event):
        await self.send(text_data=json.dumps({
            'type': 'damage',
            'attacker': event['attacker']
        }))

    async def broadcast_hp_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'hp_update',
            'player': event['player'],
            'hp': event['hp']
        }))

    async def broadcast_game_over(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_over',
            'loser': event['loser']
        }))