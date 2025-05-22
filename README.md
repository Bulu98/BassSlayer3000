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

## Setup Instructions

### Prerequisites

### Python and Pip
Python 3.8 or newer is required. Pip (Python package installer) and venv (for virtual environments) are also necessary.

*   **For Debian/Ubuntu:**
    Python 3 is usually pre-installed. You can install pip and venv with:
    ```bash
    sudo apt update && sudo apt install python3-pip python3-venv
    ```
    Verify installation: `python3 --version && pip3 --version`

*   **For Fedora:**
    Python 3 is usually pre-installed. You can install pip and venv (if not included with python3) with:
    ```bash
    sudo dnf install python3-pip python3-venv
    ```
    (If `python3-venv` is not found, venv might be included with your `python3` package or available via a differently named package like `python3-virtualenv`. Check your distribution's repositories if needed.)
    Verify installation: `python3 --version && pip3 --version`

*   **For Arch Linux:**
    ```bash
    sudo pacman -S python python-pip python-virtualenv
    ```
    Verify installation: `python --version && pip --version`

*   **For macOS:**
    Python 3 might be pre-installed. If not, or to get the latest version:
    *   **Using Homebrew (recommended):**
        ```bash
        brew install python
        ```
        This typically installs Python 3, pip, and sets up venv.
    *   **Official Installer:** Download from the [official Python website](https://www.python.org/downloads/mac-osx/).
    Verify installation (might be `python3` and `pip3` or `python` and `pip` depending on Homebrew setup): `python3 --version && pip3 --version`

*   **For Windows:**
    *   **Official Installer (recommended):** Download the latest Python 3 installer from the [official Python website](https://www.python.org/downloads/windows/).
        *   **Important:** During installation, make sure to check the box that says "Add Python to PATH".
        *   Pip and venv are usually included with the Python installer.
    *   **Using Chocolatey:**
        ```powershell
        choco install python
        ```
        This will install the latest Python 3 and add it to PATH. Pip should be included.
    Verify installation: `python --version && pip --version`

### FFmpeg
FFmpeg is required for audio processing. It must be installed and accessible in your system's PATH.

*   **For Debian/Ubuntu:**
    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```
*   **For Fedora:**
    ```bash
    sudo dnf install ffmpeg
    ```
    (Note: You might need to enable RPM Fusion repository first if ffmpeg is not found in default repos).
*   **For Arch Linux:**
    ```bash
    sudo pacman -S ffmpeg
    ```
*   **For macOS (using Homebrew):**
    ```bash
    brew install ffmpeg
    ```
*   **For Windows:**
    *   **Using Chocolatey (recommended):**
        ```powershell
        choco install ffmpeg
        ```
    *   **Manual Installation:** Download from the [official FFmpeg website](https://ffmpeg.org/download.html) (e.g., the gyan.dev or BtbN builds are often recommended for Windows). After downloading, you need to add the `bin` directory (which contains `ffmpeg.exe`) to your system's PATH environment variable.
*   **Verify FFmpeg Installation:**
    You can test your FFmpeg installation by typing the following command in your terminal or command prompt:
    ```bash
    ffmpeg -version
    ```

### Opus Audio Codec
The Opus audio codec is required by `discord.py` for voice communication. While `discord.py` attempts to load it automatically, it's best to ensure it's installed on your system.

*   **For Debian/Ubuntu:**
    ```bash
    sudo apt update && sudo apt install libopus0 libopus-dev
    ```
*   **For Fedora:**
    ```bash
    sudo dnf install opus opus-devel
    ```
*   **For Arch Linux:**
    ```bash
    sudo pacman -S opus
    ```
*   **For macOS (using Homebrew):**
    ```bash
    brew install opus
    ```
*   **For Windows:**
    The `discord.py` library attempts to load Opus from system libraries. If it fails, you might need to ensure Opus is available.
    1.  **Download Opus DLLs:** You can often find prebuilt Opus DLLs from the [official Opus website downloads page](https://opus-codec.org/downloads/) or by searching for "Opus Windows builds". Ensure you download the version matching your Python installation's architecture (e.g., 64-bit DLL for 64-bit Python).
    2.  **Placement:** Place the `opus.dll` file (it might be named `libopus-0.dll` depending on the build) in a location where it can be found by your system. This could be:
        *   In the same directory as your Python executable (`python.exe`).
        *   In a directory that is part of your system's PATH environment variable.
        *   In your bot's root directory (alongside `bot.py`).
    *   **Note:** Sometimes, a full FFmpeg installation on Windows (as covered in the FFmpeg section) might include the necessary Opus shared libraries, making a separate Opus installation unnecessary. If you encounter Opus loading errors after installing FFmpeg, try the manual DLL placement.

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
    python -m venv venv
    ```
    Activate the virtual environment:
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```

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
    python bot.py
    ```
3.  You should see a message in your console like `Logged in as YourBotName (ID: YOUR_BOT_ID)`. If `yt-dlp` verbose logging is enabled (default), you will also see more detailed output from `yt-dlp`.

## Adding Bot to Your Discord Server

To use your bot, you need to invite it to a Discord server where you have "Manage Server" permissions.

1.  **Go to the Discord Developer Portal:** Navigate to your application.
2.  **OAuth2 URL Generator:**
    *   Select the "**OAuth2**" tab from the left menu, then "**URL Generator**".
3.  **Scopes:**
    *   In the "SCOPES" section, check `bot`.
    *   (Note: `applications.commands` would be needed if you add slash commands in the future).
4.  **Bot Permissions:**
    *   In the "BOT PERMISSIONS" section that appears, select the following:
        *   **Connect** (to join voice channels)
        *   **Speak** (to play audio in voice channels)
        *   **Read Messages/View Channels** (to see commands and interact)
        *   **Send Messages** (to respond to commands)
        *   **Embed Links** (recommended for future enhancements like rich embeds for queue display, etc.)
    *   *Be mindful of the permissions you grant. These are generally sufficient for a music bot.*
5.  **Generate and Use the URL:**
    *   Scroll down and copy the **Generated URL**.
    *   Open this URL in your web browser.
    *   Select the Discord server you want to add the bot to from the dropdown menu and click "Authorize".
    *   Complete any verification steps (like CAPTCHA).

The bot should now appear in your server's member list and be ready to use commands!

## Troubleshooting Audio Issues

If the bot joins the voice channel but you don't hear any audio, or if the `!play` command fails, here are some steps to check:

1.  **FFmpeg Installation:**
    *   Ensure FFmpeg is correctly installed and accessible in your system's PATH. Verify by running `ffmpeg -version` in your terminal. If the command is not found, revisit the FFmpeg installation instructions in the "Prerequisites" section.

2.  **Opus Library Installation:**
    *   The Opus audio codec is essential for `discord.py` to transmit audio. Make sure you have installed it as per the "Opus Audio Codec" part of the "Prerequisites" section.
    *   On Windows, if you're having trouble, ensure `opus.dll` (or `libopus-0.dll`) is findable by the system, either by placing it in your Python directory, your bot's directory, or adding its location to the PATH.

3.  **Bot Permissions on Discord:**
    *   In your Discord server settings for the bot (or the roles it has):
        *   Ensure the bot has the **`Connect`** permission in the voice channel.
        *   Ensure the bot has the **`Speak`** permission in the voice channel.
        *   Ensure the bot has the **`Use Voice Activity`** permission (though `Speak` usually implies this, it's good to check).
    *   Try re-inviting the bot with the correct permissions if unsure. The invite link generator is in the "Adding Bot to Server" section.

4.  **Test with a Known-Good Link:**
    *   Try `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ` (a standard, unrestricted, well-known video). This helps rule out issues with specific videos (age restrictions, regional blocks) if you haven't configured a cookie file.

5.  **Check `yt-dlp` Verbose Output:**
    *   The bot is currently configured to run `yt-dlp` with `verbose: True`. Check the bot's console output/logs when you use the `!play` command. Look for any errors or messages from `yt-dlp` that might indicate a problem fetching the audio stream.

6.  **`source_address` Configuration:**
    *   The bot configures `yt-dlp` to use `source_address: '0.0.0.0'`. This setting can help in some network environments (like Docker or VMs) but is generally safe.

7.  **Discord Client Issues:**
    *   Sometimes, your own Discord client might have issues. Try:
        *   Disconnecting from the voice channel and rejoining.
        *   Restarting your Discord client.
        *   If using the web version of Discord, try the desktop application (or vice-versa).

8.  **Firewall/Network:**
    *   Ensure your firewall (on the machine running the bot, or your network firewall) is not blocking outgoing connections from the bot, especially UDP packets which Discord voice uses.

9.  **Check Bot's Console for Errors:**
    *   Look at the bot's console output for any Python errors or specific messages from `discord.py` that might indicate the problem.

## Advanced Configuration

### Using a YouTube Cookie File

A YouTube cookie file can be used to allow `yt-dlp` (and thus the bot) to access content that might be age-restricted or require a login (like private playlists or member-only videos, though direct support for private playlists that aren't yours might vary).

**Configuration:**

1.  Set the `YOUTUBE_COOKIE_FILE` environment variable in your `.env` file to the *absolute path* of your YouTube cookie file.
    *   Example: `YOUTUBE_COOKIE_FILE=/home/user/my_bot/youtube_cookies.txt`
    *   If this variable is not set or the file is not found, the bot will operate without cookies (which is fine for most public content).
    *   Alternatively, you can modify the path directly in `bot.py` in the `YDL_OPTS` dictionary, but using an environment variable is recommended for easier management and security.

**Obtaining a Cookie File:**

1.  You can export cookies from your browser using browser extensions. Search for extensions like:
    *   "Get cookies.txt" (available for Chrome, Firefox, Edge, etc.)
    *   "cookies.txt" (another option for Firefox)
2.  Ensure the file is exported in the **Netscape HTTP Cookie File format**.
3.  Place the exported `youtube_cookies.txt` (or a similarly named file) in a location accessible by the bot (e.g., within the bot's project directory or a dedicated data directory).
4.  Update the `YOUTUBE_COOKIE_FILE` variable in your `.env` file with the correct absolute path to this file.

**Security Note:** Cookie files contain sensitive session information. Handle them securely and do not share them or commit them to your repository, especially if they grant access to your personal YouTube account. It's recommended to use a separate YouTube account for the bot if you are concerned about security, or ensure the cookie file used only grants access to the content the bot needs.

### Other yt-dlp Enhancements

The bot's `yt-dlp` configuration includes the following options for improved debugging and connectivity:

*   **Verbose Logging (`verbose: True`):** `yt-dlp` is configured to provide more detailed output in the bot's console logs. This can be very helpful for diagnosing issues related to fetching song information or streams.
*   **Source Address (`source_address: '0.0.0.0'`):** This option configures `yt-dlp` to attempt binding to all available network interfaces. It may help with connectivity in certain network environments, such as when running the bot in a Docker container or a virtual machine, where the default outbound IP address might not be correctly routed for external services like YouTube.

## Running as a Daemon (systemd)

To run the bot continuously as a background service on a Linux system that uses `systemd`, you can create a systemd service file.

1.  **Create a Service File:**
    Create a file named `discord_music_bot.service` (or a name of your choice, e.g., `bassslayer3000.service`) in the `/etc/systemd/system/` directory. You'll need `sudo` privileges to do this.
    ```bash
    sudo nano /etc/systemd/system/discord_music_bot.service
    ```

2.  **Edit the Service File:**
    Paste the following content into the file. **You MUST adjust** the `User`, `Group`, `WorkingDirectory`, and `ExecStart` paths to match your specific setup.

    ```ini
    [Unit]
    Description=Discord Music Bot (BassSlayer3000)
    After=network.target

    [Service]
    User=your_username          # Replace with the user that will run the bot
    Group=your_groupname        # Replace with the group for that user (often same as username)
    
    WorkingDirectory=/home/your_username/BassSlayer3000  # Replace with the absolute path to your bot's project directory
    
    ExecStart=/home/your_username/BassSlayer3000/venv/bin/python /home/your_username/BassSlayer3000/bot.py
    # Above: Replace with the absolute path to your virtual environment's Python interpreter
    # and the absolute path to bot.py
    # If not using a virtual environment (not recommended), it might be:
    # ExecStart=/usr/bin/python3 /home/your_username/BassSlayer3000/bot.py

    Restart=always
    RestartSec=5s

    [Install]
    WantedBy=multi-user.target
    ```

    **Explanation of fields:**
    *   `Description`: A brief description of your service.
    *   `After=network.target`: Ensures the service starts after the network is available.
    *   `User`/`Group`: The system user and group the bot will run as. It's good practice to run bots under a dedicated non-root user.
    *   `WorkingDirectory`: The absolute path to the directory where your `bot.py` and `.env` files are located.
    *   `ExecStart`: The command that starts your bot.
        *   Make sure the path to the Python interpreter inside your virtual environment (`venv/bin/python`) is correct.
        *   Make sure the path to `bot.py` is correct.
    *   `Restart=always`: Automatically restarts the bot if it crashes.
    *   `RestartSec=5s`: Waits 5 seconds before attempting a restart.
    *   `WantedBy=multi-user.target`: Standard target to enable the service at boot for multi-user systems.

3.  **Reload systemd, Enable and Start the Service:**
    *   Tell systemd to recognize the new service file:
        ```bash
        sudo systemctl daemon-reload
        ```
    *   Enable the service to start automatically on boot:
        ```bash
        sudo systemctl enable discord_music_bot.service 
        ```
        (Use the same filename you created, e.g., `bassslayer3000.service`)
    *   Start the service immediately:
        ```bash
        sudo systemctl start discord_music_bot.service
        ```

4.  **Check Service Status and Logs:**
    *   To check if the service is running:
        ```bash
        sudo systemctl status discord_music_bot.service
        ```
    *   To view the bot's live console output (logs):
        ```bash
        sudo journalctl -fu discord_music_bot.service
        ```
    *   To view all logs for the service:
        ```bash
        sudo journalctl -u discord_music_bot.service
        ```

5.  **Stopping or Restarting the Service:**
    *   To stop: `sudo systemctl stop discord_music_bot.service`
    *   To restart: `sudo systemctl restart discord_music_bot.service`
