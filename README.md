

- ## **If you face any issues running the bot open a [issue here.](https://github.com/xNabil/discord-ai-bot/issues)**



# Discord Gemini Chat Bot

A multi-account Discord chat bot powered by Google Gemini AI, designed to engage in human-like conversations in a Discord channel. Features include topic detection, sentiment analysis, banned words handling, user profiling, and a professional yet casual tone.

## 🚀 Features & Capabilities
- Multi-account & multi-server support  
- Smart channel/server caching (`channels.json`)  
- Gemini AI-powered replies  
- Humanlike style: slang, typos, emoji, self-correction  
- Topic & sentiment detection  
- User profiling & personalization (`myinfo.txt`)  
- Per-account conversation memory (SQLite)  
- Banned words handling & AI rephrase  
- Reply/mention priority  
- Slowmode & rate-limit aware  
- Typing simulation  
- Custom colored terminal output  
- Duplicate response prevention  
- Configurable response cycles  
- Robust logging & warning suppression  


## 🧰 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/xNabil/discord-ai-bot.git
   cd discord-ai-bot
   ```
 **Windows Automatic Setup (Recommended):**
   - Run the provided batch script to help set up the bot and environment variables:
     ```
     run.bat
     ```
   - This will guide you through the initial configuration ( including step 2. **Install dependencies:**)

**Manual Setup:**  
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Requires Python 3.8+)*

3. **Prepare your environment variables:**  
   Create a `.env` file in the repo root (see below).

---

## ⚙️ .env Setup (v5.0)

The `.env` file supports multiple accounts and multiple channels.

```
DISCORD_TOKEN=token1,token2,token3
GEMINI_API_KEY=key1,key2,key3
CHANNEL_ID="channelid1,channelid2,channelid3"
SLOW_MODE="60,180"
```

- **DISCORD_TOKEN**: Comma-separated list of Discord tokens for each account (max 3).
- **GEMINI_API_KEY**: Comma-separated list of Gemini API keys—one per account.
- **CHANNEL_ID**: Comma-separated list of Discord channel IDs to monitor/reply in.
- **SLOW_MODE**: Minimum and maximum seconds between replies (e.g. `60,180` for 1-3 minutes).

---
## 🔑 How to Get Your Tokens for the `.env`

### How to Get a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Log in with your Google account.
3. Click on **Get API Key** or navigate to the **API Keys** section.
4. Create a new API key or copy an existing one.
5. Save the API key — you will need it for the `.env` file.

> ⚠️ **Important:** One `API_KEY` can generate **15 Requests Per Minute (RPM)** & **1000 Requests Per Day (RPD)**. So it is advised to use multiple Gemini `API KEYS` in the `.env` according to your needs.
---

## 🔓 How to Get Your Discord User Token

> ⚠️ **Warning:** Using a Discord user token violates Discord’s Terms of Service and can lead to account bans. Use for personal or educational purposes only.

1. Open [Discord Web](https://discord.com/channels/@me) and log in.
2. Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (Mac) to open Developer Tools.
3. Switch to the **Network** tab.
4. Refresh the page (`F5`).
5. In the filter/search box, type `api` to filter network requests.
6. Click on a request like `/api/v9/users/@me`.
7. In the **Headers** tab, scroll down to **Request Headers** and look for the line starting with `authorization:`.
8. The value after `authorization:` is your Discord user token.
![Screenshot](https://github.com/xNabil/xnabil/blob/main/assets/images/discordauthtoken.jpg)
Copy and **keep it secure**—never share your token publicly. 

---
 🔑 How to Get Your Discord Channel ID

To get the **Channel ID**, follow these steps:
you can get the Channel ID directly from the URL of the channel:

1. Go to the channel in your browser.
2. Copy the **Channel ID** from the URL. It’s the second part of the URL after `/channels/`.
   - Example URL: `https://discord.com/channels/948033443483254845/1027161980970205225`
   - **Channel ID**: `1027161980970205225`

Copy the **Channel ID** and paste it into your `.env` file or wherever you need it in your bot configuration.


### **4.(Optional) Customize Personal Info**
   Edit `myinfo.txt` to add your personal data (e.g., name, hobbies, favorite phrases) for more personalized replies.
   For each bot account, create a separate info file:
- `myinfo.txt` (for account 1)
- `myinfo2.txt` (for account 2)
- `myinfo3.txt` (for account 3)


---

## ▶️ Usage

To run the bot:
```bash
python bot.py
```

The bot will quietly monitor your Discord messages and respond where appropriate based on your settings.

---


### Use Case: Level Up for Airdrops
One of the common use cases for this bot is **leveling up in Discord servers**.
With the **Gemini AI-powered responses**, the bot can interact naturally in servers, completing tasks such as:
- Participating in chat and events.
- Responding to messages or mentions.
- Completing simple tasks that would otherwise require manual input.


## 📦 Prerequisites
- [Python 3.8+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- A Discord account
- A Gemini API key

---
## 👨‍💻 Author

- **Nabil** – [GitHub: xNabil](https://github.com/xNabil)

---

## Donate 💸
Love the bot? Wanna fuel more WAGMI vibes? Drop some crypto love to keep the charts lit! 🙌
- **SUI**: `0x8ffde56ce74ddd5fe0095edbabb054a63f33c807fa4f6d5dc982e30133c239e8`
- **USDT (TRC20)**: `TG8JGN59e8iqF3XzcD26WPL8Zd1R5So7hm`
- **BNB (BEP20)**: `0xe6bf8386077c04a9cc05aca44ee0fc2fe553eff1`
- **Binance UID**:`921100473`

Every bit helps me grind harder and keep this bot stacking bags! 😎

## ❤️ A Final Note

> **“Built for fun. Built for learning.  
> Not built for getting banned.  
> Use with caution.”**

---
