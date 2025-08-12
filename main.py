import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import datetime

# =============================
# CONFIG
# =============================
BOT_TOKEN = "MTQwNDc0MDY2NDgyMjA3MTMxNg.GYId7U.fqtiThun3lD2293sZL-joX9NSrYMLYcqLKevoc"
ANNOUNCEMENTS_CHANNEL_ID = 1404314641521311744
MC_ANNOUNCEMENTS_CHANNEL_ID = 1404391647017435186
STAFF_LOG_CHANNEL_ID = 1404316719471792218

# Role IDs
ROLE_OWNER = 1404306284462997615
ROLE_ADMIN = 1404306745232330793
ROLE_SPECIAL_BOT = 1404307797184610344
ROLE_EVENT_ANNOUNCER = 1404308179881558127

# Các mode tính cách để random style
PERSONALITY_STYLES = [
    {"color": discord.Color.blue(), "footer": "📢 Thông báo chính thức"},
    {"color": discord.Color.green(), "footer": "🌿 Dịu dàng nhưng quan trọng"},
    {"color": discord.Color.red(), "footer": "🔥 Khẩn cấp! Chú ý ngay!"},
    {"color": discord.Color.purple(), "footer": "💫 Tin tức mới lạ"},
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# =============================
# Form nhập thông báo
# =============================
class AnnouncementModal(discord.ui.Modal):
    def __init__(self, title_placeholder: str, channel_id: int, ping_roles: dict, log_channel_id: int):
        super().__init__(title="Tạo thông báo")
        self.channel_id = channel_id
        self.ping_roles = ping_roles
        self.log_channel_id = log_channel_id

        self.add_item(discord.ui.TextInput(label="Tiêu đề", placeholder=title_placeholder, required=True, max_length=100))
        self.add_item(discord.ui.TextInput(label="Nội dung", style=discord.TextStyle.paragraph, required=True, max_length=2000))

    async def on_submit(self, interaction: discord.Interaction):
        title = self.children[0].value
        content = self.children[1].value

        # Chọn style random
        style = PERSONALITY_STYLES[datetime.datetime.now().second % len(PERSONALITY_STYLES)]

        embed = discord.Embed(title=title, description=content, color=style["color"])
        embed.set_footer(text=style["footer"])

        # Chọn ping
        view = PingView(self.channel_id, embed, self.ping_roles, self.log_channel_id)
        await interaction.response.send_message("Chọn cách ping cho thông báo:", view=view, ephemeral=True)

# =============================
# View chọn ping
# =============================
class PingView(discord.ui.View):
    def __init__(self, channel_id, embed, ping_roles, log_channel_id):
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.embed = embed
        self.ping_roles = ping_roles
        self.log_channel_id = log_channel_id

    @discord.ui.button(label="@everyone", style=discord.ButtonStyle.primary)
    async def everyone(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_announcement(interaction, self.ping_roles["everyone"])

    @discord.ui.button(label="@here", style=discord.ButtonStyle.secondary)
    async def here(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_announcement(interaction, self.ping_roles["here"])

    @discord.ui.button(label="Không ping", style=discord.ButtonStyle.success)
    async def none(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_announcement(interaction, "")

    async def send_announcement(self, interaction, ping_text):
        channel = interaction.client.get_channel(self.channel_id)
        log_channel = interaction.client.get_channel(self.log_channel_id)

        await channel.send(content=ping_text if ping_text else None, embed=self.embed)
        await log_channel.send(f"📌 **{interaction.user}** đã gửi thông báo:", embed=self.embed)

        await interaction.response.edit_message(content="✅ Đã gửi thông báo!", view=None)

# =============================
# Command: main-announcement
# =============================
@bot.tree.command(name="main-announcement", description="Tạo thông báo chính cho staff")
async def main_announcement(interaction: discord.Interaction):
    allowed_roles = [ROLE_OWNER, ROLE_ADMIN, ROLE_SPECIAL_BOT]
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)

    ping_roles = {"everyone": "@everyone", "here": "@here"}
    modal = AnnouncementModal("Tiêu đề thông báo chính", ANNOUNCEMENTS_CHANNEL_ID, ping_roles, STAFF_LOG_CHANNEL_ID)
    await interaction.response.send_modal(modal)

# =============================
# Command: event-announcement
# =============================
@bot.tree.command(name="event-announcement", description="Tạo thông báo cho event (có thể hẹn giờ nhắc)")
async def event_announcement(interaction: discord.Interaction):
    allowed_roles = [ROLE_OWNER, ROLE_ADMIN, ROLE_SPECIAL_BOT, ROLE_EVENT_ANNOUNCER]
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)

    ping_roles = {"everyone": "@everyone", "here": "@here"}  # Không ping role staff
    modal = EventAnnouncementModal(MC_ANNOUNCEMENTS_CHANNEL_ID, ping_roles, STAFF_LOG_CHANNEL_ID)
    await interaction.response.send_modal(modal)

# =============================
# Modal cho event
# =============================
class EventAnnouncementModal(discord.ui.Modal):
    def __init__(self, channel_id: int, ping_roles: dict, log_channel_id: int):
        super().__init__(title="Tạo thông báo Event")
        self.channel_id = channel_id
        self.ping_roles = ping_roles
        self.log_channel_id = log_channel_id

        self.add_item(discord.ui.TextInput(label="Tiêu đề", placeholder="VD: Sự kiện đua thuyền", required=True))
        self.add_item(discord.ui.TextInput(label="Nội dung", style=discord.TextStyle.paragraph, required=True))
        self.add_item(discord.ui.TextInput(label="Thời gian (HH:MM, 24h)", placeholder="VD: 19:30", required=False))

    async def on_submit(self, interaction: discord.Interaction):
        title = self.children[0].value
        content = self.children[1].value
        time_str = self.children[2].value.strip() if self.children[2].value else None

        style = PERSONALITY_STYLES[datetime.datetime.now().second % len(PERSONALITY_STYLES)]
        embed = discord.Embed(title=title, description=content, color=style["color"])
        embed.set_footer(text=style["footer"])

        view = EventPingView(self.channel_id, embed, self.ping_roles, self.log_channel_id, time_str)
        await interaction.response.send_message("Chọn cách ping cho thông báo:", view=view, ephemeral=True)

# =============================
# View ping cho event
# =============================
class EventPingView(PingView):
    def __init__(self, channel_id, embed, ping_roles, log_channel_id, time_str):
        super().__init__(channel_id, embed, ping_roles, log_channel_id)
        self.time_str = time_str

    async def send_announcement(self, interaction, ping_text):
        await super().send_announcement(interaction, ping_text)

        if self.time_str:
            try:
                now = datetime.datetime.now()
                event_time = datetime.datetime.strptime(self.time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
                if event_time < now:
                    event_time += datetime.timedelta(days=1)

                reminders = [
                    (event_time - datetime.timedelta(hours=1), "⏰ Còn 1 giờ nữa là sự kiện bắt đầu!"),
                    (event_time - datetime.timedelta(minutes=30), "⏰ Còn 30 phút nữa là sự kiện bắt đầu!")
                ]

                for reminder_time, reminder_msg in reminders:
                    delay = (reminder_time - datetime.datetime.now()).total_seconds()
                    if delay > 0:
                        asyncio.create_task(self.schedule_reminder(delay, reminder_msg))
            except:
                pass

    async def schedule_reminder(self, delay, msg):
        await asyncio.sleep(delay)
        channel = bot.get_channel(self.channel_id)
        if channel:
            await channel.send(msg)

# =============================
# ON READY
# =============================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot đã đăng nhập thành {bot.user}")

# =============================
# RUN BOT
# =============================
bot.run(BOT_TOKEN)