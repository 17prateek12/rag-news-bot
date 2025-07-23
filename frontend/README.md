# 🧠 News Chatbot Frontend

A sleek and modern frontend for a news-based chatbot using **React + Vite + TypeScript**, styled with **Tailwind CSS** and **ShadCN/UI**. This interface enables users to start and manage chat sessions with a backend RAG-based AI system that provides responses grounded in recent news.

---

## ✨ Tech Stack

- ⚛️ React + Vite
- 🔷 TypeScript
- 🎨 Tailwind CSS
- 💎 ShadCN/UI
- 📡 WebSocket & REST API integration
- 💾 LocalStorage-based session persistence

---

## 📦 Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/news-chatbot-frontend.git
cd news-chatbot-frontend
```

### 2. Install dependencies
```
npm install
```

### 3.  Configure environment variables
Create a .env file in the root directory:
```.env
VITE_REACT_APP_HTTP_SERVER=http://localhost:8000
VITE_REACT_APP_SOCKET_SERVER=ws://localhost:8000/ws
```

### 4. Running the App
```
npm run dev
```

## 🧠 Features
### 🏠 Home Page
-**Start a new session (POST /session)**

-**View and resume recent sessions from localStorage**

-**Sessions expire after 24 hours**

### 💬 Chat Page
-**Real-time bi-directional communication via WebSocket (/ws/:session_id)**

-**Fallback to REST API if WebSocket is disconnected (POST /chat)**

-**Auto-fetches chat history on reconnect (GET /history/:session_id)**

-**Reset session (DELETE /session/:session_id)**


