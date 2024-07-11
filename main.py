# --------- Modules --------- #

import os
import re
import csv
import json
import pytz

import base64
import random
import spotipy
import asyncio
import discord
import aiohttp
import datetime
import requests

import youtube_dl
import keep_alive

from io import BytesIO

import google.generativeai as genai
from pycoingecko import CoinGeckoAPI
from geopy.geocoders import Nominatim

from discord.ext import commands, tasks
from timezonefinder import TimezoneFinder

from craiyon import Craiyon, craiyon_utils
from spotipy.oauth2 import SpotifyClientCredentials

# --------- BOT Setup --------- #

file = "chats.txt"

with open(file, "r") as f:
  chat = f.read()

generator = Craiyon()

GOOGLE_AI_KEY = os.environ['KEY']
message_history = {}

intents = discord.Intents.all()
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

CHANNEL_ID = 1176514014231150603
SELFCHANNEL = 1176514014231150603
PINGCHANNEL = 1176514014231150603

MESSAGE_INTERVAL = 10800
MEME_INTERVAL = 3600

MCHANNEL_ID = 1176514072997539850

afks = {}

allowed_user_ids = [727012870683885578]

SPOTIFY_CLIENT_ID = os.getenv("Spotify_CID")
SPOTIFY_CLIENT_SECRET = os.getenv("Spotify_CST")

spotify_credentials = SpotifyClientCredentials(
  client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)

# --------- BOT Initialisation --------- #


def load_afk_data():
  try:
    with open("afk_data.csv", "r") as file:
      reader = csv.reader(file)
      afks = {row[0]: row[1] for row in reader}
      return afks
  except FileNotFoundError:
    return {}


def save_afk_data(data):
  with open("afk_data.csv", "w", newline="") as file:
    writer = csv.writer(file)
    for user_id, reason in data.items():
      writer.writerow([user_id, reason])


afks = load_afk_data()


@bot.event
async def on_ready():
  bot.start_time = datetime.datetime.now()

  print(f'------------------------------')
  print(f'{bot.user.name} Is ONLINE')
  print(f'------------------------------')

  await bot.tree.sync()
  await bot.change_presence(activity=discord.Game(name="With Utilities"))

  send_random_meme.start()
  send_random_message.start()


@tasks.loop(seconds=MESSAGE_INTERVAL)
async def send_random_message():
  channel = bot.get_channel(CHANNEL_ID)

  with open('messages.txt', 'r') as file:
    messages = file.read().splitlines()

  random_message = random.choice(messages)

  embed = discord.Embed(title="Did You Know ?",
                        description=random_message,
                        color=discord.Color.blue())
  await channel.send(embed=embed)


@tasks.loop(seconds=MEME_INTERVAL)
async def send_random_meme():
  mchannel = bot.get_channel(MCHANNEL_ID)
  response = requests.get("https://meme-api.com/gimme")
  meme_json = response.json()
  meme_url = meme_json["url"]
  await mchannel.send(meme_url)


# --------- BOT Commands / Cogs --------- #


@bot.tree.command(name="ping", description="Get Bot's Letacy")
async def ping(interaction):
  latency = bot.latency * 1000
  server_name = interaction.guild.name if interaction.guild else "Direct Message"
  uptime = datetime.datetime.now() - bot.start_time
  uptime_seconds = uptime.total_seconds()
  uptime_str = str(datetime.timedelta(seconds=uptime_seconds)).split(".")[0]
  num_servers = len(bot.guilds)

  embed = discord.Embed(title="_*Pong !*_", color=0x2f3136)
  embed.add_field(name="---------------------", value="     ", inline=False)
  embed.add_field(name="Servers", value=num_servers, inline=False)
  embed.add_field(name="Latency", value=f"{latency:.2f}ms", inline=False)
  embed.add_field(name="Server Name", value=server_name, inline=False)
  embed.add_field(name="Uptime", value=uptime_str, inline=False)

  await interaction.response.send_message(embed=embed)


