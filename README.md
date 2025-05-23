# Discord Music Bot - BassSlayer3000

A self-hosted Discord music bot that plays audio from YouTube. Manage playback with a variety of commands, including queuing, skipping, and more.

## Features

*   **`!ping`**: Checks if the bot is responsive.
*   **`!join`**: Makes the bot join your current voice channel.
*   **`!leave`**: Makes the bot leave its current voice channel.
*   **`!play [YouTube URL or search query]`**: Plays a song from a YouTube URL or search query. If a song is already playing or the queue is not empty, it adds the new song to the queue. The bot will automatically join your voice channel if it's not already in one.
*   **`!pause`**: Pauses the currently playing audio.
*   **`!resume`**: Resumes the paused audio.
*   **`!stop`**: Stops audio playback, clears the current song queue, and disconnects the bot from the voice channel.
*   **`!skip`**: Skips the currently playing song and plays the next song in the queue (if any).
*   **`!queue` (`!q`)**: Displays the list of songs currently in the queue, including the song that is now playing.
*   **`!nowplaying` (`!np`)**: Shows detailed information about the song that is currently playing.
*   **`!volume [level]`**: Adjusts the playback volume (0-200%). If no level is provided, displays the current volume. Example: `!volume 75`
*   **`!shuffle`**: Randomizes the order of songs in the current queue.
*   **`!loop [mode]`**: Sets or shows the current loop mode. Available modes: `off`, `song`. (e.g., `!loop song`, `!loop off`, or just `!loop` to see current mode).

## Setup Instructions

This guide focuses on setup for **Debian/Ubuntu** Linux distributions.

### Prerequisites

#### Python and Pip
Python 3.8 or newer is required. Pip (Python package installer) and venv (for virtual environments) are also necessary.

*   **For Debian/Ubuntu:**
    Python 3 is usually pre-installed. You can install pip and venv with:
    ```bash
    sudo apt update && sudo apt install python3-pip python3-venv
    ```
    Verify installation: `python3 --version && pip3 --version`

#### FFmpeg
FFmpeg is required for audio processing. It must be installed and accessible in your system's PATH.

*   **For Debian/Ubuntu:**
    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```
    Verify FFmpeg Installation:
    ```bash
    ffmpeg -version
    ```

#### Opus Audio Codec
The Opus audio codec is required by `discord.py` for voice communication.

*   **For Debian/Ubuntu:**
    ```bash
    sudo apt update && sudo apt install libopus0 libopus-dev
    ```

### Installation

1.  **Clone the repository (or download the code):**
    ```bash
    git clone https://github.com/your_username/discord-music-bot.git # Replace with your repo URL if forked
    cd discord-music-bot
    ```

2.  **Navigate to the project directory:**
    (If you haven't already in the step above)
    ```bash
    cd path/to/your/discord-music-bot
    ```

3.  **Create a virtual environment (recommended):**
    This isolates the bot's dependencies from your global Python packages.
    ```bash
    python3 -m venv venv
    ```
    Activate the virtual environment:
    ```bash
    source venv/bin/activate
    ```
    (Note: The command `python -m venv venv` might also work depending on your system's Python installation and PATH configuration. `python3` is more explicit.)

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Create a `.env` file:**
    In the root of the project directory, create a file named `.env`. You can copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Set Environment Variables:**
    Open the `.env` file with a text editor and add your Discord Bot Token and optionally the path to your YouTube cookie file:
    ```env
    DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    # Optional: Path to your YouTube cookies file (Netscape format). Leave blank if not used.
    # YOUTUBE_COOKIE_FILE=
    ```
    *   `DISCORD_TOKEN`: **Required.** Your bot's unique token.
    *   `YOUTUBE_COOKIE_FILE`: **Optional.** The absolute path to a text file containing YouTube cookies in Netscape HTTP Cookie File format. This can help `yt-dlp` access age-restricted content or content that requires a login. See the "Advanced Configuration" section for more details.
    *   `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET`: **Optional.** Needed if you want to enable Spotify link playback (which searches for the songs on YouTube). See "Getting Spotify API Credentials" below.

3.  **How to get a Discord Bot Token:**
    *   Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    *   Click on "**New Application**" (give it a name, e.g., "MyMusicBot").
    *   Navigate to the "**Bot**" tab on the left sidebar.
    *   Click "**Add Bot**" and confirm.
    *   Under the bot's username, you'll see a section labeled "**Token**". Click "**Copy**".
        *   **Important:** Treat this token like a password. Do not share it with anyone or commit it to public repositories.
    *   **Enable Privileged Gateway Intents:** On the same "Bot" page, scroll down to "Privileged Gateway Intents".
        *   Enable **MESSAGE CONTENT INTENT**.
        *   The bot also relies on voice state changes, which are covered by default intents, but ensure no specific guild intent restrictions are blocking it. `GUILD_VOICE_STATES` is essential.

4.  **Getting Spotify API Credentials (Optional):**
    If you want the bot to be able to parse Spotify track, album, and playlist URLs (it will then search for these songs on YouTube), you'll need Spotify API credentials.
    *   **Go to the Spotify Developer Dashboard:** [https://developer.spotify.com/dashboard/](https://developer.spotify.com/dashboard/)
    *   **Log in** with your Spotify account or create one.
    *   Click on "**Create an App**" (or "Create App").
        *   Give your application a **Name** (e.g., "MyDiscordBot") and a brief **Description**.
        *   Agree to the terms.
    *   Once created, you'll see your app's dashboard. Note down the **Client ID** and **Client Secret** (you might need to click "Show Client Secret").
    *   **Set a Redirect URI:** Even if not strictly used by the client credentials flow, it's good practice to set one.
        *   Go to your App's settings (usually "Edit Settings" or similar).
        *   In the "Redirect URIs" field, add `http://localhost:8888/callback`.
        *   Click "Save".
    *   **Add to `.env` file:**
        Open your `.env` file and add/update the following lines with the credentials you obtained:
        ```env
        SPOTIPY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID_HERE
        SPOTIPY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET_HERE
        ```
    If these credentials are not provided or are incorrect, Spotify link processing will be disabled.

