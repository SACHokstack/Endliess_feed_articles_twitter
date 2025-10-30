# 🧾 SpineNews Frontend Revamp — Product Requirements Document (PRD)

**Version:** 1.0  
**Author:** Sachiv Chandramohan  
**Date:** October 2025  

---

## 1. 🎯 Project Overview

### Goal
Build a modern, responsive, and professional **frontend web app** for **SpineNews**, a spinal tech news aggregator.  
The frontend will consume data from the existing backend (MongoDB + REST API), display categorized news, and deliver a polished UX similar to top news dashboards.

### Tech Stack (Frontend)
- **Next.js 14** (App Router + TypeScript)
- **React 18**
- **TailwindCSS**
- **shadcn/ui** (for components)
- **lucide-react** (for icons)
- **framer-motion** (for subtle animations)
- **Axios** or **fetch API** (for backend integration)
- **Deployment:** Vercel (preferred)

### Backend (Existing)
- REST API (Express / Flask / FastAPI)
- MongoDB (connected and tested)

---

## 2. 📦 Core Features

| Feature | Description | Priority |
|----------|--------------|----------|
| 📰 **News Feed** | Fetch and display latest spinal tech articles from backend | ⭐⭐⭐⭐ |
| 📊 **Category Tabs** | Filter articles by `All`, `Industry`, `Research`, `Reports`, `Insights` | ⭐⭐⭐⭐ |
| 🔍 **Search & Filter** | Search bar for titles and tags | ⭐⭐⭐ |
| 🧩 **Article Card** | Title, category, source, date, and snippet | ⭐⭐⭐⭐ |
| 🧭 **Sidebar Widgets** | Top Articles, Trending Topics, About SpineNews | ⭐⭐⭐ |
| 📅 **Last Updated Indicator** | Show last data fetch time | ⭐⭐⭐ |
| 🌙 **Dark Mode Support** | Optional, via Tailwind dark mode toggle | ⭐⭐ |
| 📱 **Responsive Design** | Mobile to desktop layout | ⭐⭐⭐⭐ |

---

## 3. 🧠 Data Flow

### Flow
**Frontend → Backend → MongoDB**

1. **Frontend** calls:
GET http://127.0.0.1:5000/api/news

2. **Backend** retrieves documents from MongoDB and returns:
```json
{
  "_id": "672f2a7d31f1c2",
  "title": "Steamboat Orthopaedic named exclusive care provider...",
  "category": "Healthcare Insights",
  "source": "Becker’s Spine Review",
  "date": "2025-10-28",
  "author": "Cameron Cortigiano",
  "snippet": "Orthopaedic Steamboat Orthopaedic named exclusive care provider...",
  "tags": ["Industry", "Spine", "Research"],
  "url": "https://example.com/article"
}
Frontend Components

ArticleCard.tsx → displays article info

Sidebar.tsx → lists Top Articles, Trending Topics

Hero.tsx → shows “Last updated” timestamp

(Optional) React Query / SWR for caching & auto revalidation.

4. 🧩 Frontend Architecture

spinenews-frontend/
│
├── app/
│   ├── layout.tsx
│   ├── globals.css
│   ├── feed/
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   ├── error.tsx
│
├── components/
│   ├── Header.tsx
│   ├── Hero.tsx
│   ├── ArticleCard.tsx
│   ├── Sidebar.tsx
│   ├── Footer.tsx
│
├── lib/
│   ├── api.ts  # Axios instance + API helpers
│
├── types/
│   ├── Article.ts
│
└── data/
    ├── mockArticles.ts  # Temporary mock data
