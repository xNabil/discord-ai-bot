# Discord Chat Bot by Nabil
# GitHub: https://github.com/xNabil
# Version: Enhanced with Multi-Account Support, Priority Replies, Smart AI, Banned Words Handling, Probabilistic Response Lengths, Disfluencies, and Casual Professional Style

import os
import aiohttp
import random
import time
import asyncio
import google.generativeai as genai
import json
import sqlite3
from dotenv import load_dotenv
from dateutil.parser import isoparse
from colorama import init, Fore, Style
import logging
from textblob import TextBlob
import re
from collections import deque
import queue
import threading

# Custom logging filter to suppress specific warning messages
class SuppressWarningsFilter(logging.Filter):
    def filter(self, record):
        return not (
            "absl::InitializeLog" in record.getMessage() or
            "alts_credentials.cc" in record.getMessage()
        )

# Apply filter to suppress warnings from Google Gemini API
logging.getLogger().addFilter(SuppressWarningsFilter())

# Initialize colorama for colored terminal output and set up logging
init()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define account-specific colors for terminal output
ACCOUNT_COLORS = [Fore.CYAN, Fore.MAGENTA, Fore.YELLOW]

# Thread-safe queue for terminal messages
MESSAGE_QUEUE = queue.Queue()
# Shared state for slow mode timers
SLOW_MODE_TIMERS = {}
SLOW_MODE_LOCK = threading.Lock()
# Global state for countdown line
COUNTDOWN_LINE = ""
COUNTDOWN_LOCK = threading.Lock()
# Lock for channels.json file access
CHANNEL_CACHE_LOCK = threading.Lock()

print(f"{Fore.CYAN}Starting Multi-Account Discord Chat Bot...{Style.RESET_ALL}")

# Load environment variables from .env file
try:
    load_dotenv()
    print(f"{Fore.GREEN}Loaded .env file successfully{Style.RESET_ALL}")
except Exception as e:
    print(f"{Fore.RED}Error loading .env: {e}{Style.RESET_ALL}")
    exit(1)

# Retrieve and parse environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_IDS = os.getenv("CHANNEL_ID")  # Changed to CHANNEL_IDS for clarity
SLOW_MODE = os.getenv("SLOW_MODE")

# Parse comma-separated tokens, API keys, and channel IDs (max 3 accounts, max 6 channels)
try:
    DISCORD_TOKENS = [t.strip().strip('"') for t in DISCORD_TOKEN.split(",")] if DISCORD_TOKEN else []
    GEMINI_API_KEYS = [k.strip().strip('"') for k in GEMINI_API_KEY.split(",")] if GEMINI_API_KEY else []
    CHANNEL_IDS = [c.strip().strip('"') for c in CHANNEL_IDS.split(",")] if CHANNEL_IDS else []
    if len(DISCORD_TOKENS) != len(GEMINI_API_KEYS) or len(DISCORD_TOKENS) > 3:
        raise ValueError("Number of DISCORD_TOKEN and GEMINI_API_KEY must match and be <= 3")
    if len(CHANNEL_IDS) > 6:
        raise ValueError("Maximum 6 channel IDs allowed")
except Exception as e:
    print(f"{Fore.RED}Error parsing tokens, keys, or channel IDs: {e}{Style.RESET_ALL}")
    exit(1)

# Validate environment variables
if not DISCORD_TOKENS or not GEMINI_API_KEYS or not CHANNEL_IDS:
    print(f"{Fore.RED}Missing required environment variables!{Style.RESET_ALL}")
    exit(1)
print(f"{Fore.GREEN}Environment variables validated for {len(DISCORD_TOKENS)} account(s) and {len(CHANNEL_IDS)} channel(s){Style.RESET_ALL}")

# Initialize SLOW_MODE_TIMERS for accounts
SLOW_MODE_TIMERS = {i: 0 for i in range(len(DISCORD_TOKENS))}

# Banned words list
BANNED_WORDS = ['hi', 'fire', 'hello', 'lit', 'blaze']  # Add more as needed

# Topic keywords for detection
TOPICS = {
    'gaming': ['game', 'play', 'console', 'pc', 'xbox', 'playstation', 'controller', 'gamer'],
    'music': ['song', 'album', 'artist', 'band', 'concert', 'beats', 'tune'],
    'movies': ['film', 'movie', 'cinema', 'actor', 'director', 'scene', 'plot'],
    'tech': ['code', 'tech', 'software', 'hardware', 'gadget', 'app', 'update'],
    'food': ['food', 'eat', 'cook', 'recipe', 'snack', 'meal', 'yummy'],
    'anime': ['anime', 'manga', 'episode', 'series', 'character', 'aot', 'naruto', 'one piece']
}

# Regex patterns for user profiling
FAVORITE_GAME_PATTERN = re.compile(r"my favorite game is (\w+)", re.IGNORECASE)
FAVORITE_FOOD_PATTERN = re.compile(r"my favorite food is (\w+)", re.IGNORECASE)
FAVORITE_ANIME_PATTERN = re.compile(r"my favorite anime is (\w+)", re.IGNORECASE)