@bot.tree.command(name="say", description="Repeates After You")
async def say(interaction, *, message: str = None):
  if message is None:
    await interaction.response.send_message("Please Enter A Message")
  else:
    await interaction.response.send_message(message)


@bot.tree.command(name="roll", description="Rolls A Dice For You")
async def roll(interaction, num1: int = 0, num2: int = 100):

  embed = discord.Embed(title="Roll Dice", color=0x2f3136)
  embed.add_field(name="Range", value=f"{num1} - {num2}", inline=False)
  embed.add_field(name="Result",
                  value=f"{random.randint(num1, num2)}",
                  inline=False)

  await interaction.response.send_message(embed=embed)


@bot.tree.command(name="slap", description="Slaps Someone")
async def slap(interaction, user: discord.Member, item: str):
  response = interaction.user
  if user.id == 727012870683885578:
    user = response
  response = f"{response.mention} Slapped {user.mention} With {item} !"

  embed = discord.Embed(title="Slap !", description=response, color=0x2f3136)

  await interaction.response.send_message(embed=embed)


@bot.tree.command(name="infouser", description="Get Information About A User")
async def user(interaction, member: discord.Member = None):
  if member is None:
    member = interaction.user

  roles = [role.name for role in member.roles[1:]]
  roles_str = ", ".join(roles) if len(roles) > 0 else "None"

  embed = discord.Embed(title=f"{member.display_name}'s Info",
                        color=int("0x2f3136", 16))
  embed.add_field(name="User ID", value=member.id, inline=False)
  embed.add_field(name="Nickname",
                  value=member.nick if member.nick else "None",
                  inline=False)
  embed.add_field(name="Roles", value=roles_str, inline=False)
  embed.add_field(name="Join Date",
                  value=member.joined_at.strftime("%Y-%m-%d | %H:%M:%S UTC"),
                  inline=False)
  embed.add_field(name="Account Creation",
                  value=member.created_at.strftime("%Y-%m-%d | %H:%M:%S UTC"),
                  inline=False)
  embed.set_thumbnail(url=member.avatar.url)

  await interaction.response.send_message(embed=embed)


@bot.tree.command(name="weather", description="Get Weather Of A Location")
async def weather(interaction, *, location: str):
  api_key = '34379a10e456c41b137b3f30379215e5'
  url = f'https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric'
  response = requests.get(url)

  if response.status_code == 200:
    data = response.json()
    city = data['name']
    country = data['sys']['country']
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    description = data['weather'][0]['description'].capitalize()
    icon = data['weather'][0]['icon']
    precipitation = data.get('rain', {}).get('1h', 0)
    humidity = data['main']['humidity']

    embed = discord.Embed(title=f'Weather In {city}, {country}',
                          description=description,
                          color=0x2f3136)
    embed.add_field(name='Temperature', value=f'{temp}°C', inline=True)
    embed.add_field(name='Feels Like', value=f'{feels_like}°C', inline=True)
    embed.add_field(name='', value=f'-------------------------', inline=False)
    embed.add_field(name='Humidity', value=f'{humidity} %', inline=False)
    embed.add_field(name='Precipitation',
                    value=f'{precipitation} mm',
                    inline=True)
    embed.set_thumbnail(url=f'https://openweathermap.org/img/wn/{icon}.png')

    await interaction.response.send_message(embed=embed)
  else:
    await interaction.response.send_message(
      f'Error: Could Not Get Weather Information For {location}.')


def get_random_joke():
  response = requests.get("https://official-joke-api.appspot.com/random_joke")
  data = response.json()
  joke_setup = data['setup']
  joke_punchline = data['punchline']
  return joke_setup, joke_punchline


@bot.tree.command(name="joke", description="Tells You A Random Joke")
async def joke(interaction):
  joke_setup, joke_punchline = get_random_joke()

  embed = discord.Embed(title="Joke", color=0x2f3136)
  embed.add_field(name=" ", value=joke_setup, inline=False)
  embed.add_field(name=" ", value=joke_punchline, inline=False)

  embed.set_footer(text="React With 🔄 To Get Another Joke!")

  joke_message = await interaction.channel.send(embed=embed)
  await joke_message.add_reaction("🔄")


@bot.event
async def on_reaction_add(reaction, user):

  if str(reaction.emoji) == "🔄" and not user.bot:
    message = reaction.message
    if message.embeds and message.embeds[0].title == "Joke":
      joke_setup, joke_punchline = get_random_joke()

      embed = discord.Embed(title="Joke", color=0x2f3136)
      embed.add_field(name=" ", value=joke_setup, inline=False)
      embed.add_field(name=" ", value=joke_punchline, inline=False)

      embed.set_footer(text="React With 🔄 To Get Another Joke !")

      await message.edit(embed=embed)
      await message.remove_reaction("🔄", user)

    if message.embeds and message.embeds[0].title == "Thoughtful Quote":
      response = requests.get("https://api.quotable.io/random")
      data = response.json()
      content = data['content']
      response = data['response']

      embed = discord.Embed(title="Thoughtful Quote",
                            description=f"{content}",
                            color=0x2f3136)
      embed.add_field(name=" ", value=f"- {response}", inline=False)
      embed.set_footer(text="React With 🔄 To Get Another Quote!")

      await message.edit(embed=embed)
      await message.remove_reaction("🔄", user)


@bot.tree.command(name="gif", description="Get A Gif For Keyword")
async def gif(interaction, *, message: str):
  keyword = message
  if keyword:
    url = f'https://api.giphy.com/v1/gifs/search?q={keyword}&api_key=nNoanEdlMAxSHdkQqUm1gWyX0UHomLUY&limit=10'
    response = requests.get(url)
    data = response.json()['data']

    if data:
      gif = random.choice(data)
      gif_url = gif['images']['original']['url']
      gif_message = await interaction.channel.send(gif_url)
      await interaction.response.send_message("Gottcha !", ephemeral=True)
      await gif_message.add_reaction("🔄")

      def check(reaction, user):
        return str(reaction.emoji) == "🔄" and user == interaction.user

      while True:
        try:
          reaction, user = await bot.wait_for('reaction_add',
                                              timeout=30.0,
                                              check=check)
          if not user.bot:
            new_gif = random.choice(data)
            new_gif_url = new_gif['images']['original']['url']
            await gif_message.edit(content=new_gif_url)
            await gif_message.remove_reaction("🔄", user)

        except TimeoutError:
          await gif_message.clear_reactions()

    else:
      await interaction.response.send_message(
        "No GIFs Found For The Keyword. Please Try A Different Keyword.")
  else:
    await interaction.response.send_message(
      "Please Provide A Keyword To Search For GIF.")


@bot.tree.command(name="friend",
                  description="Special Message For Special People")
async def friend(interaction):
  user = interaction.user
  if user.id == 727012870683885578:
    await interaction.response.send_message(
      "<@881073499429552168>, <@727012870683885578> Admires You, Be His Best Friend As You Are !"
    )
  elif user.id == 881073499429552168:
    await interaction.response.send_message(
      "<@727012870683885578> Is A Masochist Jordan, Pls Use Him As Ur Sacrifice"
    )
  else:
    await interaction.response.send_message(
      "Don't Dare To Use This Command, Ramen's My Cake")


@bot.tree.command(name="help",
                  description="Shows Help Menu For De Utility Bot")
async def help_command(interaction):
  embed_page1 = discord.Embed(
    title="Utility Bot - Help",
    description="Welcome to the Utility Bot Help Menu!\n\n"
    "Here are some commands you can use:\n"
    "-------------------------------------------------------\n"
    "**1. `/ping`** - Get bot's latency and information\n"
    "**2. `/say`** - Repeats after you\n"
    "**3. `/roll`** - Rolls a dice\n"
    "**4. `/slap`** - Slaps someone\n"
    "**5. `/infouser`** - Get information about a user\n"
    "**6. `/weather`** - Get weather of a location\n"
    "**7. `/joke`** - Tells you a random joke\n"
    "**8. `/help`** -   Gets you this menu\n"
    "**8. `/gif`** - Get a GIF for a keyword\n"
    "**10. `/afk`** - Sets user as AFK\n"
    "**11. `/meme`** - Gets a meme For you\n"
    "**12. `/time`** - Gets the current time for a location\n"
    "**13. `!genimage`** - Generates an image based on keywords\n\n"
    "-------------------------------------------------------",
    color=0x2f3136)

  await interaction.response.send_message(embed=embed_page1)


