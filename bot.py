"""
بوت ديسكورد بيولّد بوستات تويتر جاهزة عن طريق /post، بأزرار تفاعلية بدل
كتابة أوامر معقدة. ما بينشر أي شي على تويتر - انتي يلي بتنسخي وتلصقي يدوياً.
"""
import os
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from content_generator import generate_posts, find_stock_image_url, find_stock_video_url
from trends import fetch_trending_topics, random_trending_topic

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("content-bot")

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def build_options_embed(options: list[dict], used_trend: str | None) -> discord.Embed:
    embed = discord.Embed(
        title="✨ خياراتك جاهزة",
        description=f"📰 مبنية على ترند: **{used_trend}**" if used_trend else "🎲 محتوى متنوع",
        color=discord.Color.from_rgb(230, 62, 140),  # وردي مميز
    )
    for i, opt in enumerate(options, start=1):
        embed.add_field(
            name=f"{'①②③'[i-1]} {opt['type']} — {len(opt['text'])} حرف",
            value=f"```{opt['text']}```",
            inline=False,
        )
    embed.set_footer(text="اضغطي على رقم البوست اللي بيعجبك 👇")
    return embed


class PostChoiceView(discord.ui.View):
    """أزرار اختيار الخيار (1/2/3) + تجديد + إضافة وسائط."""

    def __init__(self, options: list[dict], used_trend: str | None):
        super().__init__(timeout=600)
        self.options = options
        self.used_trend = used_trend
        self.chosen_text: str | None = None

    async def _pick(self, interaction: discord.Interaction, index: int):
        self.chosen_text = self.options[index]["text"]
        embed = discord.Embed(
            title=f"{'①②③'[index]} اخترتي هالخيار",
            description=f"```{self.chosen_text}```",
            color=discord.Color.from_rgb(88, 101, 242),
        )
        embed.set_footer(text="دزّي على 🖼️ أو 🎥 لإضافة وسائط، أو انسخي النص وانزليه على تويتر")
        await interaction.response.send_message(embed=embed, view=MediaView(self.chosen_text), ephemeral=False)

    @discord.ui.button(label="① استخدمي هاد", style=discord.ButtonStyle.primary, row=0)
    async def choose_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, 0)

    @discord.ui.button(label="② استخدمي هاد", style=discord.ButtonStyle.primary, row=0)
    async def choose_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, 1)

    @discord.ui.button(label="③ استخدمي هاد", style=discord.ButtonStyle.primary, row=0)
    async def choose_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, 2)

    @discord.ui.button(label="🔄 جدّدي الخيارات", style=discord.ButtonStyle.secondary, row=1)
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        auto = self.used_trend is not None
        new_options = generate_posts(n=3, trend_context=self.used_trend if not auto else None, auto_trend=auto)
        new_trend = new_options[0].get("trend") or self.used_trend
        embed = build_options_embed(new_options, new_trend)
        await interaction.followup.send(embed=embed, view=PostChoiceView(new_options, new_trend))

    @discord.ui.button(label="🎲 ترند جديد كلياً", style=discord.ButtonStyle.secondary, row=1)
    async def new_trend(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        new_options = generate_posts(n=3, auto_trend=True)
        new_trend = new_options[0].get("trend")
        embed = build_options_embed(new_options, new_trend)
        await interaction.followup.send(embed=embed, view=PostChoiceView(new_options, new_trend))


class MediaView(discord.ui.View):
    """أزرار إضافة صورة/فيديو حر الترخيص للبوست المختار."""

    def __init__(self, post_text: str):
        super().__init__(timeout=600)
        self.post_text = post_text

    @discord.ui.button(label="🖼️ ضيفي صورة", style=discord.ButtonStyle.success, row=0)
    async def add_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        url = find_stock_image_url(self.post_text)
        if url:
            embed = discord.Embed(color=discord.Color.green())
            embed.set_image(url=url)
            embed.set_footer(text="📷 صورة حرة الترخيص (Pexels) - مسموح تنشريها")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("⚠️ ما لقيت صورة مناسبة، جربي كمان مرة أو تأكدي من PEXELS_API_KEY")

    @discord.ui.button(label="🎥 ضيفي فيديو", style=discord.ButtonStyle.success, row=0)
    async def add_video(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        url = find_stock_video_url(self.post_text)
        if url:
            await interaction.followup.send(f"🎥 فيديو حر الترخيص (Pexels):\n{url}")
        else:
            await interaction.followup.send("⚠️ ما لقيت فيديو مناسب، جربي كمان مرة أو تأكدي من PEXELS_API_KEY")


@client.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
    else:
        await tree.sync()
    log.info("✅ البوت شغال كـ %s", client.user)


@tree.command(name="post", description="ولّد بوستات جاهزة لتويتر بأزرار تفاعلية")
@app_commands.describe(trend="اختياري: ترند محدد. اتركيه فاضي والبوت بيجيب ترند حقيقي لحاله")
async def post_command(interaction: discord.Interaction, trend: str | None = None):
    await interaction.response.defer(thinking=True)
    try:
        auto = trend is None
        options = generate_posts(n=3, trend_context=trend, auto_trend=auto)
    except Exception:
        log.exception("فشل التوليد")
        await interaction.followup.send("⚠️ صار خطأ بالتوليد، جربي كمان مرة.")
        return

    used_trend = options[0].get("trend")
    embed = build_options_embed(options, used_trend)
    await interaction.followup.send(embed=embed, view=PostChoiceView(options, used_trend))


@tree.command(name="trends", description="شوفي أهم الترندات/الأخبار الحالية")
async def trends_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        topics = fetch_trending_topics(limit=8)
    except Exception:
        log.exception("فشل جلب الترندات")
        await interaction.followup.send("⚠️ ما قدرت أجيب الترندات هلق، جربي كمان مرة.")
        return

    if not topics:
        await interaction.followup.send("ما لقيت ترندات هلق.")
        return

    text = "\n".join(f"🔸 {t}" for t in topics)
    embed = discord.Embed(title="📰 ترندات/أخبار حالية", description=text, color=discord.Color.orange())
    await interaction.followup.send(embed=embed)


@tree.command(name="reply", description="ولّد رد جاهز على تغريدة (الصقي نصها)")
@app_commands.describe(original="نص التغريدة يلي بدك ترد عليها")
async def reply_command(interaction: discord.Interaction, original: str):
    await interaction.response.defer(thinking=True)
    from content_generator import generate_reply
    try:
        reply_text = generate_reply(original)
    except Exception:
        log.exception("فشل توليد الرد")
        await interaction.followup.send("⚠️ صار خطأ بالتوليد، جربي كمان مرة.")
        return

    embed = discord.Embed(title="💬 رد جاهز", description=f"```{reply_text}```", color=discord.Color.blue())
    await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