# Account-specific state
class AccountState:
    def __init__(self, index, token, gemini_key):
        self.index = index  # 0-based index for account (0, 1, 2)
        self.token = token
        self.gemini_key = gemini_key
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        self.bot_user_id = None
        self.bot_username = None
        self.personal_info = {}
        self.user_profiles = {}
        self.responded_messages = deque(maxlen=100)
        self.response_counter = 0
        self.response_types = []
        self.pending_replies = deque(maxlen=3)
        self.db_conn = None
        self.model = None
        self.color = ACCOUNT_COLORS[index]

    def prefix(self, message):
        """Prefix messages with account identifier and color."""
        return f"{self.color}[ACC {self.index + 1} - {self.bot_username or 'Unknown'}] {message}{Style.RESET_ALL}"

# Initialize accounts
ACCOUNTS = [AccountState(i, token, key) for i, (token, key) in enumerate(zip(DISCORD_TOKENS, GEMINI_API_KEYS))]

# Function to get channel and server name with caching
async def get_channel_name(account, channel_id):
    """Retrieve channel and server name from cache or Discord API, caching results in channels.json."""
    cache_file = "channels.json"
    channel_data = {}

    # Read from cache
    with CHANNEL_CACHE_LOCK:
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    channel_data = json.load(f)
        except Exception as e:
            MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Error reading channels.json: {e}{Style.RESET_ALL}"))

    # Check if channel_id is in cache
    if channel_id in channel_data:
        return channel_data[channel_id].get("server_name", "Unknown Server")

    # Fetch from Discord API
    try:
        async def fetch_channel_info():
            url = f"https://discord.com/api/v9/channels/{channel_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=account.headers) as response:
                    if response.status == 429:
                        retry_after = float((await response.json()).get("retry_after", 1))
                        MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Rate limited fetching channel info, waiting {retry_after}s{Style.RESET_ALL}"))
                        await asyncio.sleep(retry_after)
                        return await fetch_channel_info()
                    response.raise_for_status()
                    return await response.json()

        channel_info = await fetch_channel_info()
        channel_name = channel_info.get("name", "unknown_channel")
        guild_id = channel_info.get("guild_id")

        server_name = "Unknown Server"
        if guild_id:
            async def fetch_guild_info():
                url = f"https://discord.com/api/v9/guilds/{guild_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=account.headers) as response:
                        if response.status == 429:
                            retry_after = float((await response.json()).get("retry_after", 1))
                            MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Rate limited fetching guild info, waiting {retry_after}s{Style.RESET_ALL}"))
                            await asyncio.sleep(retry_after)
                            return await fetch_guild_info()
                        response.raise_for_status()
                        return await response.json()

            guild_info = await fetch_guild_info()
            server_name = guild_info.get("name", "Unknown Server")

        # Update cache
        channel_data[channel_id] = {
            "channel_name": channel_name,
            "server_name": server_name
        }
        with CHANNEL_CACHE_LOCK:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(channel_data, f, indent=2)
                MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Cached channel {channel_id} with server name {server_name}{Style.RESET_ALL}"))
            except Exception as e:
                MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error writing to channels.json: {e}{Style.RESET_ALL}"))

        return server_name
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error fetching channel info for {channel_id}: {e}{Style.RESET_ALL}"))
        return "Unknown Server"

# Terminal printer task
async def terminal_printer():
    """Consume messages from the queue and print them line by line, handling countdown separately."""
    last_countdown = ""
    while True:
        # Check for countdown update
        with COUNTDOWN_LOCK:
            current_countdown = COUNTDOWN_LINE

        # Print countdown if it exists and has changed
        if current_countdown and current_countdown != last_countdown:
            print(f"\r{current_countdown.ljust(len(last_countdown))}", end='', flush=True)
            last_countdown = current_countdown

        # Check for other messages
        try:
            message = MESSAGE_QUEUE.get_nowait()
            # Clear countdown line before printing new message
            if last_countdown:
                print(f"\r{' ' * len(last_countdown)}\r", end='', flush=True)
            print(message)
            MESSAGE_QUEUE.task_done()
            # Reprint countdown after message
            if current_countdown:
                print(f"\r{current_countdown.ljust(len(last_countdown))}", end='', flush=True)
                last_countdown = current_countdown
        except queue.Empty:
            await asyncio.sleep(0.1)

# SQLite database initialization per account
def init_db(account):
    """Initialize SQLite database for a specific account."""
    db_name = f"conversations{'' if account.index == 0 else account.index + 1}.db"
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                author TEXT,
                content TEXT,
                bot_response TEXT,
                timestamp REAL,
                topic TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT
            )
        """)
        conn.commit()
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}SQLite database initialized at {db_name}{Style.RESET_ALL}"))
        return conn
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error initializing database: {e}{Style.RESET_ALL}"))
        return None

# Load personal info per account
def load_personal_info(account):
    """Load bot's personal info from myinfo.txt, myinfo2.txt, or myinfo3.txt."""
    file_name = f"myinfo{'' if account.index == 0 else account.index + 1}.txt"
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            info = {}
            key = None
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        info[key.lower()] = value
                    elif key == "bio" and line:
                        info[key.lower()] = (info.get(key.lower(), "") + " " + line).strip()
            MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Personal info loaded from {file_name}: {info}{Style.RESET_ALL}"))
            return info
    except FileNotFoundError:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}{file_name} not found, using defaults{Style.RESET_ALL}"))
        return {}
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error loading {file_name}: {e}{Style.RESET_ALL}"))
        return {}

