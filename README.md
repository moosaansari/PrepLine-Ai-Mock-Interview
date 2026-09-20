# PREPLINE - AI Mock Interview Platform

PREPLINE is an AI-powered mock interview platform that helps students and job seekers practice realistic technical interviews through an interactive voice-based interview experience.

The platform uses AI to conduct interviews, evaluate candidate responses, analyze communication, and generate a detailed performance report.

## Features

### AI-Powered Mock Interviews

- Real-time AI voice interviewer
- Role-specific interview questions
- Adaptive interview conversations
- Configurable interview difficulty
- Custom number of interview questions
- Interactive interview experience

### Supported Interview Roles

- Software Engineer
- Frontend Developer
- Backend Developer
- Full Stack Developer
- Data Scientist
- Machine Learning Engineer
- Data Analyst
- DevOps Engineer
- QA Engineer
- Mobile Developer
- Cybersecurity Engineer

### Difficulty Levels

- Easy
- Intermediate
- Hard

### AI Answer Evaluation

PREPLINE evaluates candidate answers based on multiple factors:

- Technical correctness
- Relevance
- Completeness
- Reasoning
- Structure
- Examples
- Clarity
- Confidence
- Directness
- Professionalism
- Assertiveness
- Hesitation
- Verbosity
- Filler words

### Communication-Aware Feedback

PREPLINE separates the quality of an answer from the way the answer is delivered.

The system analyzes how communication style may be interpreted by an interviewer and provides contextual feedback to help candidates understand different communication expectations.

### Interview Reports

After completing an interview, PREPLINE generates a detailed report containing:

- Overall performance
- Technical performance
- Communication analysis
- Strengths
- Areas for improvement
- Question-wise evaluation
- AI-generated feedback
- Recommended improvement areas

### Interview History

Users can view their previous interviews and review their performance over time.

---

# Technology Stack

## Frontend

- HTML5
- CSS3
- JavaScript
- Web Audio API
- WebSocket

## Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

## AI

- Google Gemini
- Gemini Live API
- AI-based answer evaluation
- Speech-to-Text

## Database

- Firebase
- Cloud Firestore

## Other Technologies

- REST APIs
- WebSockets
- FFmpeg
- Git
- GitHub

---

# System Architecture

```text
                     PREPLINE
                         |
                         v
              +---------------------+
              |      Frontend       |
              |   HTML / CSS / JS   |
              +----------+----------+
                         |
                  REST / WebSocket
                         |
                         v
              +---------------------+
              |   FastAPI Backend   |
              +----------+----------+
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
   Gemini Live      AI Evaluation    Firestore
   Voice Engine        Service        Database
          |              |              |
          +--------------+--------------+
                         |
                         v
              +---------------------+
              |  Interview Report   |
              +---------------------+
