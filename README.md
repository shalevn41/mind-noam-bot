# 🤖 Mind Noam Bot

A Telegram AI assistant that answers questions in Hebrew using real-time web search.

## ✨ Features

- 💬 Conversational AI powered by Groq llama-3.3-70b
- 🔍 Real-time web search via Tavily API
- 🧠 Conversation memory per user
- 🇮🇱 Hebrew-first responses
- ⚡ Fast response time with streaming

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| python-telegram-bot | Telegram integration |
| Groq API (llama-3.3-70b) | LLM engine |
| Tavily API | Real-time web search |
| Railway | Cloud deployment |

## 🚀 How It Works

1. User sends a message on Telegram
2. Bot searches the web via Tavily for relevant info
3. Groq llama-3.3-70b generates a response in Hebrew
4. Response is sent back to the user with memory of the conversation

## ⚙️ Setup

1. Clone the repo
2. Create a `.env` file with:
