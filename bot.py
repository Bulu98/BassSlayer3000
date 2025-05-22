# This is the main file for the Discord music bot.
# It will contain the core logic for connecting to Discord,
# handling commands, and managing music playback.

import discord
from discord.ext import commands
import dotenv
import os
import yt_dlp
import asyncio # Required for play_next_wrapper
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re # For URL detection

# Load environment variables
dotenv.load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Helper function for formatting duration
def format_duration(duration_seconds):
    if not duration_seconds or duration_seconds <= 0:
        return "N/A"
    minutes, seconds = divmod(int(duration_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

# Spotipy client setup
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
sp = None
if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
    try:
        auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        print("Spotipy client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Spotipy client: {e}. Spotify features will be unavailable.")
        sp = None # Ensure sp is None on error
else:
    print("Spotipy client ID or secret not found in environment variables. Spotify features will be unavailable.")
    sp = None

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
        song_item = song_queues[guild_id].pop(0)
        current_song_info[guild_id] = song_item
        
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_connected():
            try:
                ffmpeg_audio = discord.FFmpegPCMAudio(song_item['stream_url'], **FFMPEG_OPTS)
                audio_source_transformed = discord.PCMVolumeTransformer(ffmpeg_audio)
                voice_client.play(audio_source_transformed, after=lambda e: play_next_wrapper(ctx, e))
                guild_audio_sources[guild_id] = audio_source_transformed

                embed = discord.Embed(
                    title=song_item['title'], 
                    url=song_item['webpage_url'], 
                    color=discord.Color.blue()
                )
                embed.set_author(name=f"Now Playing (Requested by: {song_item['requester']})", icon_url=song_item['requester_avatar_url'])
                if song_item.get('thumbnail_url'):
                    embed.set_thumbnail(url=song_item['thumbnail_url'])
                
                embed.add_field(name="Channel/Uploader", value=song_item.get('uploader', 'N/A'), inline=True)
                embed.add_field(name="Duration", value=format_duration(song_item.get('duration')), inline=True)
                source_display = {
                    'youtube': 'YouTube',
                    'spotify_via_youtube': 'Spotify (via YouTube)',
                    'soundcloud': 'SoundCloud',
                    'search': 'Search (YouTube)' # ytsearch will be 'youtube' from extractor
                }.get(song_item.get('source_type'), 'Unknown Source')
                if song_item.get('source_type') == 'youtube' and 'ytsearch' in song_item.get('query','').lower():
                    source_display = 'Search (YouTube)'

                embed.add_field(name="Source", value=source_display, inline=True)
                
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"Error playing next song '{song_item['title']}': {e}")
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
    'cookiefile': os.getenv('YOUTUBE_COOKIE_FILE', None), 
    'extract_flat': False,
    'noplaylist': True, # Ensure we only process one item for direct yt-dlp calls unless it's a playlist *search*
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

async def fetch_youtube_info(query_or_url: str):
    """
    Fetches video information from YouTube or other yt-dlp supported sites.
    Returns a dictionary with 'title', 'stream_url', 'webpage_url', 'duration', 
    'thumbnail_url', 'uploader', 'source_type' or None.
    """
    ydl_opts_local = YDL_OPTS.copy()
    # For direct URL, don't want 'ytsearch:' and want to handle playlists if URL is a playlist
    # However, for this function's current primary use (single track resolution), noplaylist=True is good.
    # If query_or_url is a playlist URL and we want all items, this needs adjustment or a different function.
    
    is_url = query_or_url.startswith(('http:', 'https:'))
    search_query = query_or_url if is_url else f"ytsearch:{query_or_url}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts_local) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            if not info:
                return None

            # If it's a search and it returned a playlist, take the first video.
            # If it's a direct URL to a playlist, also take the first video (due to noplaylist=True).
            if 'entries' in info and info['entries']:
                video_info = info['entries'][0]
            elif 'url' in info: # Direct video URL or single search result
                video_info = info
            else:
                return None # No usable video information found

            stream_url = video_info.get('url') # Direct stream URL for some extractors
            title = video_info.get('title', 'Unknown title')
            webpage_url = video_info.get('webpage_url', query_or_url if is_url else 'Unknown source') # Original URL if provided
            duration = video_info.get('duration', 0)
            thumbnail_url = video_info.get('thumbnail', None)
            uploader = video_info.get('uploader', video_info.get('channel', 'Unknown Uploader'))
            # Determine source type based on the extractor yt-dlp used
            extractor_key = video_info.get('extractor_key', '').lower()
            source_type = extractor_key if extractor_key else 'unknown_url' if is_url else 'search'


            if not stream_url: # Fallback for some cases where 'url' might not be directly available
                formats = video_info.get('formats', [])
                for f_format in formats:
                    # Prefer audio-only if available
                    if f_format.get('acodec') != 'none' and f_format.get('vcodec') == 'none' and f_format.get('url'):
                        stream_url = f_format.get('url')
                        break
                if not stream_url and formats: # Fallback to first format with a URL
                     for f_format in formats:
                        if f_format.get('url'):
                            stream_url = f_format.get('url')
                            break
            
            if not stream_url:
                return None

            return {
                'title': title, 
                'stream_url': stream_url, # Renamed from source_url for clarity
                'webpage_url': webpage_url, 
                'duration': duration,
                'thumbnail_url': thumbnail_url,
                'uploader': uploader,
                'source_type': source_type 
            }

    except yt_dlp.utils.DownloadError as e:
        # Log discreetly or send a message if needed, but function should return None
        print(f"fetch_youtube_info DownloadError: {e}")
        return None
    except Exception as e:
        print(f"fetch_youtube_info generic error: {e}")
        return None

@bot.command(name="play")
async def play(ctx, *, query: str):
    """Plays audio from YouTube or Spotify (URL or search query)."""
    if ctx.author == bot.user:
        return

    # 1. Voice Channel Logic (unchanged, assuming it's fine)
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command.")
        return
    user_voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if voice_client:
        if voice_client.channel != user_voice_channel:
            await voice_client.move_to(user_voice_channel)
            await ctx.send(f"Moved to your voice channel: {user_voice_channel.name}")
    else:
        try:
            voice_client = await user_voice_channel.connect()
            await ctx.send(f"Joined voice channel: {user_voice_channel.name}")
        except Exception as e:
            await ctx.send(f"Error joining voice channel: {e}")
            return

    guild_id = ctx.guild.id
    if guild_id not in song_queues:
        song_queues[guild_id] = []

    # Spotify URL detection
    spotify_track_regex = r"https?://open.spotify.com/track/([a-zA-Z0-9]+)"
    spotify_album_regex = r"https?://open.spotify.com/album/([a-zA-Z0-9]+)"
    spotify_playlist_regex = r"https?://open.spotify.com/playlist/([a-zA-Z0-9]+)"

    match_track = re.match(spotify_track_regex, query)
    match_album = re.match(spotify_album_regex, query)
    match_playlist = re.match(spotify_playlist_regex, query)

    song_items_to_add = []

    if match_track or match_album or match_playlist:
        if not sp:
            await ctx.send("Spotify API credentials not configured. Cannot play Spotify links.")
            return
        
        await ctx.send(f"Processing Spotify link: `{query}`...")
        try:
            if match_track:
                track_id = match_track.group(1)
                spotify_track = sp.track(track_id)
                if spotify_track:
                    track_name = spotify_track['name']
                    artist_name = spotify_track['artists'][0]['name']
                    yt_query = f"{track_name} {artist_name} official audio"
                    await ctx.send(f"Found '{track_name}' by '{artist_name}' on Spotify. Searching on YouTube...")
                    youtube_info = await fetch_youtube_info(yt_query)
                    if youtube_info:
                        song_items_to_add.append({
                            'query': f"Spotify: {track_name} - {artist_name}",
                            'source_type': 'spotify_via_youtube',
                            'title': youtube_info['title'],
                            'webpage_url': youtube_info['webpage_url'],
                            'thumbnail_url': youtube_info['thumbnail_url'],
                            'duration': youtube_info['duration'],
                            'uploader': youtube_info['uploader'],
                            'stream_url': youtube_info['stream_url'],
                            'requester': ctx.author.name,
                            'requester_avatar_url': str(ctx.author.avatar.url) if ctx.author.avatar else None,
                        })
                        # Message will be sent when actually playing or adding to queue
                    else:
                        await ctx.send(f"Could not find a YouTube version for Spotify track: {track_name} - {artist_name}")
            
            elif match_album:
                album_id = match_album.group(1)
                album_info = sp.album(album_id)
                album_name = album_info['name']
                await ctx.send(f"Processing Spotify album: '{album_name}'. Adding up to 10 tracks...")
                tracks = sp.album_tracks(album_id, limit=10)['items']
                for i, item in enumerate(tracks):
                    track_name = item['name']
                    artist_name = item['artists'][0]['name']
                    yt_query = f"{track_name} {artist_name} official audio"
                    await ctx.send(f"({i+1}/10) Searching YouTube for: {track_name} - {artist_name}")
                    youtube_info = await fetch_youtube_info(yt_query)
                    if youtube_info:
                        song_items_to_add.append({
                            'query': f"Spotify: {track_name} - {artist_name}",
                            'source_type': 'spotify_via_youtube',
                            'title': youtube_info['title'],
                            'webpage_url': youtube_info['webpage_url'],
                            'thumbnail_url': youtube_info['thumbnail_url'],
                            'duration': youtube_info['duration'],
                            'uploader': youtube_info['uploader'],
                            'stream_url': youtube_info['stream_url'],
                            'requester': ctx.author.name,
                            'requester_avatar_url': str(ctx.author.avatar.url) if ctx.author.avatar else None,
                        })
                    else:
                        await ctx.send(f"Could not find YouTube version for: {track_name} - {artist_name}")
            
            elif match_playlist:
                playlist_id = match_playlist.group(1)
                playlist_info = sp.playlist(playlist_id)
                playlist_name = playlist_info['name']
                await ctx.send(f"Processing Spotify playlist: '{playlist_name}'. Adding up to 10 tracks...")
                results = sp.playlist_items(playlist_id, limit=10)
                for i, item in enumerate(results['items']):
                    track = item['track']
                    if track: # Ensure track object exists
                        track_name = track['name']
                        artist_name = track['artists'][0]['name']
                        yt_query = f"{track_name} {artist_name} official audio"
                        await ctx.send(f"({i+1}/10) Searching YouTube for: {track_name} - {artist_name}")
                        youtube_info = await fetch_youtube_info(yt_query)
                        if youtube_info:
                            song_items_to_add.append({
                                'query': f"Spotify: {track_name} - {artist_name}",
                                'source_type': 'spotify_via_youtube',
                                'title': youtube_info['title'],
                                'webpage_url': youtube_info['webpage_url'],
                                'thumbnail_url': youtube_info['thumbnail_url'],
                                'duration': youtube_info['duration'],
                                'uploader': youtube_info['uploader'],
                                'stream_url': youtube_info['stream_url'],
                                'requester': ctx.author.name,
                                'requester_avatar_url': str(ctx.author.avatar.url) if ctx.author.avatar else None,
                            })
                        else:
                            await ctx.send(f"Could not find YouTube version for: {track_name} - {artist_name}")
        except Exception as e:
            await ctx.send(f"Error processing Spotify link: {e}")
            print(f"Spotify processing error: {e}")
            return # Stop further processing for this command if Spotify part fails

    else: # Not a Spotify link, process as direct YouTube URL or search
        await ctx.send(f"Searching YouTube for: `{query}`...")
        youtube_info = await fetch_youtube_info(query) # query here is the original user input
        if youtube_info:
            song_items_to_add.append({
                'query': query,
                'source_type': youtube_info['source_type'], # e.g. 'youtube', 'soundcloud', etc.
                'title': youtube_info['title'],
                'webpage_url': youtube_info['webpage_url'],
                'thumbnail_url': youtube_info['thumbnail_url'],
                'duration': youtube_info['duration'],
                'uploader': youtube_info['uploader'],
                'stream_url': youtube_info['stream_url'],
                'requester': ctx.author.name,
                'requester_avatar_url': str(ctx.author.avatar.url) if ctx.author.avatar else None,
            })
        else:
            await ctx.send(f"Could not find anything for your query: `{query}`. Note: SoundCloud playlist URLs are not supported for direct queuing of all tracks.")
            return

    if not song_items_to_add:
        # This case should ideally be handled by specific error messages above,
        # but as a fallback if no items were successfully processed.
        await ctx.send("No songs were added. Please check your query or Spotify link.")
        return

    # Add processed songs to queue and/or play
    songs_played_directly = 0
    for i, song_item in enumerate(song_items_to_add):
        if voice_client.is_playing() or voice_client.is_paused() or (guild_id in song_queues and song_queues[guild_id]):
            # If already playing or queue is populated (even if we just added to it and it's about to be played)
            song_queues[guild_id].append(song_item)
            
            embed = discord.Embed(
                title=f"Added to Queue: {song_item['title']}", # Adjusted title
                url=song_item['webpage_url'],
                description=f"Position in queue: {len(song_queues[guild_id])}", # Adjusted description
                color=discord.Color.orange() 
            )
            embed.set_author(name=f"Requested by: {song_item['requester']}", icon_url=song_item['requester_avatar_url'])
            if song_item.get('thumbnail_url'):
                embed.set_thumbnail(url=song_item['thumbnail_url'])
            embed.add_field(name="Channel/Uploader", value=song_item.get('uploader', 'N/A'), inline=True)
            embed.add_field(name="Duration", value=format_duration(song_item.get('duration')), inline=True)
            await ctx.send(embed=embed)
        else:
            # Play directly if this is the first song and nothing is playing/queued
            if songs_played_directly == 0:
                current_song_info[guild_id] = song_item
                try:
                    if voice_client.is_connected():
                        ffmpeg_audio = discord.FFmpegPCMAudio(song_item['stream_url'], **FFMPEG_OPTS)
                        audio_source_transformed = discord.PCMVolumeTransformer(ffmpeg_audio)
                        voice_client.play(audio_source_transformed, after=lambda e: play_next_wrapper(ctx, e))
                        guild_audio_sources[guild_id] = audio_source_transformed
                        songs_played_directly += 1

                        embed = discord.Embed(
                            title=song_item['title'], 
                            url=song_item['webpage_url'], 
                            color=discord.Color.blue() # Blue for "now playing" (direct)
                        )
                        embed.set_author(name=f"Now Playing (Requested by: {song_item['requester']})", icon_url=song_item['requester_avatar_url'])
                        if song_item.get('thumbnail_url'):
                            embed.set_thumbnail(url=song_item['thumbnail_url'])
                        embed.add_field(name="Channel/Uploader", value=song_item.get('uploader', 'N/A'), inline=True)
                        embed.add_field(name="Duration", value=format_duration(song_item.get('duration')), inline=True)
                        source_display = {
                            'youtube': 'YouTube',
                            'spotify_via_youtube': 'Spotify (via YouTube)',
                            'soundcloud': 'SoundCloud',
                            'search': 'Search (YouTube)'
                        }.get(song_item.get('source_type'), 'Unknown Source')
                        if song_item.get('source_type') == 'youtube' and 'ytsearch' in song_item.get('query','').lower():
                             source_display = 'Search (YouTube)'
                        embed.add_field(name="Source", value=source_display, inline=True)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Bot is not connected to a voice channel anymore.")
                        current_song_info.pop(guild_id, None)
                        if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
                        # If connection lost, add remaining to queue if any
                        if i < len(song_items_to_add): song_queues[guild_id].extend(song_items_to_add[i:])
                        break 
                except Exception as e:
                    await ctx.send(f"Error starting playback for {song_item['title']}: {e}")
                    current_song_info.pop(guild_id, None)
                    if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
                    # If error on first direct play, add remaining to queue
                    if i < len(song_items_to_add): song_queues[guild_id].extend(song_items_to_add[i:])
                    break
            else: # This song should be added to queue as one was already played directly
                 song_queues[guild_id].append(song_item)
                 embed = discord.Embed(
                    title=f"Added to Queue: {song_item['title']}", # Adjusted title
                    url=song_item['webpage_url'],
                    description=f"Position in queue: {len(song_queues[guild_id])}", # Adjusted description
                    color=discord.Color.orange()
                )
                 embed.set_author(name=f"Requested by: {song_item['requester']}", icon_url=song_item['requester_avatar_url'])
                 if song_item.get('thumbnail_url'):
                    embed.set_thumbnail(url=song_item['thumbnail_url'])
                 embed.add_field(name="Channel/Uploader", value=song_item.get('uploader', 'N/A'), inline=True)
                 embed.add_field(name="Duration", value=format_duration(song_item.get('duration')), inline=True)
                 await ctx.send(embed=embed)


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
    current_song = current_song_info.get(guild_id)
    guild_queue = song_queues.get(guild_id, [])
    
    embed_description_parts = []

    if current_song:
        embed = discord.Embed(
            title=current_song['title'],
            url=current_song.get('webpage_url'),
            color=discord.Color.green() # Green for "Now Playing"
        )
        embed.set_author(
            name=f"Now Playing (Requested by: {current_song['requester']})",
            icon_url=current_song.get('requester_avatar_url')
        )
        if current_song.get('thumbnail_url'):
            embed.set_thumbnail(url=current_song['thumbnail_url'])
        
        embed.add_field(name="Channel/Uploader", value=current_song.get('uploader', 'N/A'), inline=True)
        embed.add_field(name="Duration", value=format_duration(current_song.get('duration')), inline=True)
        
        source_display = {
            'youtube': 'YouTube',
            'spotify_via_youtube': 'Spotify (via YouTube)',
            'soundcloud': 'SoundCloud',
            'search': 'Search (YouTube)'
        }.get(current_song.get('source_type'), 'Unknown Source')
        if current_song.get('source_type') == 'youtube' and 'ytsearch' in current_song.get('query','').lower():
            source_display = 'Search (YouTube)'
        embed.add_field(name="Source", value=source_display, inline=True)

    else: # Nothing currently playing
        embed = discord.Embed(
            title="Current Queue",
            color=discord.Color.blue() 
        )
        # Set a default author if nothing is playing, or leave it unset
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)


    if guild_queue:
        embed_description_parts.append("\n**Up Next:**\n")
        max_queue_display = 10 # Limit number of songs shown in queue
        for i, song_item in enumerate(guild_queue[:max_queue_display]):
            duration_str = format_duration(song_item.get('duration'))
            requester_str = song_item.get('requester', 'Unknown')
            embed_description_parts.append(
                f"{i+1}. [{song_item['title']}]({song_item.get('webpage_url', '#')}) - Req: {requester_str} ({duration_str})\n"
            )
        if len(guild_queue) > max_queue_display:
            embed_description_parts.append(f"...and {len(guild_queue) - max_queue_display} more song(s).\n")
    
    description_text = "".join(embed_description_parts)
    if description_text: # Add if there's anything to describe (e.g. "Up Next" or if it was set before)
        if len(description_text) > 4000 : # Max length is 4096, keep some buffer
            embed.description = description_text[:4000] + "..."
        else:
            embed.description = description_text
    elif not current_song: # Queue is empty AND nothing playing
         embed.description = "The queue is empty and nothing is currently playing."
    elif current_song and not guild_queue: # Something is playing, but queue is empty
        embed.description = (embed.description or "") + "\nThe queue is empty."


    await ctx.send(embed=embed)

