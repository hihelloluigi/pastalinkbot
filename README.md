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

## 📦 Dependency Management

This project uses modern Python packaging with `pyproject.toml` and a split requirements system:

- Core dependencies: `requirements/base.txt`
- Development: `requirements/dev.txt`
- Testing: `requirements/test.txt`
- Production: `requirements/prod.txt`

Install dependencies with one of the following:

```bash
# Recommended for development
pip install -e .[dev]

# For testing only
pip install -e .[test]

# For production
pip install -e .

# Or use requirements files directly
pip install -r requirements/dev.txt
pip install -r requirements/test.txt
pip install -r requirements/prod.txt
```

---

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

_(If you have less than 16GB RAM, you can use a quantized version: `ollama pull llama3.1:8b-q4_K_M`)_

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

## 🧪 Running Tests

Tests use `pytest` and are organized in the `tests/` directory. You can run tests with:

```bash
pytest
```

Or use the custom test runner for advanced options:

```bash
python run_tests.py --type all        # Run all tests
python run_tests.py --type unit       # Run unit tests only
python run_tests.py --type integration # Run integration tests only
python run_tests.py --type coverage   # Run tests with coverage (see htmlcov/)
python run_tests.py --type quick      # Run all except slow tests
python run_tests.py --type basic      # Run basic smoke tests
```

Test markers: `unit`, `integration`, `slow` (see `tests/`).

---

## 🛠 Makefile Shortcuts

Common development tasks are available via the Makefile:

### Dependency Installation

```bash
make install-base        # Install base dependencies
make install-prod        # Install production dependencies
make install-dev         # Install development dependencies
make install-test        # Install test dependencies
make install-dev-modern  # Install dev deps via pyproject.toml
make install-test-modern # Install test deps via pyproject.toml
```

### Testing

```bash
make test                # Run all tests
make test-coverage       # Run tests with coverage
make test-fail-fast      # Run tests and stop on first failure
make test-verbose        # Run tests with verbose output
```

### Internationalization (i18n)

```bash
make i18n-extract        # Extract translatable strings
make i18n-init           # Initialize .po files for each language
make i18n-compile        # Compile .po files to .mo
make i18n-refresh        # Refresh translations
```

### Linting & Code Quality

```bash
make lint                # Run code quality and lint checks
```

---

## 💡 Example Commands

**In Italian:**

```txt
Dove vedo le ricette del mio dottore?
Dove pago il bollo auto?
Come rinnovo la patente?
```

**In English:**

```txt
Where do I see my doctor's prescriptions?
Where do I pay the car tax?
How do I renew my driving license?
```

---

## 🛠 Project Structure

```txt
telegram-pa-bot/
├── bot.py                 # Main bot code
├── llm.py                 # LLM interaction with Ollama
├── data/
│   └── pa_bot_links_seed.json   # Public service links database
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

### Expanding the Database

Want to help make PAstaLinkBot more useful? You can contribute by expanding the database of public service links!

The bot uses a JSON database located at `data/pa_bot_links_seed.json` that contains Italian public service links. If you know of additional services that should be included, feel free to:

1. **Fork the repository**
2. **Add new entries** to the database file
3. **Create a pull request** with your additions

Each entry should include:

- **intent**: Main category of the service (e.g., "fascicolo_sanitario", "bollo_auto", "patente")
- **sub_intent**: Specific subcategory or action (e.g., "accesso_fse", "calcolo_bollo", "rinnovo_patente_info")
- **region**: Geographic scope ("Nazionale" for national services, or specific region name)
- **label**: Human-readable name for the service
- **url**: The official link to the service
- **notes**: Brief explanation or additional information about the service

### Example Database Entry

```json
{
  "intent": "fascicolo_sanitario",
  "sub_intent": "accesso_fse",
  "region": "Lombardia",
  "label": "FSE Lombardia",
  "url": "https://www.fascicolosanitario.regione.lombardia.it/",
  "notes": "Accesso con SPID/CIE/CNS"
}
```

Your contributions help make Italian public services more accessible to everyone! 🇮🇹

---

## 📜 License

MIT License. Free to use, modify, and share.
