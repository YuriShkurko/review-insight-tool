# Review Insight Tool -- Frontend

Next.js frontend for the Review Insight Tool micro-SaaS.

## Quick Start

### Prerequisites

- Node.js 18+
- Backend running at http://localhost:8000

### Setup

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

### Pages

| Route | Description |
|-------|-------------|
| `/` | Redirects to `/login` or `/businesses` |
| `/register` | Create a new account |
| `/login` | Sign in |
| `/businesses` | List your businesses, add new ones |
| `/businesses/[id]` | Dashboard with reviews, analysis, and insights |

### Project Structure

```
src/
├── app/            # Next.js App Router pages
├── components/     # Reusable UI components
└── lib/            # API client, auth context, types
```
