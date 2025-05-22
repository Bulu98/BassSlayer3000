# This is the main file for the Discord music bot.
# It will contain the core logic for connecting to Discord,
# handling commands, and managing music playback.

import discord
from discord.ext import commands
import dotenv
import os
import yt_dlp
import asyncio # Required for play_next_wrapper

# Load environment variables
dotenv.load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Bot setup
song_queues = {} # Guild ID: [list of song_item dictionaries]
current_song_info = {} # Guild ID: song_item
guild_audio_sources = {} # Guild ID: discord.PCMVolumeTransformer
# song_item = {'title': str, 'source_url': str, 'requester': str}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")

async def play_next(ctx):
    """Plays the next song in the queue for the guild."""
    guild_id = ctx.guild.id
    if guild_id in song_queues and song_queues[guild_id]:
        song_item = song_queues[guild_id].pop(0) # Get next song
        current_song_info[guild_id] = song_item # Store as current song
        
        title = song_item['title']
        source_url = song_item['source_url']
        requester = song_item['requester']
        
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_connected():
            try:
                ffmpeg_audio = discord.FFmpegPCMAudio(source_url, **FFMPEG_OPTS)
                audio_source_transformed = discord.PCMVolumeTransformer(ffmpeg_audio) # Default volume 1.0
                voice_client.play(audio_source_transformed, after=lambda e: play_next_wrapper(ctx, e))
                guild_audio_sources[guild_id] = audio_source_transformed
                await ctx.send(f"Now playing: **{title}** (Requested by: {requester})")
            except Exception as e:
                await ctx.send(f"Error playing next song '{title}': {e}")
                current_song_info.pop(guild_id, None)
                if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
                await play_next(ctx) 
        else:
            if guild_id in song_queues: song_queues[guild_id].clear()
            current_song_info.pop(guild_id, None)
            if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
    elif ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.send("Queue finished.")
        current_song_info.pop(guild_id, None)
        if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
    else: 
        current_song_info.pop(guild_id, None)
        if guild_id in song_queues: song_queues[guild_id].clear()
        if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]

def play_next_wrapper(ctx, error):
    """
    A synchronous wrapper for play_next to be used in the 'after' lambda.
    This is needed because 'after' expects a synchronous function,
    but play_next is async. We schedule play_next to run in the bot's event loop.
    """
    if error:
        print(f'Player error in play_next_wrapper: {error}')
        # You might want to send a message to the channel here as well
        # e.g., asyncio.run_coroutine_threadsafe(ctx.send(f"Playback error: {error}"), bot.loop)
    
    # Schedule play_next to run.
    # If there was an error, play_next might decide to skip or retry.
    # If no error, it proceeds to the next song or announces queue end.
    return asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)


@bot.command(name="ping")
async def ping(ctx):
    """Responds with Pong!"""
    if ctx.author == bot.user:
        return
    await ctx.send("Pong!")

@bot.command(name="join")
async def join(ctx):
    """Makes the bot join the voice channel of the command issuer."""
    if ctx.author == bot.user:
        return
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client: # If bot is already in a voice channel in this guild
            if ctx.voice_client.channel == channel:
                await ctx.send("I am already in your voice channel.")
            else:
                await ctx.voice_client.move_to(channel)
                await ctx.send(f"Moved to your voice channel: {channel.name}")
        else: # Bot is not in a voice channel in this guild
            await channel.connect()
            await ctx.send(f"Joined voice channel: {channel.name}")
    else:
        await ctx.send("You need to be in a voice channel to use this command.")

@bot.command(name="leave")
async def leave(ctx):
    """Makes the bot leave its current voice channel."""
    if ctx.author == bot.user:
        return
    if ctx.voice_client: # If bot is in a voice channel
        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I am not in a voice channel.")

# yt-dlp options
YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'quiet': False, # Set to False if verbose is True, otherwise verbose messages might be suppressed
    'verbose': True, # For more detailed output from yt-dlp for debugging
    'source_address': '0.0.0.0', # Helps in some network configurations
    'cookiefile': os.getenv('YOUTUBE_COOKIE_FILE', None), # Allows specifying a cookie file
    'extract_flat': False, 
    # 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s', 
    # 'restrictfilenames': True, 
    # 'nooverwrites': True, 
    # 'nocheckcertificate': True, 
    # 'ignoreerrors': False, 
    # 'logtostderr': False, 
    # 'keepvideo': False, 
    # 'skip_download': True, 
    # 'postprocessors': [{ 
    #     'key': 'FFmpegExtractAudio',
    #     'preferredcodec': 'mp3',
    #     'preferredquality': '192',
    # }],
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


