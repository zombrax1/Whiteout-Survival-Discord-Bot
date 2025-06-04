import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os

class UserProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs('db', exist_ok=True)
        self.conn = sqlite3.connect('db/profile.sqlite')
        self.cursor = self.conn.cursor()
        self._setup_db()
        self.level_mapping = {
            31: "30-1", 32: "30-2", 33: "30-3", 34: "30-4",
            35: "FC 1", 36: "FC 1 - 1", 37: "FC 1 - 2", 38: "FC 1 - 3", 39: "FC 1 - 4",
            40: "FC 2", 41: "FC 2 - 1", 42: "FC 2 - 2", 43: "FC 2 - 3", 44: "FC 2 - 4",
            45: "FC 3", 46: "FC 3 - 1", 47: "FC 3 - 2", 48: "FC 3 - 3", 49: "FC 3 - 4",
            50: "FC 4", 51: "FC 4 - 1", 52: "FC 4 - 2", 53: "FC 4 - 3", 54: "FC 4 - 4",
            55: "FC 5", 56: "FC 5 - 1", 57: "FC 5 - 2", 58: "FC 5 - 3", 59: "FC 5 - 4",
            60: "FC 6", 61: "FC 6 - 1", 62: "FC 6 - 2", 63: "FC 6 - 3", 64: "FC 6 - 4",
            65: "FC 7", 66: "FC 7 - 1", 67: "FC 7 - 2", 68: "FC 7 - 3", 69: "FC 7 - 4",
            70: "FC 8", 71: "FC 8 - 1", 72: "FC 8 - 2", 73: "FC 8 - 3", 74: "FC 8 - 4",
            75: "FC 9", 76: "FC 9 - 1", 77: "FC 9 - 2", 78: "FC 9 - 3", 79: "FC 9 - 4",
            80: "FC 10", 81: "FC 10 - 1", 82: "FC 10 - 2", 83: "FC 10 - 3", 84: "FC 10 - 4"
        }

    def cog_unload(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def _setup_db(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                discord_id INTEGER PRIMARY KEY,
                fid INTEGER,
                location_x INTEGER,
                location_y INTEGER,
                bear_trap TEXT,
                profile_pic TEXT
            )
            """
        )
        self.conn.commit()

    async def is_admin(self, user_id: int) -> bool:
        try:
            with sqlite3.connect('db/settings.sqlite') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM admin WHERE id = ?", (user_id,))
                return cursor.fetchone() is not None
        except Exception:
            return False

    def upsert_profile(self, discord_id: int, **kwargs):
        columns = ', '.join(f"{k}=?" for k in kwargs.keys())
        values = list(kwargs.values())
        values.append(discord_id)
        self.cursor.execute(
            f"UPDATE profiles SET {columns} WHERE discord_id=?",
            values
        )
        if self.cursor.rowcount == 0:
            fields = ', '.join(kwargs.keys()) + ', discord_id'
            placeholders = ', '.join(['?' for _ in kwargs]) + ', ?'
            self.cursor.execute(
                f"INSERT INTO profiles ({fields}) VALUES ({placeholders})",
                list(kwargs.values()) + [discord_id]
            )
        self.conn.commit()

    @app_commands.command(name="set_fid", description="Link your in-game FID to your Discord account")
    async def set_fid(self, interaction: discord.Interaction, fid: int):
        self.upsert_profile(interaction.user.id, fid=fid)
        await interaction.response.send_message("✅ FID saved.", ephemeral=True)

    @app_commands.command(name="set_location", description="Set your base coordinates")
    async def set_location(self, interaction: discord.Interaction, x: int, y: int):
        self.upsert_profile(interaction.user.id, location_x=x, location_y=y)
        await interaction.response.send_message("✅ Location updated.", ephemeral=True)

    @app_commands.command(name="set_beartrap", description="Set Bear Trap info")
    async def set_beartrap(self, interaction: discord.Interaction, info: str):
        self.upsert_profile(interaction.user.id, bear_trap=info)
        await interaction.response.send_message("✅ Bear Trap info saved.", ephemeral=True)

    @app_commands.command(name="set_pfp", description="Set profile picture URL")
    async def set_pfp(self, interaction: discord.Interaction, image_url: str):
        self.upsert_profile(interaction.user.id, profile_pic=image_url)
        await interaction.response.send_message("✅ Profile picture saved.", ephemeral=True)

    @app_commands.command(name="profile", description="View a member's profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member=None):
        member = member or interaction.user
        if member.id != interaction.user.id:
            if not await self.is_admin(interaction.user.id):
                await interaction.response.send_message(
                    "❌ You can only view your own profile.", ephemeral=True
                )
                return
        self.cursor.execute("SELECT fid, location_x, location_y, bear_trap, profile_pic FROM profiles WHERE discord_id=?", (member.id,))
        profile = self.cursor.fetchone()

        fid = profile[0] if profile else None
        location_x = profile[1] if profile else None
        location_y = profile[2] if profile else None
        bear_trap = profile[3] if profile else None
        profile_pic = profile[4] if profile else None

        furnace_text = "Unknown"
        if fid:
            try:
                with sqlite3.connect('db/users.sqlite') as users_db:
                    cursor = users_db.cursor()
                    cursor.execute("SELECT furnace_lv FROM users WHERE fid=?", (fid,))
                    result = cursor.fetchone()
                    if result:
                        level = result[0]
                        furnace_text = self.level_mapping.get(level, str(level))
            except Exception:
                pass

        embed = discord.Embed(title=f"Profile of {member.display_name}", color=discord.Color.blue())
        if fid:
            embed.add_field(name="FID", value=str(fid), inline=True)
        embed.add_field(name="Furnace Level", value=furnace_text, inline=True)
        if location_x is not None and location_y is not None:
            embed.add_field(name="Location", value=f"X: {location_x} Y: {location_y}", inline=False)
        if bear_trap:
            embed.add_field(name="Bear Trap", value=bear_trap, inline=False)
        if profile_pic:
            embed.set_thumbnail(url=profile_pic)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UserProfile(bot))
