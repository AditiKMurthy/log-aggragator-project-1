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

## 🚀 Features Completed Today

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
Create a `.env` file in the root directory (based on `.env.example` if available) and add your keys:

```env
# Database Credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=doc_summarizer

# AI Provider API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id

# SMTP Email Configuration (Optional, falls back to logging OTP to console if empty)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
```

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
  celery -A app.tasks.celery_app.celery worker --loglevel=info
  ```
* **Frontend**:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
