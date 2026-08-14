# OutreachIQ — AI-Powered LinkedIn Outreach Agent

OutreachIQ is an AI-powered outreach assistant that generates personalized LinkedIn outreach messages from profile information, product/service context, and a selected communication tone.

Instead of producing generic outreach, OutreachIQ uses an AI agent and tool calling to extract relevant profile information and generate a message tailored to the recipient.

> **Important:** OutreachIQ generates outreach drafts. It does not automatically send LinkedIn messages or perform mass automated outreach.

---

## 🚀 Features

* 🤖 **AI Agent** using LangChain tool calling
* 👤 **Profile parsing** from supplied profile text
* ✍️ **Personalized outreach generation**
* 🎯 **Multiple tones**

  * Casual
  * Formal
  * Technical
* 🔒 **Pydantic validation** for requests and responses
* ⚡ **FastAPI REST API**
* 📦 **Batch outreach processing**
* 📄 **CSV export**
* 🛡️ **Ethical outreach design**
* 🧪 **Automated tests using pytest**

---

## 🏗️ Architecture

```text
                    User
                      │
                      ▼
                  FastAPI
                      │
                      ▼
              Pydantic Validation
                      │
                      ▼
             Custom Tool-Calling Agent
                      │
             ┌────────┴────────┐
             ▼                 ▼
      scrape_profile     generate_message
             │                 │
             ▼                 ▼
   ProfileScraper Pipeline  Self-Correction Evaluator
             │                 │
             ▼                 ▼
          Cache / HTTP      Gemini LLM
             │                 │
             └────────┬────────┘
                      ▼
                 OutreachMessage
                      │
                      ▼
                API Response
```

The agent is designed to call the profile extraction tool before generating the final outreach message, which is then automatically evaluated and improved via a self-correction loop.

---

## 🔄 How It Works

### 1. Provide profile information

The application receives profile information along with:

* Product/service description
* Desired outreach tone

### 2. Validate the request

FastAPI receives the request and Pydantic validates the input structure.

### 3. Run the AI agent

The LangChain agent coordinates the required tools.

The intended workflow is:

```text
scrape_profile
      ↓
generate_outreach
```

### 4. Extract profile information

The profile parser extracts structured information such as:

* Name
* Headline
* About
* Recent activity

### 5. Generate the message

The message generation tool combines:

* Recipient profile
* Product/service description
* Selected tone

and sends the resulting prompt to the Gemini model.

### 6. Validate the output

The generated response is validated using the `OutreachMessage` Pydantic model.

### 7. Return the result

The final personalized outreach message is returned through the API.

---

## 🛠️ Tech Stack

| Technology                       | Purpose                   |
| -------------------------------- | ------------------------- |
| **Python**                       | Core programming language |
| **FastAPI**                      | REST API                  |
| **Pydantic**                     | Data validation           |
| **LangChain**                    | AI agent and tool calling |
| **Google Gemini**                | Message generation        |
| **BeautifulSoup / Parser logic** | Profile text processing   |
| **Pandas**                       | CSV export                |
| **Pytest**                       | Automated testing         |

---

## 📁 Project Structure

```text
outreachiq/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── models/
│   │   ├── request_models.py
│   │   ├── response_models.py
│   │   └── profile_models.py
│   │
│   ├── scraper/
│   │   ├── profile_scraper.py
│   │   ├── parser.py
│   │   └── rate_limiter.py
│   │
│   ├── agent/
│   │   ├── tools.py
│   │   ├── agent_core.py
│   │   └── prompts.py
│   │
│   ├── generator/
│   │   ├── message_builder.py
│   │   └── tone_templates.py
│   │
│   ├── export/
│   │   └── csv_exporter.py
│   │
│   └── api/
│       └── routes.py
│
├── tests/
│   ├── test_models.py
│   ├── test_agent.py
│   └── test_scraper.py
│
├── docs/
│   ├── architecture.md
│   └── ethical_use.md
│
├── scripts/
│   └── test.py
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd outreachiq
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file from `.env.example`:

```powershell
copy .env.example .env
```

Add your Gemini API key and required configuration.

> Never commit `.env` or API keys to GitHub.

---

## ▶️ Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI's interactive Swagger documentation is available at:

```text
http://localhost:8000/docs
```

---

## 📡 API Endpoints

### Generate a single message (JSON)

```http
POST /generate
```

Accepts either `profile_text` (raw pasted profile text) or `profile_url` (for pre-registered fixtures).

Example request:

```json
{
  "profile_text": "John Doe\nAI Engineer at OpenAI\nAbout\nBuilding AI agents using LangChain.\nRecent Activity\n- Published a post about RAG.",
  "product_description": "AI-powered automation platform for building intelligent business workflows.",
  "tone": "casual"
}
```

Example response:

```json
{
  "recipient_name": "John Doe",
  "message": "Personalized outreach message...",
  "reason_for_outreach": "Their work with AI agents is relevant."
}
```

---

### Generate from PDF (Multipart)

```http
POST /generate-from-pdf
```

Accepts a PDF file upload containing the profile text. The PDF is processed in-memory and deleted immediately.

Parameters (multipart/form-data):
- `profile_pdf`: The PDF file upload
- `product_description`: String description of your product
- `tone`: e.g., "casual"

---

### Generate messages in batch

```http
POST /generate-batch
```

This endpoint accepts multiple outreach requests and processes them as a batch.
The batch workflow is designed so that a failure for one profile does not necessarily prevent other profiles from being processed.

---

## 🧪 Testing

OutreachIQ uses `pytest` for automated testing.

Run the complete test suite:

```bash
python -m pytest
```

Run tests with detailed output:

```bash
python -m pytest -v
```

Run a specific test file:

```bash
python -m pytest tests/test_models.py -v
```

Current tests cover:

* Pydantic model validation
* Invalid request handling
* Agent output handling
* Agent failure handling
* Profile parsing
* Missing profile sections
* Malformed profile input

---

## 🛡️ Ethical Design

OutreachIQ is intentionally designed as a **human-in-the-loop outreach assistant**.

It does not:

* Automatically send LinkedIn messages
* Perform mass automated outreach
* Scrape private profile information
* Automate user accounts or login sessions

The goal is to help users create better outreach drafts while keeping the final decision and sending action with the human user.

See [`docs/ethical_use.md`](docs/ethical_use.md) for more details.

---

## 🔮 Future Improvements

Potential future improvements include:

* More robust profile parsing
* Public-profile data extraction where appropriate
* Improved personalization scoring
* Message quality evaluation
* Additional LLM providers
* Better batch processing
* Persistent outreach history
* Authentication and user accounts
* More advanced outreach analytics

---

## 📚 Documentation

Additional documentation:

* [`docs/architecture.md`](docs/architecture.md)
* [`docs/ethical_use.md`](docs/ethical_use.md)

---

## 🎯 Project Goal

The goal of OutreachIQ is not simply to generate text with an LLM.

The project demonstrates how multiple software engineering and AI concepts can be combined into a practical system:

```text
FastAPI
   +
Pydantic
   +
LangChain Agent
   +
Tool Calling
   +
Prompt Engineering
   +
LLM
   +
Testing
```

The project also demonstrates responsible AI product design by keeping a human in the loop instead of automating message delivery.

---

## 👨‍💻 Author

**Your Name**

Built as a practical AI engineering project focused on agentic workflows, API development, structured LLM outputs, and responsible automation.
