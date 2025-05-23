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
import random # For shuffling queue

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

# Custom Check Function
async def user_in_same_voice_channel(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        embed = discord.Embed(description="You need to be in a voice channel to use this command.", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
        raise commands.CheckFailure("User not in a voice channel.")
    
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        embed = discord.Embed(description="I am not currently in a voice channel.", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
        raise commands.CheckFailure("Bot not in a voice channel.")
    
    if ctx.author.voice.channel != ctx.voice_client.channel:
        embed = discord.Embed(description="You must be in the same voice channel as me to use this command.", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
        raise commands.CheckFailure("User not in the same voice channel as bot.")
    
    return True # If all checks pass

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
active_control_messages = {} # Guild ID: discord.Message object for current playback controls
guild_loop_states = {} # Guild ID: 'off' or 'song' (or 'queue' in future)

# song_item structure (for reference):
# {
# 'query': str, 'source_type': str, 'title': str, 'webpage_url': str, 
# 'thumbnail_url': str, 'duration': int, 'uploader': str, 
# 'stream_url': str, 'requester': str, 'requester_avatar_url': str
# }

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
                
                # Manage active control messages
                if guild_id in active_control_messages and active_control_messages[guild_id]:
                    try:
                        old_message = active_control_messages[guild_id]
                        # Create a new view with all buttons disabled for the old message
                        disabled_view = PlaybackControlView()
                        for child in disabled_view.children:
                            child.disabled = True
                        await old_message.edit(view=disabled_view)
                    except discord.NotFound:
                        pass # Old message might have been deleted
                    except Exception as ex:
                        print(f"Error editing old control message: {ex}")
                
                view = PlaybackControlView()
                # We need a way to update button states correctly here.
                # For now, buttons will have default states. Pause/Resume handles itself on click.
                # Skip/Stop might be enabled even if queue is empty after this song.
                # This will be improved by view.update_button_states in a follow-up if needed.
                
                new_message = await ctx.send(embed=embed, view=view)
                active_control_messages[guild_id] = new_message
                # await view.update_button_states(ctx) # Requires passing ctx or interaction to view or this method

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
        # If queue finishes, disable controls on the last message
        if guild_id in active_control_messages and active_control_messages[guild_id]:
            try:
                last_message = active_control_messages.pop(guild_id)
                if last_message: # Check if it wasn't already None
                    # Create a new view with all buttons disabled for the old message
                    disabled_view = PlaybackControlView()
                    for child in disabled_view.children:
                        child.disabled = True
                    await last_message.edit(view=disabled_view)
            except discord.NotFound:
                pass # Old message might have been deleted
            except Exception as ex:
                print(f"Error editing old control message on queue end: {ex}")

    else: # Bot not connected, or some other case where playback stops
        current_song_info.pop(guild_id, None)
        if guild_id in song_queues: song_queues[guild_id].clear()
        if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
        # Also try to disable controls if bot is not connected anymore
        if guild_id in active_control_messages and active_control_messages[guild_id]:
            try:
                last_message = active_control_messages.pop(guild_id)
                if last_message:
                    disabled_view = PlaybackControlView()
                    for child in disabled_view.children:
                        child.disabled = True
                    await last_message.edit(view=disabled_view)
            except discord.NotFound:
                pass
            except Exception as ex:
                print(f"Error editing old control message on disconnect: {ex}")

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

    guild_id = ctx.guild.id # Assuming ctx.guild is available
    loop_mode = guild_loop_states.get(guild_id, 'off')

    if loop_mode == 'song' and error is None:
        current_song = current_song_info.get(guild_id) # Get the song that just finished
        if current_song:
            # Ensure queue exists for the guild
            if guild_id not in song_queues:
                song_queues[guild_id] = []
            # Add the just-finished song to the beginning of the queue
            # Use .copy() to ensure modifications to the item (if any later) don't affect the original
            song_queues[guild_id].insert(0, current_song.copy()) 
            # No need to send a message here, play_next will play it and announce
    
    # elif loop_mode == 'queue' and error is None: # Placeholder for future queue loop
    #     current_song = current_song_info.get(guild_id)
    #     if current_song:
    #         if guild_id not in song_queues:
    #             song_queues[guild_id] = []
    #         song_queues[guild_id].append(current_song.copy()) # Add to the end for queue loop

    asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)


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

# This is the new, combined play command that includes Spotify and general URL/search logic
async def fetch_youtube_info(query_or_url: str): # Ensure this helper is defined before the play command that uses it
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
                        
                        # Manage active control messages for direct play
                        if guild_id in active_control_messages and active_control_messages[guild_id]:
                            try:
                                old_message = active_control_messages[guild_id]
                                disabled_view = PlaybackControlView()
                                for child_button in disabled_view.children: # Renamed to avoid conflict
                                    child_button.disabled = True
                                await old_message.edit(view=disabled_view)
                            except discord.NotFound:
                                pass
                            except Exception as ex:
                                print(f"Error editing old control message (direct play): {ex}")

                        view = PlaybackControlView()
                        new_message = await ctx.send(embed=embed, view=view)
                        active_control_messages[guild_id] = new_message
                        # await view.update_button_states(ctx) # Needs adjustment

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
@commands.check(user_in_same_voice_channel)
async def pause(ctx):
    """Pauses the currently playing audio."""
    if ctx.author == bot.user: # Still useful to prevent self-action if bot could use commands
        return
    
    voice_client = ctx.voice_client # Check ensures voice_client exists and is connected
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send(embed=discord.Embed(description="Playback paused.", color=discord.Color.blue()))
    else:
        await ctx.send(embed=discord.Embed(description="I am not playing anything right now.", color=discord.Color.orange()))

@bot.command(name="resume")
@commands.check(user_in_same_voice_channel)
async def resume(ctx):
    """Resumes the paused audio."""
    if ctx.author == bot.user:
        return
        
    voice_client = ctx.voice_client # Check ensures voice_client exists and is connected
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send(embed=discord.Embed(description="Playback resumed.", color=discord.Color.blue()))
    else:
        await ctx.send(embed=discord.Embed(description="Playback is not paused.", color=discord.Color.orange()))

@bot.command(name="stop")
@commands.check(user_in_same_voice_channel) # Applying check, user must be in channel to stop.
async def stop(ctx):
    """Stops audio playback and disconnects the bot from the voice channel."""
    if ctx.author == bot.user:
        return
    
    voice_client = ctx.voice_client # Check ensures voice_client exists and is connected
    guild_id = ctx.guild.id
    
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
        guild_id = ctx.guild.id 
        if guild_id in guild_audio_sources: del guild_audio_sources[guild_id]
        if guild_id in current_song_info: del current_song_info[guild_id]
        if guild_id in song_queues: song_queues[guild_id].clear() # Also clear queue on stop
        
        if guild_id in active_control_messages and active_control_messages[guild_id]:
            try:
                old_message = active_control_messages.pop(guild_id)
                if old_message:
                    disabled_view = PlaybackControlView()
                    for child_button_view in disabled_view.children: # Renamed variable
                        child_button_view.disabled = True
                    await old_message.edit(view=disabled_view)
            except discord.NotFound:
                pass
            except Exception as ex:
                print(f"Error editing old control message on stop (not connected scenario): {ex}")


@bot.command(name="skip")
@commands.check(user_in_same_voice_channel)
async def skip(ctx):
    """Skips the current song."""
    if ctx.author == bot.user:
        return
        
    voice_client = ctx.voice_client # Check ensures voice_client exists and is connected
    # guild_id = ctx.guild.id # No longer needed here directly for current_song_info pop

    if voice_client.is_playing() or voice_client.is_paused():
        # Send simple text message as ephemeral, or a small embed
        await ctx.send(embed=discord.Embed(description="Skipping current song...", color=discord.Color.blue()), delete_after=5)
        voice_client.stop()  # Triggers play_next via 'after' callback, which handles current_song_info
    else:
        # This case should ideally be less frequent if button is disabled, but good for direct command use
        await ctx.send(embed=discord.Embed(description="Not playing anything to skip.", color=discord.Color.orange()))


@bot.command(name="queue", aliases=["q"])
async def queue_command(ctx):
    """Displays the current song queue."""
    # This command does not require the user to be in the same voice channel,
    # nor does it require the bot to be in a voice channel. It just shows information.
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

@bot.command(name="shuffle")
async def shuffle(ctx):
    """Shuffles the current song queue."""
    if ctx.author == bot.user:
        return

    guild_id = ctx.guild.id
    if guild_id in song_queues and song_queues[guild_id]:
        queue = song_queues[guild_id]
        random.shuffle(queue)
        
        embed = discord.Embed(
            title="Queue Shuffled",
            description="The song queue has been randomized.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Queue Empty",
            description="The queue is currently empty, nothing to shuffle.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

@bot.command(name="loop")
async def loop(ctx, mode: str = None):
    """Sets or shows the current loop mode. Modes: off, song."""
    if ctx.author == bot.user:
        return

    guild_id = ctx.guild.id
    current_loop_mode = guild_loop_states.get(guild_id, 'off') # Check ensures voice_client exists

    if mode is None:
        embed = discord.Embed(
            title="Loop Status",
            description=f"Current loop mode: **{current_loop_mode.capitalize()}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    elif mode.lower() == 'off':
        guild_loop_states[guild_id] = 'off'
        embed = discord.Embed(description="Looping turned **off**.", color=discord.Color.green())
        await ctx.send(embed=embed)
    elif mode.lower() == 'song':
        guild_loop_states[guild_id] = 'song'
        embed = discord.Embed(description="Looping current **song**.", color=discord.Color.green())
        await ctx.send(embed=embed)
    # Placeholder for 'queue' mode in a future task
    # elif mode.lower() == 'queue':
    #     guild_loop_states[guild_id] = 'queue'
    #     embed = discord.Embed(description="Looping current **queue**.", color=discord.Color.green())
    #     await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            description="Invalid loop mode. Available modes: `off`, `song`.", # Add `queue` when implemented
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name="volume")
async def volume(ctx, level: str = None):
    """Adjusts the playback volume or displays current volume.
    Usage: !volume (shows current) or !volume <0-200> (sets volume)
    """
    if ctx.author == bot.user:
        return

    guild_id = ctx.guild.id
    voice_client = ctx.voice_client # Check ensures voice_client exists and is connected
    audio_source = guild_audio_sources.get(guild_id) # Check ensures voice_client.source exists via the bot connected check

    # The main check `user_in_same_voice_channel` already confirms:
    # 1. User is in a voice channel.
    # 2. Bot is in a voice channel.
    # 3. User and Bot are in the same channel.
    # We still need to check if voice_client.source exists for volume adjustment.
    if not voice_client.source:
        await ctx.send(embed=discord.Embed(description="Not currently playing anything.", color=discord.Color.orange()))
        return

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

# Playback Control View
class PlaybackControlView(discord.ui.View):
    def __init__(self, *, timeout=None): # Defaulting to None for persistent view
        super().__init__(timeout=timeout)

    async def update_button_states(self, interaction: discord.Interaction):
        """Updates the pause/resume button based on current playback state."""
        voice_client = interaction.guild.voice_client
        pause_resume_button = next((child for child in self.children if child.custom_id == "pause_resume_button"), None)
        
        if pause_resume_button:
            if voice_client and voice_client.is_playing():
                pause_resume_button.label = "Pause"
                pause_resume_button.emoji = "⏸️"
            elif voice_client and voice_client.is_paused():
                pause_resume_button.label = "Resume"
                pause_resume_button.emoji = "▶️"
            else: # Not playing or paused (e.g., stopped, or finished)
                pause_resume_button.label = "Pause" # Default to Pause
                pause_resume_button.emoji = "⏸️"
                pause_resume_button.disabled = True # Disable if not playing/paused

        # Potentially disable skip/stop if not relevant
        skip_button = next((child for child in self.children if child.custom_id == "skip_button"), None)
        stop_button = next((child for child in self.children if child.custom_id == "stop_button"), None)

        if not (voice_client and (voice_client.is_playing() or voice_client.is_paused())):
            if skip_button: skip_button.disabled = True
            # Stop button might still be relevant to disconnect if connected but not playing
            if stop_button and not voice_client.is_connected(): stop_button.disabled = True
        else:
            if skip_button: skip_button.disabled = False
            if stop_button: stop_button.disabled = False


    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary, emoji="⏸️", custom_id="pause_resume_button", row=0)
    async def pause_resume_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            button.label = "Resume"
            button.emoji = "▶️"
            await interaction.response.edit_message(view=self)
        elif voice_client and voice_client.is_paused():
            voice_client.resume()
            button.label = "Pause"
            button.emoji = "⏸️"
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Not playing anything to pause/resume.", ephemeral=True)
            button.disabled = True # Disable if state is unexpected
            await interaction.edit_original_response(view=self)


    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="skip_button", row=0)
    async def skip_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        guild_id = interaction.guild.id

        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            await interaction.response.send_message("Skipping to the next song...", ephemeral=True)
            voice_client.stop() # Triggers play_next via 'after' callback
            # play_next will handle new message with its own view or disable if queue empty
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)
            button.disabled = True
            await interaction.edit_original_response(view=self)


    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="stop_button", row=0)
    async def stop_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        guild_id = interaction.guild.id

        if voice_client and voice_client.is_connected():
            if guild_id in song_queues:
                song_queues[guild_id].clear()
            current_song_info.pop(guild_id, None)
            if guild_id in guild_audio_sources:
                del guild_audio_sources[guild_id]
            
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            
            await voice_client.disconnect()
            await interaction.response.send_message("Playback stopped and bot disconnected.", ephemeral=True)

            # Disable all buttons on this view
            for child_button in self.children:
                child_button.disabled = True
            if interaction.message: # Ensure message exists before trying to edit
                 await interaction.message.edit(view=self)
            self.stop() # Stop the view itself (removes from listening)
            
            # Clear this message from active_control_messages if it's the one
            if active_control_messages.get(guild_id) == interaction.message:
                active_control_messages.pop(guild_id, None)
        else:
            await interaction.response.send_message("Not connected to a voice channel.", ephemeral=True)
            button.disabled = True
            if interaction.message:
                await interaction.message.edit(view=self)
            self.stop() # Also stop view if bot wasn't connected