@bot.command(name="play")
async def play(ctx, *, query: str):
    """Plays audio from YouTube (URL or search query)."""
    if ctx.author == bot.user:
        return

    # 1. Voice Channel Logic
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    user_voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client

    if voice_client:
        if voice_client.channel != user_voice_channel:
            await voice_client.move_to(user_voice_channel)
            await ctx.send(f"Moved to your voice channel: {user_voice_channel.name}")
        # else: bot is already in the user's channel
    else: # Bot is not in a voice channel in this guild
        try:
            voice_client = await user_voice_channel.connect()
            await ctx.send(f"Joined voice channel: {user_voice_channel.name}")
        except Exception as e:
            await ctx.send(f"Error joining voice channel: {e}")
            return

    # 2. yt-dlp Integration & Audio Playback
    guild_id = ctx.guild.id
    if guild_id not in song_queues:
        song_queues[guild_id] = []

    await ctx.send(f"Searching for: `{query}`...")

    # Fetch song info
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}" if not query.startswith(('http:', 'https:')) else query, download=False)
            if 'entries' in info and info['entries']:
                video_info = info['entries'][0]
            elif 'url' in info: # Direct URL
                video_info = info
            else:
                await ctx.send("Could not find a suitable audio source.")
                return

            stream_url = video_info.get('url') # Direct stream URL for some extractors
            title = video_info.get('title', 'Unknown title')

            if not stream_url: # Fallback for ytsearch or playlists where 'url' is not top-level
                formats = video_info.get('formats', [])
                for f_format in formats:
                    if f_format.get('acodec') != 'none' and f_format.get('vcodec') == 'none' and f_format.get('url'):
                        stream_url = f_format.get('url')
                        break
                if not stream_url and formats: # If no audio-only, try first format with a URL
                     for f_format in formats:
                        if f_format.get('url'):
                            stream_url = f_format.get('url')
                            break
            
            if not stream_url:
                await ctx.send(f"Could not extract a streamable URL for '{title}'.")
                return

    except yt_dlp.utils.DownloadError as e:
        await ctx.send(f"Error fetching audio: {e}. Try a different query or URL.")
        return
    except Exception as e:
        await ctx.send(f"An unexpected error occurred with yt-dlp: {e}")
        return

    song_item = {'title': title, 'source_url': stream_url, 'requester': ctx.author.name}

    if voice_client.is_playing() or voice_client.is_paused() or song_queues[guild_id]:
        song_queues[guild_id].append(song_item)
        await ctx.send(f"Added to queue: **{title}** (Requested by: {ctx.author.name})")
    else:
        # Queue was empty and bot wasn't playing, so play directly
        current_song_info[guild_id] = song_item 
        try:
            if voice_client.is_connected():
                ffmpeg_audio = discord.FFmpegPCMAudio(song_item['source_url'], **FFMPEG_OPTS)
                audio_source_transformed = discord.PCMVolumeTransformer(ffmpeg_audio) # Default volume 1.0
                voice_client.play(audio_source_transformed, after=lambda e: play_next_wrapper(ctx, e))
                guild_audio_sources[guild_id] = audio_source_transformed
                await ctx.send(f"Now playing: **{title}** (Requested by: {ctx.author.name})")
            else:
                await ctx.send("Bot is not connected to a voice channel anymore.")
                current_song_info.pop(guild_id, None)
                if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
        except Exception as e:
            await ctx.send(f"Error starting playback: {e}")
            current_song_info.pop(guild_id, None)
            if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]


@bot.command(name="pause")
async def pause(ctx):
    """Pauses the currently playing audio."""
    if ctx.author == bot.user:
        return
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.pause()
            await ctx.send("Playback paused.")
        else:
            await ctx.send("I am not playing anything right now.")
    else:
        await ctx.send("I am not connected to a voice channel.")

@bot.command(name="resume")
async def resume(ctx):
    """Resumes the paused audio."""
    if ctx.author == bot.user:
        return
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_connected():
        if voice_client.is_paused():
            voice_client.resume()
            await ctx.send("Playback resumed.")
        else:
            await ctx.send("Playback is not paused.")
    else:
        await ctx.send("I am not connected to a voice channel.")

@bot.command(name="stop")
async def stop(ctx):
    """Stops audio playback and disconnects the bot from the voice channel."""
    if ctx.author == bot.user:
        return
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_connected():
        guild_id = ctx.guild.id # Ensure guild_id is defined
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop() # This will trigger the 'after' callback.
                                # play_next will then clear current_song_info if queue is empty.
        
        if guild_id in song_queues:
            song_queues[guild_id].clear()
            await ctx.send("Queue cleared.")
        current_song_info.pop(guild_id, None) 
        if guild_id in guild_audio_sources: # Clear audio source on stop
            del guild_audio_sources[guild_id]

        await voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("I am not connected to a voice channel.")
        # Ensure cleanup if stop is called when not connected but data might exist
        guild_id = ctx.guild.id # Get guild_id for cleanup
        if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
        if guild_id in current_song_info: del current_song_info[guild_id]
        if guild_id in song_queues: song_queues[guild_id].clear()

