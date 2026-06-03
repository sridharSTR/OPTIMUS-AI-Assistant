---
marp: true
title: OPTIMUS Project Workflow
description: Full-stack AI chatbot architecture and workflow presentation
theme: default
paginate: true
---

# OPTIMUS Full-Stack AI Chat

## Project Workflow Presentation

Created by Sridhar M

OPTIMUS is a secure AI assistant built with React, Django REST Framework, PostgreSQL, OTP email verification, JWT cookie authentication, NLP, RAG documents, resume analysis, Tavily search, and OpenRouter/Gemini AI providers.

---

# Key Capabilities

- Secure registration and login with email OTP.
- Registration OTP verifies the account but does not log the user in.
- Login OTP is the only step that creates JWT cookies.
- Persistent conversations, user memories, NLP analytics, and response cache.
- Live web search through Tavily for current/latest queries.
- Resume analysis and document RAG chat.
- Admin dashboard with role-based access control.

---

# Technology Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, Vite, Axios, CSS |
| Backend | Django, Django REST Framework |
| Database | PostgreSQL through Django ORM |
| Auth | Email OTP, SimpleJWT, httpOnly cookies |
| NLP | SpaCy, TextBlob, regex fallback |
| AI | OpenRouter, Google Gemini |
| Search | Tavily |
| Documents | PDF, DOCX, TXT extraction and chunking |

---

# Local Development Flow

```mermaid
flowchart LR
    Dev[Developer] --> Backend[Django backend]
    Dev --> Frontend[Vite React frontend]
    Frontend -->|/api proxy| Backend
    Backend --> DB[(PostgreSQL)]
    Backend --> SMTP[Gmail SMTP]
    Backend --> AI[OpenRouter or Gemini]
    Backend --> Search[Tavily]
```

Backend runs at `http://127.0.0.1:8000`.

Frontend runs at `http://localhost:5174` or `https://localhost:5174`.

---

# Required Auth Flow

```mermaid
flowchart TD
    A[Register] --> B[Registration OTP Verify]
    B --> C[Account verified]
    C --> D[Redirect to Login]
    D --> E[Login with email and password]
    E --> F[Login OTP Verify]
    F --> G[JWT cookies created]
    G --> H[Dashboard /chat]
```

Registration verification never creates a login session.

JWT tokens are issued only after successful login OTP verification.

---

# Registration Flow

```mermaid
sequenceDiagram
    participant User
    participant React
    participant Django
    participant DB as PostgreSQL
    participant SMTP as Email SMTP

    User->>React: Fill registration form
    React->>Django: POST /api/users/register/
    Django->>DB: Create user email_verified=false, is_active=false
    Django->>DB: Save hashed register OTP
    Django->>SMTP: Send registration OTP to user.email
    Django-->>React: requires_otp=true
    User->>React: Enter OTP
    React->>Django: POST /api/users/verify-otp/
    Django->>DB: Set email_verified=true and is_active=true
    Django-->>React: Registration successful, no JWT tokens
    React-->>User: Show success toast
    React->>React: Redirect to Login page
```

---

# Login Flow

```mermaid
sequenceDiagram
    participant User
    participant React
    participant Django
    participant DB as PostgreSQL
    participant SMTP as Email SMTP

    User->>React: Enter email and password
    React->>Django: POST /api/users/login/
    Django->>DB: Validate user and password
    Django->>DB: Save hashed login OTP
    Django->>SMTP: Send login OTP to user.email
    Django-->>React: requires_otp=true
    User->>React: Enter OTP
    React->>Django: POST /api/users/verify-otp/
    Django->>DB: Verify login OTP
    Django-->>React: Set JWT cookies and return user data
    React->>React: Redirect to /chat
```

---

# Admin Registration Flow

```mermaid
flowchart TD
    A[Admin Register] --> B[Create normal pending user]
    B --> C[Create AdminRegistrationRequest]
    C --> D[Send registration OTP]
    D --> E[Verify OTP]
    E --> F[Account active and email verified]
    F --> G[Redirect to admin login]
    G --> H{Admin approved?}
    H -->|No| I[Admin login blocked]
    H -->|Yes| J[Admin login OTP]
    J --> K[Admin dashboard]
```

Admin registration does not grant admin access automatically.

An existing admin or super admin must approve the request.

---

# Chat Request Lifecycle

```mermaid
flowchart TD
    A[User sends message] --> B[Django ChatView]
    B --> C[Authenticate JWT cookie]
    C --> D[Check email_verified]
    D --> E[Run NLP intent and sentiment]
    E --> F{Local handler?}
    F -->|Yes| G[FAQ, memory, profile, greeting]
    F -->|No| H{Cached response?}
    H -->|Yes| I[Return cached response]
    H -->|No| J{Needs live data?}
    J -->|Yes| K[Tavily search]
    J -->|No| L[Build AI prompt]
    K --> L
    L --> M[OpenRouter or Gemini]
    M --> N[Save response]
    G --> N
    I --> N
    N --> O[React renders Markdown]
```

---

# Memory and NLP Flow

- User messages are analyzed for intent, sentiment, and entities.
- Memory commands can save, update, delete, and retrieve user memories.
- Memory changes are written to PostgreSQL immediately.
- The frontend receives `memory_sync` so the Memory page stays current.
- Relevant memories are injected into the AI prompt for personalization.

---

# Document RAG Flow

```mermaid
flowchart LR
    A[Upload PDF, DOCX, or TXT] --> B[Store file bytes in PostgreSQL]
    B --> C[Extract text]
    C --> D[Create document chunks]
    D --> E[Ask document question]
    E --> F[Retrieve relevant chunks]
    F --> G[Build grounded prompt]
    G --> H[AI answer with sources]
```

Uploaded document content is stored in the database and used for document chat.

---

# Resume Analysis Flow

```mermaid
flowchart LR
    A[Upload resume PDF] --> B[Extract text]
    B --> C[OCR fallback if needed]
    C --> D[Detect skills and sections]
    D --> E[Score resume]
    E --> F[Generate suggestions]
    F --> G[Generate interview questions]
    G --> H[Store analysis in PostgreSQL]
```

---

# Run OPTIMUS Locally

Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

---

# Verification Checklist

Backend:

```bash
cd backend
python manage.py check
python manage.py test users
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

---

# Final Workflow Summary

Register

OTP Verify

Registration Successful

Redirect to Login

Login

OTP Verify

Dashboard `/chat`
