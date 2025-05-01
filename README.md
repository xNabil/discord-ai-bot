# Discord Gemini Chat Bot

A simple Discord self-bot that uses **Gemini AI** to automatically reply, handle mentions, and engage in conversations. Great for automating tasks like leveling up in servers for **airdrops** and participating in events that require activity.

---

## 📜 Overview
**Discord Gemini Chat Bot** is a **Python-based auto bot** designed to work as a **Discord self-bot**. It leverages **Gemini AI** for natural, **conversational interactions**, making your Discord server more engaging and interactive. The bot automatically replies to messages, mentions, and conversations, **personalizing responses** with different moods and languages.

⚡ _Ideal for automating Discord interactions, creating a self-bot for fun, or using it for specific tasks like leveling up in servers for **airdrops** or participating in events that require activity on platforms like **Mee6 bot**._

## 🚀 Features
- **AI-Driven Responses**: Converses using Gemini AI with natural, context-aware replies.
- **Reply & Mention Priority**: Instantly responds to direct mentions and replies.
- **Multi-Language Support**: English, Hindi, Spanish, French, and German out of the box.
- **Conversation Memory**: Maintains up to 50 past interactions for smarter conversations.
- **Customizable Slow Mode**: Control message scanning intervals via `.env` (`60`, `65`, etc.).
- **Mood Variations**: Randomized tones — excited, chill, sarcastic — with emojis.
- **Personalization**: Integrates details from `myinfo.txt` to craft customized responses.
- **Rate Limiting Handling**: Smart retry system for Discord and Gemini API limits.

---

## 🔑 How to Get Your Tokens

### How to Get a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Log in with your Google account.
3. Click on **Get API Key** or navigate to the **API Keys** section.
4. Create a new API key or copy an existing one.
5. Save the API key — you will need it for the `.env` file.

> ⚡ You must have a Google Cloud billing account set up (even if you're within the free tier).

---

### 🔓 Discord User Token
> ⚠️ **Warning:** Using a **user token** violates Discord’s **Terms of Service** and can lead to account bans. Use for personal/educational purposes only.

1. Open [Discord Web](https://discord.com/channels/@me) and log in.  
2. Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (Mac) to open Developer Tools.  
3. Switch to the **Network** tab and refresh the page (`F5`).  
4. Filter by `api` and find a request like `/api/v9/users/@me`.  

**Another Method Instead of digging through Headers**,
 Open [Discord Web](https://discord.com/channels/@me)
 open Developer Tools or inspect element 
 switch to the **Console** tab and paste the Commands blow 
 
     
     allow pasting
      
   - **Then paste** the following snippet and hit **Enter**:
     ```js
     (
         webpackChunkdiscord_app.push(
             [
                 [''],
                 {},
                 e => {
                     m = [];
                     for (let c in e.c)
                         m.push(e.c[c]);
                 }
             ]
         ),
         m
     ).find(
         m => m?.exports?.default?.getToken !== void 0
     ).exports.default.getToken()
     ```  
   - The console will print your **Discord user token**.  
6. Copy and **keep it secure** — never share it publicly.

---
## 🔑 How to Get Your Discord Channel ID

To get the **Channel ID**, follow these steps:
you can get the Channel ID directly from the URL of the channel:

1. Go to the channel in your browser.
2. Copy the **Channel ID** from the URL. It’s the second part of the URL after `/channels/`.
   - Example URL: `https://discord.com/channels/948033443483254845/1027161980970205225`
   - **Channel ID**: `1027161980970205225`

Copy the **Channel ID** and paste it into your `.env` file or wherever you need it in your bot configuration.


## 🧰 Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/xNabil/discord-ai-bot.git
   cd discord-ai-bot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup the `.env` File**
   Create a file named `.env` in the root directory and add:
   ```env
   DISCORD_TOKEN=your_discord_user_token
   GEMINI_API_KEY=your_gemini_api_key
   SLOW_MODE=60,65
   ```

4. **(Optional) Customize Personal Info**
   Edit `myinfo.txt` to add your personal data (e.g., name, hobbies, favorite phrases) for more personalized replies.

---

## ▶️ Usage

To run the bot:
```bash
python bot.py
```

The bot will quietly monitor your Discord messages and respond where appropriate based on your settings.

---


### Use Case: Level Up for Airdrops
One of the common use cases for this bot is **leveling up in Discord servers**. Many **airdrops** or events require users to gain levels or activity in certain Discord servers. By using the **Mee6 bot** or similar bots that track activity, you can **automatically generate messages** and **interact in channels**, helping you level up faster without manual input.

With the **Gemini AI-powered responses**, the bot can interact naturally in servers, completing tasks such as:
- Participating in chat and events.
- Responding to messages or mentions.
- Completing simple tasks that would otherwise require manual input.

This makes the **Discord Gemini Chat Bot** a powerful tool for automating your Discord experience and enhancing your **airdrops strategy** or **server activities**.


## 📦 Prerequisites
- [Python 3.8+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- A Discord account
- A Gemini API key

---
## 👨‍💻 Author

- **Nabil** – [GitHub: xNabil](https://github.com/xNabil)

---

## ❤️ A Final Note

> **“Built for fun. Built for learning.  
> Not built for getting banned.  
> Use with caution.”**

---