@bot.command(name="skip") # Added for completeness from previous task, ensure it works with current_song_info
async def skip(ctx):
    """Skips the current song."""
    if ctx.author == bot.user:
        return
    voice_client = ctx.voice_client
    guild_id = ctx.guild.id
    if voice_client and voice_client.is_connected():
        if voice_client.is_playing() or voice_client.is_paused():
            await ctx.send("Skipping current song...")
            # current_song_info will be updated by play_next via the 'after' callback
            voice_client.stop() 
        else:
            await ctx.send("Not playing anything to skip.")
            current_song_info.pop(guild_id, None) # Ensure cleared if nothing was playing
    else:
        await ctx.send("I am not connected to a voice channel.")
        current_song_info.pop(guild_id, None) # Ensure cleared if not connected

@bot.command(name="queue", aliases=["q"]) # Added for completeness
async def queue_command(ctx):
    """Displays the current song queue."""
    if ctx.author == bot.user:
        return
    guild_id = ctx.guild.id
    
    queue_list = song_queues.get(guild_id, [])
    
    response = ""
    # Optionally, show current song first if it exists
    if guild_id in current_song_info:
        song = current_song_info[guild_id]
        response += f"Now Playing: **{song['title']}** (Requested by: {song['requester']})\n\n"
    
    if not queue_list:
        if not response: # Nothing playing and queue empty
             await ctx.send("The queue is currently empty and nothing is playing.")
        else: # Something playing, but queue is empty
            await ctx.send(response + "The upcoming queue is empty.")
        return

    response += "Upcoming Queue:\n"
    for i, song_item in enumerate(queue_list):
        response += f"{i+1}. **{song_item['title']}** (Requested by: {song_item['requester']})\n"
    
    if len(response) > 1900: # Discord message limit, leave some room
        await ctx.send(response[:1900] + "\n... (queue too long to display fully)")
    else:
        await ctx.send(response)

@bot.command(name="nowplaying", aliases=["np"])
async def nowplaying(ctx):
    """Displays the currently playing song."""
    if ctx.author == bot.user:
        return
    
    guild_id = ctx.guild.id
    voice_client = ctx.voice_client # Get current voice client for the guild

    # Check if bot is connected, playing/paused, and song info exists
    if voice_client and voice_client.is_connected() and \
       (voice_client.is_playing() or voice_client.is_paused()) and \
       guild_id in current_song_info:
        song = current_song_info[guild_id]
        title = song['title']
        requester = song['requester']
        await ctx.send(f"Now Playing: **{title}** (Requested by: {requester})")
    else:
        # If not playing but info somehow exists, clear it.
        if guild_id in current_song_info and not (voice_client and (voice_client.is_playing() or voice_client.is_paused())):
             current_song_info.pop(guild_id, None)
        await ctx.send("Nothing is currently playing.")

@bot.command(name="volume")
async def volume(ctx, level: str = None):
    """Adjusts the playback volume or displays current volume.
    Usage: !volume (shows current) or !volume <0-200> (sets volume)
    """
    if ctx.author == bot.user:
        return

    guild_id = ctx.guild.id
    voice_client = ctx.voice_client

    if not (voice_client and voice_client.is_connected() and voice_client.source):
        await ctx.send("Not currently playing anything or volume is not adjustable.")
        return

    audio_source = guild_audio_sources.get(guild_id)

    if not isinstance(audio_source, discord.PCMVolumeTransformer):
        await ctx.send("Volume is not adjustable for the current audio source.")
        # This might also indicate an issue if guild_audio_sources[guild_id] was not set correctly
        if guild_id in guild_audio_sources: # Clean up if it's an invalid source
            del guild_audio_sources[guild_id]
        return

    if level is None:
        # Display current volume
        current_volume_percentage = int(audio_source.volume * 100)
        await ctx.send(f"Current volume is: {current_volume_percentage}%")
    else:
        # Set volume
        try:
            volume_value = int(level)
            if 0 <= volume_value <= 200:
                audio_source.volume = volume_value / 100.0
                await ctx.send(f"Volume set to {volume_value}%.")
            else:
                await ctx.send("Volume must be between 0 and 200.")
        except ValueError:
            await ctx.send("Invalid volume level. Please use a number between 0 and 200.")
        except Exception as e:
            await ctx.send(f"An error occurred while setting volume: {e}")
            print(f"Error in volume command: {e}")


# Run the bot
if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("Error: DISCORD_TOKEN not found in .env file.")