# Memory management functions
def ensure_db_connection(account):
    """Ensure the database connection is open for an account."""
    if account.db_conn is None or (hasattr(account.db_conn, 'cursor') and account.db_conn.cursor() is None):
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Database connection closed, reinitializing...{Style.RESET_ALL}"))
        account.db_conn = init_db(account)
    return account.db_conn

def add_to_memory(account, message_id, author, content, bot_response=None, topic='general'):
    """Add a message and bot response to SQLite memory for an account."""
    try:
        conn = ensure_db_connection(account)
        if conn is None:
            raise Exception("Failed to initialize database connection")
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO memory (message_id, author, content, bot_response, timestamp, topic)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, author, content, bot_response, time.time(), topic))
        c.execute("DELETE FROM memory WHERE timestamp < ?", (time.time() - 24 * 3600,))
        conn.commit()
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.LIGHTCYAN_EX}Added to memory{Style.RESET_ALL}"))
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error adding to memory: {e}{Style.RESET_ALL}"))

def get_memory_context(account):
    """Get recent conversation context from SQLite for an account."""
    try:
        conn = ensure_db_connection(account)
        if conn is None:
            raise Exception("Failed to initialize database connection")
        c = conn.cursor()
        c.execute("SELECT author, content FROM memory ORDER BY timestamp DESC LIMIT 10")
        recent = c.fetchall()
        if recent:
            return "\n".join([f"{author}: {content}" for author, content in recent])
        return ""
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error retrieving memory: {e}{Style.RESET_ALL}"))
        return ""

def has_responded(account, message_id):
    """Check if an account has responded to a message."""
    try:
        conn = ensure_db_connection(account)
        if conn is None:
            raise Exception("Failed to initialize database connection")
        c = conn.cursor()
        c.execute("SELECT bot_response FROM memory WHERE message_id = ?", (message_id,))
        result = c.fetchone()
        return result is not None and result[0] is not None
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error checking response status: {e}{Style.RESET_ALL}"))
        return False

# User profile management
def load_user_profiles(account):
    """Load user profiles from SQLite for an account."""
    try:
        conn = ensure_db_connection(account)
        if conn is None:
            raise Exception("Failed to initialize database connection")
        c = conn.cursor()
        c.execute("SELECT user_id, profile_data FROM user_profiles")
        for user_id, profile_data in c.fetchall():
            account.user_profiles[user_id] = json.loads(profile_data)
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Loaded user profiles{Style.RESET_ALL}"))
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error loading user profiles: {e}{Style.RESET_ALL}"))
        account.user_profiles = {}

def save_user_profiles(account):
    """Save user profiles to SQLite for an account."""
    try:
        conn = ensure_db_connection(account)
        if conn is None:
            raise Exception("Failed to initialize database connection")
        c = conn.cursor()
        for user_id, profile in account.user_profiles.items():
            c.execute("""
                INSERT OR REPLACE INTO user_profiles (user_id, profile_data)
                VALUES (?, ?)
            """, (user_id, json.dumps(profile)))
        conn.commit()
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Saved user profiles{Style.RESET_ALL}"))
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error saving user profiles: {e}{Style.RESET_ALL}"))

def update_user_profile(account, user_id, key, value):
    """Update a user's profile for an account."""
    if user_id not in account.user_profiles:
        account.user_profiles[user_id] = {}
    account.user_profiles[user_id][key] = value
    save_user_profiles(account)

def get_user_profile(account, user_id):
    """Retrieve a user's profile for an account."""
    return account.user_profiles.get(user_id, {})

# Banned words handling
def sanitize_message(message):
    """Replace banned words with ***."""
    sanitized = message.lower()
    for word in BANNED_WORDS:
        sanitized = re.sub(rf'\b{word}\b', '***', sanitized, flags=re.IGNORECASE)
    return sanitized if sanitized != message.lower() else message

async def rephrase_message(account, original_message, mood, sentiment, topic):
    """Rephrase a message to avoid banned words using Gemini AI."""
    try:
        prompt = f"rephrase this to avoid words like {', '.join(BANNED_WORDS)} while keeping the same vibe, mood ({mood}), sentiment ({sentiment}), and topic ({topic}), use plain text, no markdown:\n{original_message}"
        response = account.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.9,
                top_p=0.9,
                max_output_tokens=150
            )
        )
        return response.text.strip() or original_message
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error rephrasing message: {e}{Style.RESET_ALL}"))
        return original_message