@bot.command(name="nowplaying", aliases=["np"])
async def nowplaying(ctx):
    """Displays the currently playing song."""
    if ctx.author == bot.user:
        return
    
    guild_id = ctx.guild.id
    voice_client = ctx.voice_client

    if voice_client and voice_client.is_connected() and \
       (voice_client.is_playing() or voice_client.is_paused()) and \
       guild_id in current_song_info:
        
        song_item = current_song_info[guild_id]
        embed = discord.Embed(
            title=song_item['title'], 
            url=song_item['webpage_url'], 
            color=discord.Color.green() # Green for "now playing"
        )
        embed.set_author(name=f"Now Playing (Requested by: {song_item['requester']})", icon_url=song_item['requester_avatar_url'])
        if song_item.get('thumbnail_url'):
            embed.set_thumbnail(url=song_item['thumbnail_url'])
        
        embed.add_field(name="Channel/Uploader", value=song_item.get('uploader', 'N/A'), inline=True)
        embed.add_field(name="Duration", value=format_duration(song_item.get('duration')), inline=True)
        
        source_display = {
            'youtube': 'YouTube',
            'spotify_via_youtube': 'Spotify (via YouTube)',
            'soundcloud': 'SoundCloud',
            'search': 'Search (YouTube)'
        }.get(song_item.get('source_type'), 'Unknown Source')
        if song_item.get('source_type') == 'youtube' and 'ytsearch' in song_item.get('query','').lower():
            source_display = 'Search (YouTube)'
        
        embed.add_field(name="Source", value=source_display, inline=True)
        
        # Add queue position if possible (might be complex to get accurately without queue access here)
        # For now, !queue command shows full queue.
        
        await ctx.send(embed=embed)
    else:
        if guild_id in current_song_info and not (voice_client and (voice_client.is_playing() or voice_client.is_paused())):
             current_song_info.pop(guild_id, None) # Clear stale info
        
        embed = discord.Embed(description="Nothing is currently playing.", color=discord.Color.orange())
        await ctx.send(embed=embed)

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
