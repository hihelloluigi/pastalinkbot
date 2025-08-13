# PAstaLinkBot 🍝

A Telegram bot that helps users quickly find **official links** for Italian public services (PA) — no bureaucracy spaghetti, just the right link in one click.

Supports **Italian** 🇮🇹 and **English** 🇬🇧 based on the user's Telegram language setting.

---

## ✨ Features

- **Quick public service search**  
  Examples: Health record (FSE), car tax (bollo auto), driving license renewal, ANPR certificates, IO/PagoPA, CUP, school enrolments, waste tax.
- **Bilingual responses** (IT/EN) automatically detected.
- **Smalltalk**: friendly answers to greetings and casual chat.
- **Off-topic detection**: tells the user what the bot can do if they ask unrelated questions.
- **Typing indicator** while searching.
- **LLM-powered intent classification** using [Ollama](https://ollama.com).

---

## 📦 Requirements

- Python **3.10+** (tested on 3.13.1)
- [Telegram Bot Token](https://core.telegram.org/bots#how-do-i-create-a-bot)  
- [Ollama](https://ollama.com) installed locally

---

## 🚀 Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourname/telegram-pa-bot.git
cd telegram-pa-bot
```

1. **Set up Python virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate
```

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

1. **Configure environment variables**  

Create a `.env` file:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
DATA_PATH=./data/pa_bot_links_seed.json
```

---

## 🤖 LLM Setup with Ollama

We use **LLaMA 3.1 8B** for natural language understanding.

1. **Install Ollama**  
   [Download & Install Ollama](https://ollama.com/download)

2. **Pull the model**

```bash
ollama pull llama3.1:8b
```

*(If you have less than 16GB RAM, you can use a quantized version: `ollama pull llama3.1:8b-q4_K_M`)*

1. **Run Ollama in the background**

```bash
ollama serve
```

1. **Test the model**

```bash
ollama run llama3.1:8b "Hello from PAstaLinkBot!"
```

---

## ▶️ Running the Bot

Once everything is installed:

```bash
source .venv/bin/activate
python bot.py
```

The bot will start polling and will reply to your Telegram messages.

---

## 💡 Example Commands

**In Italian:**

``` txt
Dove vedo le ricette del mio dottore?
Dove pago il bollo auto?
Come rinnovo la patente?
```

**In English:**

``` txt
Where do I see my doctor's prescriptions?
Where do I pay the car tax?
How do I renew my driving license?
```

---

## 🛠 Project Structure

``` txt
telegram-pa-bot/
├── bot.py                 # Main bot code
├── llm.py                 # LLM interaction with Ollama
├── data/
│   └── pa_bot_links_seed.json   # Public service links database
├── requirements.txt
└── README.md
```

---

## 📜 License

MIT License. Free to use, modify, and share.