@bot.tree.command(name="meme", description="Sends A Random Meme")
async def meme(interaction):
  response = requests.get("https://meme-api.com/gimme")
  meme_json = response.json()
  meme_url = meme_json["url"]
  await interaction.response.send_message(meme_url)

@bot.tree.command(name="aboutme", description="Learn About The Bot")
async def aboutme(interaction):

  embed = discord.Embed(
    title="Introduction",
    description=
    "Hi there, I am De Utility\n\nI am a multiutility bot. \nTo get started with me, use `/help`"
  )
  embed.add_field(name="Prefix: /", value="", inline=False)
  embed.add_field(name="My Developers:", value="_._soham_", inline=False)
  embed.add_field(name=" ", value="", inline=False)
  embed.add_field(
    name=" ",
    value=
    "Invite Link: [Click here](https://discord.com/api/oauth2/authorize?client_id=1101810424380391444&permissions=8&scope=bot)",
    inline=False)
  await interaction.response.send_message(embed=embed)

@bot.tree.command(name="time",
                  description="Gets Current Time Of A Certain Location")
async def time(interaction, location: str):
  geolocator = Nominatim(user_agent="time_converter")
  try:
    location_info = geolocator.geocode(location)
    if location_info is None:
      await interaction.response.send_message(
        f"Could not find the location: {location}")
      return
  except:
    await interaction.response.send_message(
      "Error occurred while fetching location information.")
    return

  location_lat = location_info.latitude
  location_lon = location_info.longitude

  tf = TimezoneFinder()
  location_timezone = pytz.timezone(
    tf.timezone_at(lat=location_lat, lng=location_lon))

  current_time = datetime.datetime.now(location_timezone)
  current_time_str = current_time.strftime('%H:%M')

  indian_timezone = pytz.timezone('Asia/Kolkata')
  indian_time = current_time.astimezone(indian_timezone)

  uk_timezone = pytz.timezone('Europe/London')
  uk_time = current_time.astimezone(uk_timezone)

  usa_timezone = pytz.timezone('America/New_York')
  usa_time = current_time.astimezone(usa_timezone)

  philippines_timezone = pytz.timezone('Asia/Manila')
  philippines_time = current_time.astimezone(philippines_timezone)

  indian_time_str = indian_time.strftime('%H:%M')
  uk_time_str = uk_time.strftime('%H:%M')
  usa_time_str = usa_time.strftime('%H:%M')
  philippines_time_str = philippines_time.strftime('%H:%M')

  message = f"**Current Time in {location_info.address}: {current_time_str} **\n\n"
  message += f"Converted Time : \n\n"
  message += f"> UK Time: {uk_time_str}\n"
  message += f"> USA Time: {usa_time_str}\n"
  message += f"> Indian Time: {indian_time_str}\n"
  message += f"> Philippines Time: {philippines_time_str}"

  await interaction.response.send_message(message)

@bot.command()
async def genimage(ctx, *, prompt: str):
  await ctx.send(f"Generating Prompt \"{prompt}\"...")

  generated_images = await generator.async_generate(prompt)
  b64_list = await craiyon_utils.async_encode_base64(generated_images.images)
  images1 = []
  for index, image in enumerate(b64_list):
    img_bytes = BytesIO(base64.b64decode(image))
    image = discord.File(img_bytes)
    image.filename = f"result{index}.webp"
    images1.append(image)

  await ctx.send(files=images1)


trigger_words = ['jk', 'jking', 'lol', 'lul', 'lamo']


