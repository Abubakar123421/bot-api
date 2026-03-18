import discord
from discord.ext import commands, tasks
import aiohttp
from database import get_guild_settings, update_guild_settings

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)

# ============================================================
#  CONFIG — All values hardcoded for Wispbyte
# ============================================================
DISCORD_TOKEN      = "MTQ4Mzc3MDUxMTQ2ODAwNzQ2NQ.G2jVIf.Yeok0qFb_9yqodxbndDlK9c3rVxd1YcvQOQBFM"
OCR_API_KEY        = "K88876086888957"
YOUTUBE_API_KEY    = "AIzaSyCUnauC2VtPVnB06EdO4gnqv2UmWT3_X34"
YOUTUBE_CHANNEL_ID = "UCBCZXuX_NMeYLfCxJ_BBkjg"
# ============================================================

last_video_id = "fYsfI1CItYo"


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} — Online!')
    activity = discord.Streaming(
        name="YouTube | @agtop302",
        url="https://www.youtube.com/@agtop302"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    check_new_video.start()
    print("[DB] Connected to MongoDB ✅")


# ============================================================
#  WELCOME SYSTEM
# ============================================================
@bot.event
async def on_member_join(member: discord.Member):
    settings = await get_guild_settings(str(member.guild.id))

    if not settings.get("welcome_enabled"):
        return

    channel_id = settings.get("welcome_channel_id")
    if not channel_id:
        return

    channel = bot.get_channel(int(channel_id))
    if not channel:
        return

    message = settings.get("welcome_message", "Welcome {user} to {server}! 🎉")
    message = message.replace("{user}", member.mention)
    message = message.replace("{server}", member.guild.name)
    message = message.replace("{membercount}", str(member.guild.member_count))
    message = message.replace("{username}", member.display_name)

    try:
        color = int(settings.get("welcome_color", "#5865F2").replace("#", ""), 16)
    except:
        color = 0x5865F2

    embed = discord.Embed(
        title=f"👋 Welcome to {member.guild.name}!",
        description=message,
        color=color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{member.guild.member_count}")
    await channel.send(embed=embed)


# ============================================================
#  YOUTUBE POLLING — every 5 minutes
# ============================================================
@tasks.loop(minutes=5)
async def check_new_video():
    global last_video_id
    try:
        url = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?key={YOUTUBE_API_KEY}"
            f"&channelId={YOUTUBE_CHANNEL_ID}"
            "&part=snippet,id"
            "&order=date"
            "&maxResults=1"
            "&type=video"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        items = data.get("items", [])
        if not items:
            return

        latest   = items[0]
        video_id = latest["id"].get("videoId")
        if not video_id or video_id == last_video_id:
            return

        last_video_id = video_id
        title     = latest["snippet"]["title"]
        thumb     = latest["snippet"]["thumbnails"]["high"]["url"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"[YT] New video: {title}")

        from database import guilds
        guild_doc = await guilds.find_one({"videos_channel_id": {"$ne": None}})
        if not guild_doc:
            return

        channel = bot.get_channel(int(guild_doc["videos_channel_id"]))
        if not channel:
            return

        embed = discord.Embed(
            title=f"🎬  {title}",
            url=video_url,
            description="> A new video just went live — go check it out!",
            color=0xFF0000
        )
        embed.set_image(url=thumb)
        embed.set_author(name="agtop302 • New Upload", icon_url="https://www.youtube.com/favicon.ico")
        embed.set_footer(text="YouTube • agtop302")

        await channel.send(
            content="# 🔔 New Video\n@everyone",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True)
        )

    except Exception as e:
        print(f"[YT ERROR] {type(e).__name__}: {e}")


@check_new_video.before_loop
async def before_check():
    await bot.wait_until_ready()


# ============================================================
#  VERIFICATION
# ============================================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    settings = await get_guild_settings(str(message.guild.id))
    verify_channel_id = int(settings.get("verify_channel_id", 0))

    if message.channel.id == verify_channel_id and message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg']):
                await handle_verification(message, attachment, settings)

    await bot.process_commands(message)


async def handle_verification(message: discord.Message, attachment: discord.Attachment, settings: dict):
    role_name = settings.get("role_name", "subscribers")
    role      = discord.utils.get(message.guild.roles, name=role_name)

    if role and role in message.author.roles:
        embed = discord.Embed(
            title="Already Verified",
            description="You already have access! No need to verify again. 👍",
            color=discord.Color.blurple()
        )
        await message.reply(embed=embed)
        return

    try:
        image_bytes = await attachment.read()

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("apikey", OCR_API_KEY)
            form.add_field("language", "eng")
            form.add_field("file", image_bytes, filename="image.png", content_type="image/png")

            async with session.post("https://api.ocr.space/parse/image", data=form) as resp:
                result = await resp.json()

        if result.get("IsErroredOnProcessing") or not result.get("ParsedResults"):
            embed = discord.Embed(
                title="⚠️ Oops!",
                description="We couldn't read your screenshot. Try sending a clearer image.",
                color=discord.Color.yellow()
            )
            embed.set_footer(text="Tip: Make sure the screenshot is not blurry or cropped.")
            await message.reply(embed=embed)
            return

        extracted_text = result["ParsedResults"][0]["ParsedText"].lower()
        required_texts = settings.get("required_texts", [])
        missing        = [r for r in required_texts if r.lower() not in extracted_text]

        if not missing:
            if role:
                await message.author.add_roles(role)
                embed = discord.Embed(
                    title="✅ Verified!",
                    description=f"Welcome to the squad, {message.author.mention}! 🎉\nYou now have full access.",
                    color=discord.Color.brand_green()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                embed.set_footer(text="Thanks for subscribing to agtop302 ❤️")
                await message.reply(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ Something went wrong",
                    description="Please contact an admin to sort this out.",
                    color=discord.Color.orange()
                )
                await message.reply(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="We couldn't confirm your subscription.\nDouble-check your screenshot and try again.",
                color=discord.Color.brand_red()
            )
            embed.set_footer(text="Still having issues? Contact an admin.")
            await message.reply(embed=embed)

    except Exception as e:
        print(f"[OCR ERROR] {type(e).__name__}: {e}")
        embed = discord.Embed(
            title="⚠️ Something went wrong",
            description="An unexpected error occurred. Please try again later.",
            color=discord.Color.orange()
        )
        await message.reply(embed=embed)


# ============================================================
#  COMMANDS
# ============================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Command Center",
        description="Here's everything you can do:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🖼️  `.avatar [@user]`", value="Shows a user's profile picture.",  inline=False)
    embed.add_field(name="🏓  `.ping`",            value="Checks the bot's response time.",  inline=False)
    embed.add_field(name="🏠  `.serverinfo`",      value="Shows info about this server.",    inline=False)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed  = discord.Embed(title=f"🖼️  {member.display_name}'s Avatar", color=discord.Color.blurple())
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    color   = discord.Color.brand_green() if latency < 100 else discord.Color.yellow() if latency < 200 else discord.Color.brand_red()
    embed   = discord.Embed(title="🏓 Pong!", description=f"Latency: **{latency}ms**", color=color)
    await ctx.send(embed=embed)


@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"🏠  {guild.name}", color=discord.Color.blurple())
    embed.add_field(name="👥 Members",   value=f"`{guild.member_count}`",                     inline=True)
    embed.add_field(name="📅 Created",   value=f"`{guild.created_at.strftime('%B %d, %Y')}`", inline=True)
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`",                               inline=False)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command()
async def balala(ctx):
    embed = discord.Embed(
        title="✨ No way you actually typed this",
        description="bro really found the secret command 💀\nRespect honestly.",
        color=discord.Color.gold()
    )
    embed.set_image(url="https://media.giphy.com/media/l41lOlmIQyA2Ezaa4/giphy.gif")
    await ctx.send(embed=embed)


# ── Run ──────────────────────────────────────────────────────
bot.run(DISCORD_TOKEN)