# Emoji generation
def get_random_emojis(count=1, mood='chill'):
    """Return random emojis based on mood, used sparingly."""
    emoji_map = {
        'excited': ['🤩', '🥳', '💥', '🎉'],
        'chill': ['😌', '🍃', '🛋️', '✌️', '😎'],
        'sarcastic': ['🙄', '😏', '🤷', '😒', '👀'],
        'joking': ['😂', '🤣', '😜', '😝', '🤡'],
        'lazy': ['😴', '💤', '🛌', '😪', '🥱'],
        'paranoid': ['🫣', '🤐', '👀', '😬', '🙈']
    }
    emojis = emoji_map.get(mood, emoji_map['chill'])
    if random.random() < 0.067:
        return ''.join(random.choice(emojis) for _ in range(count))
    return ''

# Rate limiter for AI requests
class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def can_make_request(self):
        now = time.time()
        self.requests = [t for t in self.requests if now - t < self.time_window]
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

# Mood system
def get_bot_mood(sentiment='neutral'):
    mood_map = {
        'positive': ['excited', 'chill', 'joking'],
        'negative': ['sarcastic', 'paranoid', 'lazy'],
        'neutral': ['chill', 'joking', 'lazy']
    }
    return random.choice(mood_map.get(sentiment, ['chill']))

# Sentiment analysis
def get_sentiment(text):
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return 'positive'
        elif polarity < -0.1:
            return 'negative'
        else:
            return 'neutral'
    except Exception as e:
        MESSAGE_QUEUE.put(f"{Fore.RED}Sentiment analysis error: {e}{Style.RESET_ALL}")
        return 'neutral'

# Topic detection
def detect_topic(text):
    text = text.lower()
    for topic, keywords in TOPICS.items():
        if any(keyword in text for keyword in keywords):
            return topic
    return 'general'

# Profile extraction
def extract_user_preferences(text):
    preferences = {}
    game_match = FAVORITE_GAME_PATTERN.search(text)
    if game_match:
        preferences['favorite_game'] = game_match.group(1)
    food_match = FAVORITE_FOOD_PATTERN.search(text)
    if food_match:
        preferences['favorite_food'] = game_match.group(1)
    anime_match = FAVORITE_ANIME_PATTERN.search(text)
    if anime_match:
        preferences['favorite_anime'] = anime_match.group(1)
    return preferences

# Human-like prompt engineering
def generate_human_prompt(account, prompt, message_type, mood, user_profile, sentiment, topic):
    """Generate a prompt for Gemini AI with account-specific context."""
    account.response_counter = (account.response_counter + 1) % 15
    if account.response_counter == 0:
        account.response_types = []

    single_word_count = account.response_types.count('single_word')
    short_reply_count = account.response_types.count('short')
    long_reply_count = account.response_types.count('long')

    response_type = 'short'  # Default
    length_instruction = "exactly one sentence short and engaging no extra lines"
    max_tokens = 30

    if long_reply_count == 0 and random.random() < 0.267:
        response_type = 'long'
        length_instruction = "write 2 to 4 sentences max with personality no more"
        max_tokens = 100
    elif single_word_count < 3 and random.random() < 0.2:
        response_type = 'single_word'
        length_instruction = "respond with exactly one word like yeah cool nice"
        max_tokens = 10

    account.response_types.append(response_type)

    use_multiple_commas = random.random() < 0.20
    use_self_correction = random.random() < 0.15
    use_disfluencies = random.random() < 0.15
    use_genz_slang = random.random() < 0.10

    punctuation_instruction = "no quotes apostrophes periods semicolons colons dashes underscores just commas or nothing"
    commas_instruction = (
        "use multiple commas sometimes like hey,,, sounds good"
        if use_multiple_commas else "use single commas if needed"
    )
    correction_instruction = (
        "correct yourself sometimes like hold on i mean or my bad"
        if use_self_correction else ""
    )

    disfluency_types = [
        ("Hesitation", ["well", "um"]),
        ("Casual Leads", ["so", "like"]),
        ("Backtracking", ["wait i mean", "my bad"]),
        ("Confirming", ["right", "you know"])
    ]
    selected_disfluencies = []
    if use_disfluencies:
        num_disfluencies = 1 if max_tokens <= 10 else random.randint(1, 2)
        selected_disfluencies = random.sample(disfluency_types, num_disfluencies)
        disfluency_instruction = (
            f"use natural disfluencies like {', '.join([t[0] for t in selected_disfluencies])}. "
            f"examples: {', '.join([f'{t[0]}: {e}' for t in selected_disfluencies for e in t[1]])}"
        )
    else:
        disfluency_instruction = "skip disfluencies unless it fits"

    slang_instruction = (
        "use gen z slang like vibe or chill sparingly only if it fits naturally"
        if use_genz_slang else "avoid gen z slang stick to standard casual words"
    )

    human_instructions = f"""
youre a relaxed witty discord user like a friendly coworker, a real human, keep it casual professional and humanlike like chatting in a work group. heres the vibe:

- {disfluency_instruction}
- {correction_instruction}
- all lowercase no caps unless its a name
- use im not i am, whats not what is, gonna not going to
- {length_instruction}
- {commas_instruction}
- minor typos ok but keep it readable
- no emoji spam add one only if i say so
- stay friendly engaging never robotic think workplace discord energy
- {punctuation_instruction}
- plain text no markdown no ** * _ etc
- avoid banned words like {', '.join(BANNED_WORDS)}
- {slang_instruction}
- stick to the topic {topic} and sentiment {sentiment}
- use myinfo.txt for preferences like favorite anime game food, if asked about something specific like is aot your fav anime check myinfo.txt and respond based on it, if no info say you dont have a fave but suggest something
- no multi line responses unless i say two to four sentences
- generate unique responses that avoid repeating phrases from recent replies
- keep replies concise relevant and non spammy
- use your personal info to differentiate responses without mentioning account numbers
"""

    MODES = {
        'excited': [
            "sound enthusiastic use exclamations like thats awesome",
            "act engaged high energy but professional"
        ],
        'chill': [
            "stay relaxed say cool nice like you’re at ease",
            "keep it simple friendly and approachable"
        ],
        'sarcastic': [
            "use light wit say oh really or nice one",
            "keep it playful but never rude"
        ],
        'joking': [
            "be lighthearted like sharing a workplace joke",
            "keep it fun but appropriate"
        ],
        'lazy': [
            "type like you’re winding down say maybe later or sounds like work",
            "low effort but still friendly"
        ],
        'paranoid': [
            "act cautious say you sure or lets double check",
            "sound careful but not overly serious"
        ]
    }

    templates = {
        'reply': [
            'respond like a friendly coworker engaging witty plain text',
            'chat like you’re keeping the convo going plain text',
            'answer like you’re in a work chat short sharp plain text',
            'hit back like its a casual team talk plain text'
        ],
        'random': [
            'say something engaging like a coworker sparking chat plain text',
            'drop a casual comment like in a team channel plain text',
            'talk like you’re starting a convo witty plain text',
            'throw out something light and relevant plain text'
        ]
    }

    personal_context = (
        f"use this from myinfo.txt to answer preference questions: "
        f"name: {account.personal_info.get('name', 'unknown')}, "
        f"age: {account.personal_info.get('age', 'unknown')}, "
        f"interests: {account.personal_info.get('interests', 'none')}, "
        f"location: {account.personal_info.get('location', 'somewhere')}, "
        f"favorite_anime: {account.personal_info.get('favorite_anime', 'none')}, "
        f"favorite_game: {account.personal_info.get('favorite_game', 'none')}, "
        f"favorite_food: {account.personal_info.get('favorite_food', 'none')}, "
        f"discord_level: {account.personal_info.get('discord_level', 'none')}, "
        f"tvl: {account.personal_info.get('tvl', 'none')}, "
        f"trading_volume: {account.personal_info.get('trading_volume', 'none')}, "
        f"tier: {account.personal_info.get('tier', 'none')}, "
        f"bio: {account.personal_info.get('bio', 'just a chill bot')}"
    )

    memory_context = get_memory_context(account)
    if memory_context:
        memory_context = f"recent chat for context:\n{memory_context}\n"

    user_context = ""
    if user_profile:
        if topic == 'gaming' and 'favorite_game' in user_profile:
            user_context += f"they like {user_profile['favorite_game']} "
        if topic == 'food' and 'favorite_food' in user_profile:
            user_context += f"theyre into {user_profile['favorite_food']} "
        if topic == 'anime' and 'favorite_anime' in user_profile:
            user_context += f"theyre into {user_profile['favorite_anime']} "

    topic_context = f"focus on the topic {topic} and tailor the response to it"

    template = random.choice(templates.get(message_type, MODES[mood]))
    mode_instruction = random.choice(MODES[mood])
    full_prompt = (
        human_instructions + "\n\n" +
        f"reply in english, mood is {mood}, sentiment is {sentiment}, topic is {topic}, {mode_instruction}\n" +
        f"{length_instruction}\n" +
        f"{personal_context}\n{memory_context}\n{user_context}\n{topic_context}\n" +
        f"no usernames, simple words, plain text no markdown\n\n{prompt}"
    )

    return full_prompt, max_tokens

# AI response generation
async def get_gemini_response(account, prompt, message_type='reply', mood='chill', user_profile=None, sentiment='neutral', topic='general'):
    """Generate a response using Gemini AI for an account."""
    ai_rate_limiter = RateLimiter(max_requests=30, time_window=60)
    try:
        if not ai_rate_limiter.can_make_request():
            return None

        full_prompt, max_tokens = generate_human_prompt(account, prompt, message_type, mood, user_profile, sentiment, topic)
        response = account.model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.9,
                top_p=0.9,
                max_output_tokens=max_tokens
            )
        )
        response_text = response.text.strip().lower()
        response_text = re.sub(r'[\*\_\~\`\#\'\"\;\:\-\_]+', '', response_text)
        response_text = response_text.replace("'", "").replace('"', "")

        sentences = [s.strip() for s in response_text.split('.') if s.strip()]
        if max_tokens <= 10:
            response_text = response_text.split()[0]
        elif max_tokens <= 30:
            response_text = sentences[0] if sentences else response_text
        else:
            response_text = ' '.join(sentences[:4]) if sentences else response_text

        response_text += get_random_emojis(1, mood)
        return response_text if response_text else None
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}AI generation error: {e}{Style.RESET_ALL}"))
        return None