@bot.tree.command(name="afk", description="Sets AFK As Your Status")
async def afk(interaction, *, reason: str = None):
  if reason:
    reason = reason.replace('@everyone',
                            '@\u200beveryone').replace('@here', '@\u200bhere')

  user_id = str(interaction.user.id)

  if user_id in afks:
    await remove_afk(interaction.user)
    await interaction.response.send_message(
      ':no_entry: You Are Already AFK. Your AFK Status Has Been Removed.')
    return

  msg = ':white_check_mark: {0} Is Now AFK.'.format(interaction.user)
  original_name = interaction.user.display_name
  afk_name = "[AFK] " + original_name

  try:
    await interaction.user.edit(nick=afk_name)
  except discord.Forbidden:
    await interaction.response.send_message("Missing Permissions")
    await interaction.channel.send(msg)

  afks[user_id] = original_name + "|" + (reason or "")

  await interaction.response.send_message(msg)

  save_afk_data(afks)


STICKER_URL = "https://media.discordapp.net/stickers/1130433877027065936.webp?size=128"

genai.configure(api_key=GOOGLE_AI_KEY)
text_generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 512,
}
image_generation_config = {
  "temperature": 0.4,
  "top_p": 1,
  "top_k": 32,
  "max_output_tokens": 512,
}
safety_settings = [{
  "category": "HARM_CATEGORY_HARASSMENT",
  "threshold": "BLOCK_NONE"
}, {
  "category": "HARM_CATEGORY_HATE_SPEECH",
  "threshold": "BLOCK_NONE"
}, {
  "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
  "threshold": "BLOCK_NONE"
}, {
  "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
  "threshold": "BLOCK_NONE"
}]
text_model = genai.GenerativeModel(model_name="gemini-pro",
                                   generation_config=text_generation_config,
                                   safety_settings=safety_settings)

image_model = genai.GenerativeModel(model_name="gemini-pro-vision",
                                    generation_config=image_generation_config,
                                    safety_settings=safety_settings)


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  if not (bot.user.mentioned_in(message)
          or isinstance(message.channel, discord.DMChannel)):
    return

  async with message.channel.typing():
    if message.attachments:
      print("New Image Message FROM:" + str(message.author.id) + ": " +
            message.content)

      for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext)
               for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
          await message.add_reaction('🎨')

          async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
              if resp.status != 200:
                await message.channel.send('Unable To Get The Image')
                return
              image_data = await resp.read()
              response_text = await generate_response_with_image_and_text(
                image_data, message.content)

              await split_and_send_messages(message, response_text, 1700)
              return

    elif message.content.startswith('chattie'):
      print("New Text Message FROM:" + str(message.author.id) + ": " +
            message.content)
      response_text = await generate_response_with_text(
        message.channel.id, message.content)
      await split_and_send_messages(message, response_text, 1700)
      return
    else:
      print("New Message FROM:" + str(message.author.id) + ": " +
            message.content)
      response_text = await generate_response_with_text(
        message.channel.id, message.content)
      await split_and_send_messages(message, response_text, 1700)

    content = message.content.lower()

    if any(trigger_word in content for trigger_word in trigger_words):
      reminder_message = f"**{message.author.name}** Is Just Kidding!"
      await message.channel.send(reminder_message, delete_after=5)

    await bot.process_commands(message)

    if isinstance(message.channel, discord.DMChannel):
      return

    mentions = message.raw_mentions
    for user_id, reason in afks.items():
      if user_id in mentions:
        user = message.guild.get_member(user_id)
        if user:
          await message.channel.send(
            ':keyboard: {0} Is Currently AFK{1}'.format(
              user.name,
              ' :\n:keyboard: Reason : {0}'.format(reason) if reason else '.'))
          try:
            await user.send(
              f":sparkles: You Were Mentioned In A Message In {message.channel.mention}"
            )
          except discord.Forbidden:
            pass
          return

    if message.channel.id == 1176514067809185823 and message.attachments and message.attachments[
        0].url.endswith(('.png', '.jpg', '.jpeg', '.gif')):

      custom_emojis = [
        discord.PartialEmoji(name='7752heartslipbite', id=1176917694130434058)
      ]

      for emoji in custom_emojis:
        await message.add_reaction(emoji)

      if message.author.id == bot.user.id:
        return

      else:
        print("New Message FROM:" + str(message.author.id) + ": " +
              message.content)
        response_text = await generate_response_with_text(
          message.channel.id, message.content)
        await split_and_send_messages(message, response_text, 1700)
        return

    await bot.process_commands(message)


