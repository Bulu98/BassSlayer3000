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

2.  **Add your Discord Bot Token:**
    Open the `.env` file with a text editor and add your Discord Bot Token:
    ```env
    DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    ```

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

## Running the Bot

Once you have completed the setup and configuration:

1.  Ensure your virtual environment is activated (if you created one).
2.  Run the bot script from the project's root directory:
    ```bash
    python bot.py
    ```
3.  You should see a message in your console like `Logged in as YourBotName (ID: YOUR_BOT_ID)`.

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