## Running the Bot

Once you have completed the setup and configuration:

1.  Ensure your virtual environment is activated (if you created one).
2.  Run the bot script from the project's root directory:
    ```bash
    python3 bot.py
    ```
    (Note: `python bot.py` might also work depending on your system's PATH and if `python` defaults to Python 3.)
3.  You should see a message in your console like `Logged in as YourBotName (ID: YOUR_BOT_ID)`. If `yt-dlp` verbose logging is enabled (default), you will also see more detailed output from `yt-dlp`.

## Adding Bot to Your Discord Server

To use your bot, you need to invite it to a Discord server where you have "Manage Server" permissions.

1.  **Go to the Discord Developer Portal:** Navigate to your application.
2.  **OAuth2 URL Generator:**
    *   Select the "**OAuth2**" tab from the left menu, then "**URL Generator**".
3.  **Scopes:**
    *   In the "SCOPES" section, check `bot`.
4.  **Bot Permissions:**
    *   In the "BOT PERMISSIONS" section that appears, select the following:
        *   **Connect** (to join voice channels)
        *   **Speak** (to play audio in voice channels)
        *   **Read Messages/View Channels** (to see commands and interact)
        *   **Send Messages** (to respond to commands)
        *   **Embed Links** (recommended for future enhancements like rich embeds for queue display, etc.)
5.  **Generate and Use the URL:**
    *   Scroll down and copy the **Generated URL**.
    *   Open this URL in your web browser.
    *   Select the Discord server you want to add the bot to from the dropdown menu and click "Authorize".
    *   Complete any verification steps (like CAPTCHA).

The bot should now appear in your server's member list and be ready to use commands!

## Troubleshooting Audio Issues

If the bot joins the voice channel but you don't hear any audio, or if the `!play` command fails, here are some steps to check:

1.  **FFmpeg Installation:**
    *   Ensure FFmpeg is correctly installed. Verify by running `ffmpeg -version` in your terminal. If the command is not found, revisit the FFmpeg installation instructions in the "Prerequisites" section.

2.  **Opus Library Installation:**
    *   The Opus audio codec is essential. Make sure you have installed `libopus0` and `libopus-dev` (or equivalent) as per the "Prerequisites" section.

3.  **Bot Permissions on Discord:**
    *   Ensure the bot has **`Connect`**, **`Speak`**, and **`Use Voice Activity`** permissions in the voice channel.

4.  **Test with a Known-Good Link:**
    *   Try `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`.

5.  **Check `yt-dlp` Verbose Output:**
    *   The bot runs `yt-dlp` with `verbose: True`. Check the console logs for `yt-dlp` errors.

6.  **Discord Client Issues:**
    *   Try disconnecting/rejoining the voice channel or restarting your Discord client.

7.  **Firewall/Network:**
    *   Ensure your firewall isn't blocking outgoing connections (especially UDP for voice).

8.  **Check Bot's Console for Errors:**
    *   Look for Python errors or specific messages from `discord.py`.

## Advanced Configuration

### Using a YouTube Cookie File

A YouTube cookie file can be used to allow `yt-dlp` (and thus the bot) to access content that might be age-restricted or require a login.

**Configuration:**
Set the `YOUTUBE_COOKIE_FILE` environment variable in your `.env` file to the *absolute path* of your YouTube cookie file. Example: `YOUTUBE_COOKIE_FILE=/home/user/my_bot/youtube_cookies.txt`.

**Obtaining a Cookie File:**
Use browser extensions like "Get cookies.txt" (Chrome/Edge) or "cookies.txt" (Firefox). Ensure the file is in Netscape HTTP Cookie File format.

**Security Note:** Handle cookie files securely. Do not share them or commit them to your repository.

### Other yt-dlp Enhancements

*   **Verbose Logging (`verbose: True`):** `yt-dlp` provides detailed console output for debugging.
*   **Source Address (`source_address: '0.0.0.0'`):** Helps with connectivity in some network environments.

## Running as a Daemon (systemd)

To run the bot continuously as a background service on a Linux system that uses `systemd`:

1.  **Create `/etc/systemd/system/discord_music_bot.service`:**
    ```ini
    [Unit]
    Description=Discord Music Bot (BassSlayer3000)
    After=network.target

    [Service]
    User=your_username
    Group=your_groupname
    WorkingDirectory=/home/your_username/BassSlayer3000
    ExecStart=/home/your_username/BassSlayer3000/venv/bin/python3 /home/your_username/BassSlayer3000/bot.py
    Restart=always
    RestartSec=5s

    [Install]
    WantedBy=multi-user.target
    ```
    **Note:** Replace `your_username`, `your_groupname`, and paths with your actual setup.

2.  **Reload, Enable, and Start:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable discord_music_bot.service
    sudo systemctl start discord_music_bot.service
    ```

3.  **Check Status/Logs:**
    ```bash
    sudo systemctl status discord_music_bot.service
    sudo journalctl -fu discord_music_bot.service
    ```