#---------------------------------------------AI Generation History-------------------------------------------------


async def generate_response_with_text(channel_id, message_text):
  cleaned_text = clean_discord_message(message_text)
  if not (channel_id in message_history):
    message_history[channel_id] = text_model.start_chat(history=[])
  response = message_history[channel_id].send_message(cleaned_text)
  return response.text


async def generate_response_with_image_and_text(image_data, text):
  image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
  prompt_parts = [
    image_parts[0], f"\n{text if text else 'What is this a picture of?'}"
  ]
  response = image_model.generate_content(prompt_parts)
  if (response._error):
    return "❌" + str(response._error)
  return response.text


@bot.tree.command(name='forget', description='Forget Message History')
async def forget(interaction: discord.Interaction):

  await interaction.response.send_message('Cleared Chat History')
  await message_history.pop(interaction.channel_id)


#---------------------------------------------Sending Messages-------------------------------------------------
async def split_and_send_messages(message_system: discord.Message, text,
                                  max_length):

  messages = []
  for i in range(0, len(text), max_length):
    sub_message = text[i:i + max_length]
    messages.append(sub_message)

  for string in messages:
    message_system = await message_system.reply(string)


def clean_discord_message(input_string):

  bracket_pattern = re.compile(r'<[^>]+>')

  cleaned_content = bracket_pattern.sub('', input_string)
  return cleaned_content


#---------------------------------------------Run Bot-------------------------------------------------


@bot.event
async def on_member_join(member):
  channel = bot.get_channel(CHANNEL_ID)
  schannel = bot.get_channel(SELFCHANNEL)
  pchannel = bot.get_channel(PINGCHANNEL)

  if schannel:
    message = await pchannel.send(f'{member.mention}')
    await asyncio.sleep(5)
    await message.delete()

  server_id = "1176513479897788496"
  if member.guild.id == int(server_id):

    await channel.send(
      f'🌟 Hey {member.mention} - Welcome Aboard \n🚀 Dive Into The Fun, Chat Away, and Enjoy Your Stay.'
    )

    user_ids = ["881073499429552168", "788296776741421066"]
    for user_id in user_ids:
      user = await bot.fetch_user(int(user_id))
      await user.send(
        f"Hey, {user.name} | {member.name} Just Joined The Server. Go And Greet Our New Mate :)"
      )
      print(f"DM Sent To {user.name}")


@bot.event
async def on_typing(channel, user, when):
  user_id = str(user.id)

  if user_id in afks:
    await remove_afk(user)
    await user.send(
      ':ok_hand: Welcome Back, Your AFK Status Has Been Removed{0}.'.format(
        ' ({0})'.format(channel.mention)
        if not isinstance(channel, discord.DMChannel) else ''))


async def remove_afk(user):
  user_id = str(user.id)

  if user_id in afks:
    original_name, reason = afks[user_id].split(
      "|") if "|" in afks[user_id] else (afks[user_id], "")
    afk_name_prefix = "[AFK] "

    if user.display_name.startswith(afk_name_prefix):
      new_name = user.display_name[len(afk_name_prefix):]
      try:
        await user.edit(nick=new_name)
      except discord.Forbidden:
        pass

    del afks[user_id]
    save_afk_data(afks)


# Moderation Bot Commands #

warnings_file = 'warnings.csv'


@bot.command()
@commands.has_permissions(kick_members=True)
async def timeout(ctx, member: discord.Member, duration: int = 60):
  await asyncio.sleep(duration)
  await ctx.message.delete()
  await member.send('Your warning message has been deleted after the timeout.')


