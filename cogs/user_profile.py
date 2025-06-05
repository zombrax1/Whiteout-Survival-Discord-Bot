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
                profile_pic TEXT,
                skip_merge_prompt INTEGER DEFAULT 0
            )
            """
        )

        self.cursor.execute("PRAGMA table_info(profiles)")
        columns = [row[1] for row in self.cursor.fetchall()]
        if "skip_merge_prompt" not in columns:
            self.cursor.execute(
                "ALTER TABLE profiles ADD COLUMN skip_merge_prompt INTEGER DEFAULT 0"
            )

        self.conn.commit()

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

    def merge_user_data(self, fid: int) -> bool:
        try:
            with sqlite3.connect('db/users.sqlite') as users_db:
                cursor = users_db.cursor()
                cursor.execute("SELECT fid FROM users WHERE fid=?", (fid,))
                exists = cursor.fetchone()
                if exists is None:
                    cursor.execute("INSERT INTO users (fid) VALUES (?)", (fid,))
                    users_db.commit()
            return True
        except Exception:
            return False

    def get_skip_prompt(self, discord_id: int) -> bool:
        self.cursor.execute(
            "SELECT skip_merge_prompt FROM profiles WHERE discord_id=?",
            (discord_id,),
        )
        row = self.cursor.fetchone()
        return bool(row[0]) if row else False

    class MergePromptView(discord.ui.View):
        def __init__(self, cog: 'UserProfile', user_id: int, fid: int):
            super().__init__()
            self.cog = cog
            self.user_id = user_id
            self.fid = fid

        class BackupPromptView(discord.ui.View):
            def __init__(self, parent: 'UserProfile.MergePromptView', action: str):
                super().__init__()
                self.parent = parent
                self.action = action  # 'merge' or 'new'

            def perform_action(self) -> str:
                if self.action == "merge":
                    success = self.parent.cog.merge_user_data(self.parent.fid)
                    return "✅ Data merged." if success else "❌ Merge failed."
                return "Continuing without merging."

            @discord.ui.button(label="Yes, backup", style=discord.ButtonStyle.primary)
            async def backup_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                backup_cog = self.parent.cog.bot.get_cog("BackupOperations")
                backup_msg = ""
                if backup_cog:
                    result = await backup_cog.create_backup(str(self.parent.user_id), backup_cog.default_storage)
                    if result:
                        backup_msg = "✅ Backup created. "
                    else:
                        backup_msg = "❌ Backup failed. "
                else:
                    backup_msg = "❌ Backup system unavailable. "
                action_msg = self.perform_action()
                await interaction.followup.send(backup_msg + action_msg, ephemeral=True)
                self.stop()

            @discord.ui.button(label="No, continue", style=discord.ButtonStyle.secondary)
            async def backup_no(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                action_msg = self.perform_action()
                await interaction.followup.send(action_msg, ephemeral=True)
                self.stop()

        @discord.ui.button(label="Merge Data", style=discord.ButtonStyle.primary)
        async def merge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            view = self.BackupPromptView(self, "merge")
            await interaction.response.send_message(
                "Backup your data before merging?", view=view, ephemeral=True
            )
            self.stop()

        @discord.ui.button(label="Continue as New", style=discord.ButtonStyle.secondary)
        async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            view = self.BackupPromptView(self, "new")
            await interaction.response.send_message(
                "Backup your data before continuing?", view=view, ephemeral=True
            )
            self.stop()

        @discord.ui.button(label="Never show again", style=discord.ButtonStyle.danger)
        async def never_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.cog.cursor.execute(
                "UPDATE profiles SET skip_merge_prompt=1 WHERE discord_id=?",
                (self.user_id,),
            )
            self.cog.conn.commit()
            await interaction.response.send_message("Merge prompt disabled.", ephemeral=True)
            self.stop()

        @discord.ui.button(label="Keep reminding me", style=discord.ButtonStyle.secondary)
        async def keep_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Ok, will remind you next time.", ephemeral=True)
            self.stop()

    @app_commands.command(name="set_fid", description="Link your in-game FID to your Discord account")
    async def set_fid(self, interaction: discord.Interaction, fid: int):
        self.upsert_profile(interaction.user.id, fid=fid)

        fid_status = ""
        os.makedirs('db', exist_ok=True)
        db_path = 'db/users.sqlite'
        # Determine if the users database already exists before writing to it
        file_exists = os.path.exists(db_path)
        try:
            # Check the users database for the provided FID and create the
            # record if it doesn't exist yet
            with sqlite3.connect(db_path) as users_db:
                cursor = users_db.cursor()
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS users (fid INTEGER PRIMARY KEY)"
                )
                cursor.execute("SELECT fid FROM users WHERE fid=?", (fid,))
                exists = cursor.fetchone()
                if exists is None:
                    cursor.execute("INSERT INTO users (fid) VALUES (?)", (fid,))
                    users_db.commit()
                    fid_status = "FID added to users database."
                else:
                    fid_status = "FID already exists in users database."
        except sqlite3.Error as exc:
            fid_status = "Error accessing users database."
            print(f"Database error: {exc}")
        except Exception as exc:
            fid_status = "Unexpected error accessing users database."
            print(f"Unexpected error: {exc}")

        if file_exists and not self.get_skip_prompt(interaction.user.id):
            view = self.MergePromptView(self, interaction.user.id, fid)
            await interaction.response.send_message(
                f"✅ FID saved. {fid_status} Choose an option:",
                view=view,
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"✅ FID saved. {fid_status}", ephemeral=True)

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
