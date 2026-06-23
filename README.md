# LogStream AI - Intelligent Document & Log Summarizer

LogStream AI is a modern, high-performance web application designed to ingest, process, and summarize large log files and documents using AI, enabling interactive Q&A chat interfaces over the uploaded content.

---

## 🏗️ Project Architecture

The application is structured as a multi-service containerized environment orchestrated by Docker Compose:

1. **Frontend**: Next.js 16 (React 19 + TypeScript + CSS Modules), providing a premium, dark-mode visual interface with drag-and-drop file upload, file state tracking, and interactive chat.
2. **Backend**: FastAPI (Python 3.11), exposing secure, structured REST APIs.
3. **Database**: PostgreSQL with `pgvector` extension for structured data persistence and semantic vector search storage.
4. **Asynchronous Worker**: Celery + Redis, managing background log parsing, semantic chunking, and AI processing without blocking API threads.
5. **Caching / Message Broker**: Redis server.

---

## 🚀 Features 

Today's implementations completed the core **User Authentication, Data Isolation, and Account Management** features:

### 1. User Authentication System
* **Conventional Accounts**: Custom user registration and login workflows with secure password hashing.
* **OTP Verification**: Email verification using One-Time Passwords (OTP) during registration and password reset flows.
* **Google OAuth Integration**: Native Google Sign-In button on the frontend, verifying Google ID tokens securely on the backend, and automatically creating a registered account.
* **Bcrypt Hashing**: Upgraded backend security using direct `bcrypt` hashing, bypassing outdated wrapper bugs for robust local and containerized performance.
* **Password Visibility Toggle**: Added an interactive eye-toggle button (`type="password"` / `type="text"`) with smooth SVG icons inside the frontend login, registration, and reset password input fields.

### 2. User Data Isolation & Persistence
* Database tables (`users`, `user_otps`, `documents`, `summaries`, `chat_messages`) configured in SQLAlchemy.
* Log histories, uploaded document records, AI summaries, and Q&A chat messages are saved in PostgreSQL and isolated specifically to each logged-in user.

### 3. Tiered Usage Limits
* **Guest Mode**: Restricts unauthenticated visitors to a maximum of 3 document uploads and locks conversational Q&A.
* **Registered Mode**: Authenticated users unlock unlimited document uploads, persistent history, and full interactive Q&A.

---

## 🛠️ Getting Started

### 1. Configure Environment Variables
We use environment variable files (`.env`) to configure credentials and services securely. The repository includes safe template files (`.env.example`) to guide configuration.

* **Project Root**: Copy `.env.example` to `.env` and fill in your keys (used by Docker Compose).
* **Backend**: Copy `backend/.env.example` to `backend/.env` for running the backend locally.
* **Frontend**: Copy `frontend/.env.example` to `frontend/.env` for running the frontend locally.

### 2. Run the Entire Project (Docker Compose)
To start all dependency services, backend APIs, Celery workers, and the frontend at once, run:
```bash
docker compose up --build
```

Access the services:
* **Frontend UI**: [http://localhost:3000](http://localhost:3000)
* **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Local Development (Alternative)
To run the components individually for local debugging, start the database and Redis using Docker (`docker compose up -d db redis`), then:

* **Backend**:
  ```bash
  cd backend
  # Activate virtual environment (.venv\Scripts\Activate on Windows)
  pip install -r requirements.txt
  uvicorn app.main:app --reload
  ```
* **Celery Worker**:
  ```bash
  cd backend
  celery -A app.tasks.celery_app.celery worker --loglevel=info -P solo
  ```
* **Frontend**:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

---

## 🧪 Running Tests

LogStream AI includes comprehensive automated test suites for both the backend (unit, integration, and Celery task logic) and frontend (E2E browser tests).

### 1. Backend Tests (Pytest)
The backend tests run against a dynamic, in-memory SQLite database, isolating tests from your production/development PostgreSQL database. External APIs (Gemini, OpenAI, SMTP) are fully mocked to allow fast, deterministic execution.

**How to run:**
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate your virtual environment:
   * **Windows:** `.venv\Scripts\activate`
   * **macOS/Linux:** `source .venv/bin/activate`
3. Run the pytest suite:
   ```bash
   python -m pytest -v
   ```

### 2. Frontend E2E Tests (Playwright)
Frontend tests are built using Playwright to verify the UI layout, authentication forms, usage limits banners, and page components.

**How to run:**
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Playwright browser engines (if running for the first time):
   ```bash
   npx playwright install
   ```
3. Run the Playwright test suite:
   ```bash
   npx playwright test
   ```
4. View HTML report of test results (optional):
   ```bash
   npx playwright show-report
   ```