@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
  with open(warnings_file, 'a', newline='') as file:
    writer = csv.writer(file)
    writer.writerow([ctx.guild.id, member.id, reason])

  await member.send(f'You have been warned in {ctx.guild.name} for {reason}.')
  await ctx.send(f'{member.mention} has been warned for {reason}.')


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
  await member.kick(reason=reason)
  if reason:
    await ctx.send(f'{member.mention} has been kicked for {reason}.')
    await member.send(
      f'You have been kicked from {ctx.guild.name} for {reason}.')
  else:
    await ctx.send(f'{member.mention} has been kicked.')
    await member.send(f'You have been kicked from {ctx.guild.name}.')


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
  await member.ban(reason=reason)
  if reason:
    await ctx.send(f'{member.mention} has been banned for {reason}.')
    await member.send(
      f'You have been banned from {ctx.guild.name} for {reason}.')
  else:
    await ctx.send(f'{member.mention} has been banned.')
    await member.send(f'You have been banned from {ctx.guild.name}.')


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
  await ctx.channel.purge(limit=amount + 1)
  await ctx.send(f'{amount} messages have been deleted.')


@bot.command()
@commands.has_permissions(manage_messages=True)
async def slowmode(ctx, seconds: int):
  await ctx.channel.edit(slowmode_delay=seconds)
  await ctx.send(f'Slowmode has been set to {seconds} seconds.')


@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
  await member.add_roles(role)
  await ctx.send(f'{member.mention} has been given the {role.name} role.')


@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
  await member.remove_roles(role)
  await ctx.send(
    f'{member.mention} has been removed from the {role.name} role.')


@bot.command()
async def helpmod(ctx):
  embed = discord.Embed(title='Moderator Commands',
                        description='List of available moderator commands:')
  embed.add_field(name='!kick @member [reason]',
                  value='Kick a member from the server.',
                  inline=False)
  embed.add_field(name='!ban @member [reason]',
                  value='Ban a member from the server.',
                  inline=False)
  embed.add_field(
    name='!purge <amount>',
    value='Delete a specified number of messages in the channel.',
    inline=False)
  embed.add_field(name='!warn @member [reason]',
                  value='Warn a member.',
                  inline=False)
  embed.add_field(name='!timeout @member [duration]',
                  value='Add a timeout to a member\'s warning.',
                  inline=False)
  embed.add_field(name='!addrole @member @role',
                  value='Add a role to a member.',
                  inline=False)
  embed.add_field(name='!removerole @member @role',
                  value='Remove a role from a member.',
                  inline=False)
  embed.add_field(name='!slowmode <amount>',
                  value='Set the slowmode (cooldown) for the channel.',
                  inline=False)

  await ctx.send(embed=embed)


# Music Bot #


@bot.tree.command(name="music", description="Sends Link For Seached Music")
async def search(interaction, query: str):

  results = spotify.search(q=query, limit=1, type='track')
  tracks = results['tracks']['items']

  if tracks:
    response = f"Search Results For '{query}' :\n"
    for index, track in enumerate(tracks, start=1):
      track_name = track['name']
      track_artist = track['artists'][0]['name']
      track_url = track['external_urls']['spotify']
      response += f"{track_name} by {track_artist}\nListen On Spotify: {track_url}\n\n"

    await interaction.response.send_message(response)
  else:
    await interaction.response.send_message(
      f"No Results Found For '{query}' On Spotify.")


@bot.tree.command(name="playlist",
                  description="Sends Link For Seached Playlist")
async def playlist(interaction, *, query: str, limit: int = 1):
  try:
    results = spotify.search(q=query, type='playlist', limit=limit)
    playlists = results['playlists']['items']

    if len(playlists) == 0:
      await interaction.response.send_message('No Playlists Found.')
      return

    response = ""

    for playlist in playlists:
      name = playlist['name']
      url = playlist['external_urls']['spotify']
      owner = playlist['owner']['display_name']
      description = playlist['description']

      response += f"{name} by {owner}\nListen On Spotify: {url}\n\n"

    await interaction.response.send_message(response)
  except Exception as e:
    print(f'An Error Occurred: {str(e)}')
    await interaction.response.send_message(
      'An Error Occurred While Searching For Playlists.')


keep_alive.keep_alive()
token = os.environ['TOKEN']
bot.run(token)