# Discord API utilities
async def trigger_typing(account, channel_id):
    """Trigger typing indicator for an account."""
    try:
        url = f"https://discord.com/api/v9/channels/{channel_id}/typing"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=account.headers) as response:
                if response.status == 204:
                    return True
                elif response.status == 429:
                    retry_after = float((await response.json()).get("retry_after", 1))
                    MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Typing rate limited, waiting {retry_after}s{Style.RESET_ALL}"))
                    await asyncio.sleep(retry_after)
                    return await trigger_typing(account, channel_id)
                else:
                    MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Typing failed with status {response.status}{Style.RESET_ALL}"))
                    return False
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Typing error: {e}{Style.RESET_ALL}"))
        return False

def calculate_typing_time(response):
    word_count = len(response.split())
    typing_time = min(5.0, max(3.0, 3.0 + (word_count / 10.0)))
    return typing_time

async def send_reply(account, channel_id, message, delay_range, message_id=None):
    """Send a reply for an account with typing simulation."""
    max_length = 2000
    if len(message) > max_length:
        message = message[:max_length - 3] + "..."
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Message truncated to fit Discord limit{Style.RESET_ALL}"))

    delay = random.uniform(delay_range[0], delay_range[1])
    await asyncio.sleep(delay)

    typing_time = calculate_typing_time(message)
    typing_success = await trigger_typing(account, channel_id)
    if not typing_success:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Typing failed, proceeding without{Style.RESET_ALL}"))
    await asyncio.sleep(typing_time)

    data = {"content": message}
    if message_id:
        data["message_reference"] = {"message_id": message_id}
    result = await make_discord_request(
        account,
        f"https://discord.com/api/v9/channels/{channel_id}/messages",
        method="POST",
        json_data=data
    )
    if result is None:
        return
    MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Sent: {message}{Style.RESET_ALL}"))

async def make_discord_request(account, url, method="GET", json_data=None):
    """Make a Discord API request for an account."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, headers=account.headers, json=json_data) as response:
                if response.status == 429:
                    retry_after = float((await response.json()).get("retry_after", 1))
                    MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Rate limited, waiting {retry_after}s{Style.RESET_ALL}"))
                    await asyncio.sleep(retry_after)
                    return await make_discord_request(account, url, method, json_data)
                if response.status == 400:
                    MESSAGE_QUEUE.put(account.prefix(f"{Fore.YELLOW}Skipping message due to 400 Bad Request{Style.RESET_ALL}"))
                    return None
                if response.content_type != 'application/json':
                    content = await response.text()
                    MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Unknown response type: {response.content_type}, content: {content[:100]}{Style.RESET_ALL}"))
                    raise ValueError(f"Expected JSON, got {response.content_type}")
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Discord API error: {e}{Style.RESET_ALL}"))
            raise

async def fetch_channel_messages(account, channel_id, limit=50):
    """Fetch messages for an account."""
    try:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"
        return await make_discord_request(account, url)
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Error fetching messages: {e}{Style.RESET_ALL}"))
        return []

async def validate_token(account):
    """Validate Discord token for an account."""
    try:
        user_data = await make_discord_request(account, "https://discord.com/api/v9/users/@me")
        if user_data is None:
            return False
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Token validated, user: {user_data.get('username')}{Style.RESET_ALL}"))
        return True
    except Exception as e:
        MESSAGE_QUEUE.put(account.prefix(f"{Fore.RED}Token validation failed: {e}{Style.RESET_ALL}"))
        return False

async def get_bot_user_id(account):
    """Fetch bot user ID and username for an account."""
    user_data = await make_discord_request(account, "https://discord.com/api/v9/users/@me")
    if user_data is None:
        return None
    account.bot_username = user_data.get("username")
    account.bot_user_id = user_data.get("id")
    MESSAGE_QUEUE.put(account.prefix(f"{Fore.GREEN}Bot ID: {account.bot_user_id}, Username: {account.bot_username}{Style.RESET_ALL}"))
    return account.bot_user_id

def is_message_old(timestamp_str):
    try:
        message_time = isoparse(timestamp_str).timestamp()
        return time.time() - message_time > 300
    except Exception:
        return True

# Terminal UI utilities
def print_header():
    header = """
