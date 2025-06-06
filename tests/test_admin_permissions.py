import os
import sqlite3
import asyncio
import unittest

from cogs.alliance_member_operations import AllianceMemberOperations

class DummyUser:
    def __init__(self, user_id, name="Admin"):
        self.id = user_id
        self.name = name

class DummyResponse:
    def __init__(self):
        self.messages = []
    async def send_message(self, content=None, **kwargs):
        self.messages.append(content)

class DummyInteraction:
    def __init__(self, user_id, guild_id=1):
        self.user = DummyUser(user_id)
        self.guild_id = guild_id
        self.response = DummyResponse()

class PermissionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        os.makedirs('db', exist_ok=True)
        # settings db
        with sqlite3.connect('db/settings.sqlite') as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY, is_initial INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS adminserver (admin INTEGER, alliances_id INTEGER)")
            conn.commit()
        # alliance db
        with sqlite3.connect('db/alliance.sqlite') as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS alliance_list (alliance_id INTEGER PRIMARY KEY, name TEXT)")
            conn.commit()
        # users db required by cog
        with sqlite3.connect('db/users.sqlite') as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS users (fid INTEGER PRIMARY KEY, nickname TEXT, furnace_lv INTEGER, kid INTEGER, stove_lv_content TEXT, alliance TEXT)")
            conn.commit()
        os.makedirs('log', exist_ok=True)
        self.cog = AllianceMemberOperations(bot=None)

    def tearDown(self):
        self.cog.conn_alliance.close()
        self.cog.conn_users.close()
        for fname in ['db/settings.sqlite','db/alliance.sqlite','db/users.sqlite']:
            if os.path.exists(fname):
                os.remove(fname)
        if os.path.exists('db'):
            os.rmdir('db')
        if os.path.exists('log'):
            os.rmdir('log')

    async def test_add_user_blocked_for_unassigned_alliance(self):
        # create admin and alliances
        with sqlite3.connect('db/settings.sqlite') as conn:
            conn.execute("INSERT INTO admin (id, is_initial) VALUES (1, 0)")
            conn.execute("INSERT INTO adminserver (admin, alliances_id) VALUES (1, 1)")
            conn.commit()
        with sqlite3.connect('db/alliance.sqlite') as conn:
            conn.execute("INSERT INTO alliance_list (alliance_id, name) VALUES (1,'Alpha')")
            conn.execute("INSERT INTO alliance_list (alliance_id, name) VALUES (2,'Beta')")
            conn.commit()

        interaction = DummyInteraction(1, guild_id=1)
        await self.cog.add_user(interaction, '2', '12345')
        self.assertTrue(any('permission' in m.lower() for m in interaction.response.messages))

if __name__ == '__main__':
    unittest.main()
