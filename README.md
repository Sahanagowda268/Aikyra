# 🚀 AI-Powered Intelligent Task Management & Productivity Platform

Aikyra is an AI-powered intelligent automation platform developed using **Python** and **Flask**. It combines multiple productivity tools into a single web application, enabling users to manage tasks, interact with an AI chatbot, process documents, automate emails, perform OCR, execute code, and organize schedules efficiently.

The platform is designed to improve productivity by integrating AI-driven features with day-to-day workflow management in a secure and user-friendly interface.

---

# 📌 Features

### 🤖 AI Chatbot
- AI-powered conversational assistant
- Context-aware responses
- Voice input support
- OCR-based question answering from uploaded documents
- Text translation

### 📄 Smart Document Processing
- Upload PDF, DOCX, TXT, and Images
- OCR using Tesseract
- Extract text from documents
- AI-based document understanding
- Text-to-Speech conversion

### 📧 Email Automation
- Compose and send emails
- AI-generated professional email content
- Email validation
- Email history tracking
- SMTP integration

### 📅 Smart Calendar
- Create and manage events
- Event reminders
- Email notifications
- Event scheduling

### ✅ Task Management
- Create tasks
- Set priorities
- Due dates and reminders
- Task status tracking
- Email reminders

### 💻 AI Code Assistant
- Generate source code
- Execute code
- Store execution history
- Download generated code
- Support for multiple programming languages

### 👤 User Management
- Secure Registration
- Login Authentication
- Password Hashing
- User Profile Management
- Profile Picture Upload
- Dark Mode Support

### 🔊 Speech Features
- Speech-to-Text
- Text-to-Speech
- Voice interaction with chatbot

### 🗂 File Management
- Upload multiple document formats
- Image OCR
- Secure file storage
- Content hashing

---

# 🛠 Tech Stack

## Backend
- Python
- Flask

## AI & NLP
- Google Gemini API
- gTTS
- SpeechRecognition

## Database
- SQLite

## Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap

## Libraries
- PyPDF2
- python-docx
- pytesseract
- Pillow
- pygame
- mutagen
- requests
- email-validator
- Werkzeug
- python-dotenv

---

# 📂 Project Structure

```
Aikyra/
│
├── app.py
├── requirements.txt
├── instance/
│   └── app.db
├── static/
│   ├── css/
│   ├── js/
│   ├── uploads/
│   └── images/
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── chatbot.html
│   ├── calendar.html
│   ├── tasks.html
│   ├── documents.html
│   ├── email.html
│   └── profile.html
└── README.md
```

---

# ⚙ Installation

Clone the repository

```bash
git clone https://github.com/yourusername/Aikyra.git
```

Navigate into the project

```bash
cd Aikyra
```

Create Virtual Environment

```bash
python -m venv venv
```

Activate Environment

Windows

```bash
venv\Scripts\activate
```

Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a `.env` file in the project root.

```env
SECRET_KEY=YOUR_SECRET_KEY

GEMINI_API_KEY=YOUR_GEMINI_API_KEY

EMAIL_ADDRESS=YOUR_EMAIL

EMAIL_PASSWORD=YOUR_EMAIL_APP_PASSWORD
```

---

# ▶ Running the Project

```bash
python app.py
```

Open your browser

```
http://127.0.0.1:5000
```

---

# 📌 Functional Modules

- User Authentication
- Dashboard
- AI Chatbot
- Smart Email Generator
- Email Automation
- Calendar Management
- Task Management
- AI Code Generator
- Code Executor
- OCR Document Reader
- Document Analyzer
- Text-to-Speech
- Speech-to-Text
- User Profile
- Theme Management

---

# 🔒 Security Features

- Password Hashing
- Secure Session Management
- Environment Variables for Secrets
- Email Validation
- Secure File Upload
- SHA-256 Hashing
- Input Validation

---

# 📷 Supported File Types

- PDF
- DOC
- DOCX
- TXT
- PNG
- JPG
- JPEG
- GIF

---

# 📈 Future Enhancements

- OpenAI / Multi-LLM Support
- Google Calendar Integration
- WhatsApp Automation
- Voice Assistant
- Real-Time Notifications
- Cloud Database
- Docker Deployment
- Multi-user Collaboration
- AI Workflow Automation
- Mobile Application

---

# 🎯 Learning Outcomes

This project demonstrates practical implementation of:

- Full Stack Web Development
- Artificial Intelligence Integration
- Flask Framework
- RESTful Application Development
- OCR
- Natural Language Processing
- Authentication
- Database Management
- Email Automation
- Secure Software Development

---

# 👩‍💻 Author

**Sahana K**

Aspiring Software Developer passionate about AI, Full Stack Development, and Intelligent Automation.

GitHub: https://github.com/Sahanagowda268

LinkedIn: https://www.linkedin.com/

---

# ⭐ If you found this project useful, consider giving it a star.