╭──────────────────────────────────────────────────────────╮
│   🤖  Discord Chat Bot by Nabil - Version 5.0            │
│   ⚡  Multi-Account · Smart · Humanlike · Gemini-Powered │
│   🌐  github.com/xNabil                                  │
╰──────────────────────────────────────────────────────────╯
    """
    MESSAGE_QUEUE.put(f"{Fore.CYAN}{Style.BRIGHT}{header}{Style.RESET_ALL}")

def print_status(account, message, status_type='info'):
    colors = {
        'info': account.color,
        'success': Fore.GREEN,
        'error': Fore.RED,
        'warning': Fore.YELLOW
    }
    color = colors.get(status_type, account.color)
    MESSAGE_QUEUE.put(f"{account.prefix(f'{color}{Style.BRIGHT}{message}{Style.RESET_ALL}')}")

async def print_countdown(account, seconds, message="Waiting"):
    """Track slow mode timer for an account without animation."""
    if seconds < 1:
        return
    with SLOW_MODE_LOCK:
        SLOW_MODE_TIMERS[account.index] = seconds
    start_time = time.time()
    elapsed = 0
    check_interval = 2.0
    while elapsed < seconds:
        with SLOW_MODE_LOCK:
            SLOW_MODE_TIMERS[account.index] = max(0, seconds - elapsed)
        elapsed = time.time() - start_time
        if elapsed % check_interval < 0.1 or elapsed >= seconds:
            for channel_id in CHANNEL_IDS:
                server_name = await get_channel_name(account, channel_id)
                messages = await fetch_channel_messages(account, channel_id, 50)
                if messages:
                    new_replies = [
                        msg for msg in messages
                        if msg.get("referenced_message", {}).get("author", {}).get("id") == account.bot_user_id
                        and not is_message_old(msg.get("timestamp", ""))
                        and not has_responded(account, msg.get("id"))
                        and msg.get("id") not in account.responded_messages
                        and msg not in account.pending_replies
                    ]
                    for reply in new_replies:
                        account.pending_replies.append(reply)
                        print_status(
                            account,
                            f"Queued reply from {Fore.BLUE}{reply['author']['username']}{Style.RESET_ALL}: "
                            f"{Fore.YELLOW}{reply['content']}{Style.RESET_ALL} in {server_name}",
                            'info'
                        )
        await asyncio.sleep(0.1)
    with SLOW_MODE_LOCK:
        SLOW_MODE_TIMERS[account.index] = 0

async def print_slowmode_status():
    """Update the global countdown line for all accounts."""
    global COUNTDOWN_LINE
    while True:
        with SLOW_MODE_LOCK:
            timers = [
                f"{ACCOUNTS[i].color}[ACC {i + 1} - {ACCOUNTS[i].bot_username or 'Unknown'}]-{int(t)}s{Style.RESET_ALL}"
                for i, t in SLOW_MODE_TIMERS.items() if t > 0
            ]
            with COUNTDOWN_LOCK:
                COUNTDOWN_LINE = f"In slowmode {' '.join(timers)}" if timers else ""
        await asyncio.sleep(1)

# Main bot logic for a single account
async def run_account(account, slow_mode_range):
    print_status(account, "Getting bot ready...", 'info')

    if not await validate_token(account):
        print_status(account, "DISCORD_TOKEN is invalid, shutting down...", 'error')
        return

    load_user_profiles(account)
    if not await get_bot_user_id(account):
        print_status(account, "Can’t grab bot ID, check DISCORD_TOKEN", 'error')
        return

    try:
        while True:
            try:
                wait_time = random.uniform(*slow_mode_range)
                await print_countdown(account, wait_time)

                for channel_id in CHANNEL_IDS:
                    server_name = await get_channel_name(account, channel_id)
                    print_status(account, f"Processing {server_name}", 'info')

                    messages = await fetch_channel_messages(account, channel_id, 50)
                    if not messages:
                        print_status(account, f"No messages found in {server_name}, trying again...", 'warning')
                        continue

                    for msg in messages:
                        prefs = extract_user_preferences(msg.get('content', ''))
                        for key, value in prefs.items():
                            update_user_profile(account, msg['author']['id'], key, value)

                    other_messages = [
                        msg for msg in messages
                        if msg.get("content")
                        and not is_message_old(msg.get("timestamp", ""))
                        and msg.get("author", {}).get("id") != account.bot_user_id
                        and not has_responded(account, msg.get("id"))
                        and msg.get("id") not in account.responded_messages
                        and msg not in account.pending_replies
                    ]

                    # Determine the dominant topic and sentiment from recent messages
                    recent_topics = [detect_topic(msg.get('content', '')) for msg in messages[:5]]
                    recent_sentiments = [get_sentiment(msg.get('content', '')) for msg in messages[:5]]
                    dominant_topic = max(set(recent_topics), key=recent_topics.count, default='general')
                    dominant_sentiment = max(set(recent_sentiments), key=recent_sentiments.count, default='neutral')
                    mood = get_bot_mood(dominant_sentiment)

                    last_message_time = max([isoparse(msg['timestamp']).timestamp() for msg in messages if msg.get('timestamp')])
                    if time.time() - last_message_time > 300 and random.random() < 0.2:
                        print_status(account, f"Chat’s quiet in {server_name}, starting something...", 'info')
                        # Generate a dynamic prompt for a random message
                        memory_context = get_memory_context(account)
                        prompt = (
                            f"the chat has been quiet for a while, start a new conversation "
                            f"based on the recent topic ({dominant_topic}) and sentiment ({dominant_sentiment}). "
                            f"consider this recent chat history:\n{memory_context}\n"
                            f"create a casual, engaging message to spark discussion, "
                            f"tailored to the topic and mood ({mood})."
                        )
                        response = await get_gemini_response(account, prompt, 'random', mood, None, dominant_sentiment, dominant_topic)
                        if response:
                            await send_reply(account, channel_id, response, (0, 2))
                            add_to_memory(account, None, account.bot_username, prompt, response, dominant_topic)
                        continue

                    target_message = None
                    if account.pending_replies:
                        target_message = account.pending_replies.popleft()
                        print_status(account, f"Responding to queued reply from {target_message['author']['username']} in {server_name}", 'info')
                    elif other_messages and random.random() < 0.99:
                        target_message = random.choice(other_messages)
                        print_status(account, f"Replying to other message from {target_message['author']['username']} in {server_name}", 'info')
                    else:
                        print_status(account, f"No replies in {server_name}, sending random message", 'info')
                        # Generate a dynamic prompt for a random message
                        memory_context = get_memory_context(account)
                        prompt = (
                            f"the chat is active, contribute to the conversation "
                            f"based on the recent topic ({dominant_topic}) and sentiment ({dominant_sentiment}). "
                            f"consider this recent chat history:\n{memory_context}\n"
                            f"create a casual, engaging message to keep the discussion going, "
                            f"tailored to the topic and mood ({mood})."
                        )
                        response = await get_gemini_response(account, prompt, 'random', mood, None, dominant_sentiment, dominant_topic)
                        if response:
                            await send_reply(account, channel_id, response, (0, 2))
                            add_to_memory(account, None, account.bot_username, prompt, response, dominant_topic)
                        continue

                    sentiment = get_sentiment(target_message['content'])
                    topic = detect_topic(target_message['content'])
                    mood = get_bot_mood(sentiment)
                    user_profile = get_user_profile(account, target_message['author']['id'])

                    context = f"they said: {target_message['content']}"
                    prompt = (
                        f"you’re a chill discord user responding to this:\n{context}\n"
                        f"create a unique, engaging reply that matches the topic ({topic}), "
                        f"sentiment ({sentiment}), and mood ({mood})."
                    )
                    response = await get_gemini_response(account, prompt, 'reply', mood, user_profile, sentiment, topic)

                    if response:
                        print_status(
                            account,
                            f"Replying to [ {Fore.BLUE}{target_message['author']['username']}{Style.RESET_ALL} ]: "
                            f"{Fore.YELLOW}{target_message['content']}{Style.RESET_ALL} in {server_name}",
                            'info'
                        )
                        await send_reply(account, channel_id, response, (0, 2), target_message.get("id"))
                        add_to_memory(account, target_message['id'], target_message['author']['username'], target_message['content'], response, topic)
                        account.responded_messages.append(target_message['id'])

                    # Add delay between channels (2-5 seconds)
                    channel_delay = random.uniform(2, 5)
                    print_status(account, f"Waiting {channel_delay:.2f}s before processing next channel", 'info')
                    await asyncio.sleep(channel_delay)

            except Exception as e:
                print_status(account, f"Main loop error: {e}", 'error')
                await asyncio.sleep(5)

    except KeyboardInterrupt:
        print_status(account, "Shutting down bot...", 'info')
    finally:
        if account.db_conn is not None:
            account.db_conn.close()
            print_status(account, "Database connection closed", 'info')

# Main entry point for multi-account bot
async def main():
    print_header()  # Display banner once at startup
    # Initialize each account
    slow_mode_range = (60, 180)  # Default slow mode
    if SLOW_MODE:
        try:
            min_delay, max_delay = map(int, SLOW_MODE.split(','))
            slow_mode_range = (min_delay, max_delay)
        except:
            MESSAGE_QUEUE.put(f"{Fore.RED}SLOW_MODE invalid, using 60-180s default{Style.RESET_ALL}")

    for account in ACCOUNTS:
        # Configure Gemini AI for the account
        try:
            genai.configure(api_key=account.gemini_key)
            account.model = genai.GenerativeModel("gemini-2.5-flash")
            print_status(account, "Gemini AI configured successfully", 'success')
        except Exception as e:
            print_status(account, f"Error configuring Gemini AI: {e}", 'error')
            continue

        # Initialize database and personal info
        account.db_conn = init_db(account)
        account.personal_info = load_personal_info(account)

    # Start terminal printer and slow mode status tasks
    tasks = [
        terminal_printer(),
        print_slowmode_status(),
        *[run_account(account, slow_mode_range) for account in ACCOUNTS]
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    print_status(ACCOUNTS[0], f"Starting bot with {len(ACCOUNTS)} accounts and {len(CHANNEL_IDS)} channels...", 'info')
    asyncio.run(main())