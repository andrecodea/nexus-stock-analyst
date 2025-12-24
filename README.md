# Nexus Financial Agent

Quick start and developer notes (English).

Prerequisites
- Node.js (for frontend)
- Python 3.10+ (for backend)

Setup
1. Backend
   - Create a virtual environment and install dependencies:
     ```bash
     cd backend
     python -m venv .venv
     .venv\Scripts\activate      # Windows
     pip install -r requirements.txt || pip install .
     ```
   - Copy the example env and fill secrets locally:
     ```bash
     cp ../.env.example .env
     # then edit backend/.env with real keys (DO NOT commit)
     ```

2. Frontend
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Security & Git history
- Sensitive keys were previously present in `backend/.env`. The repository history was rewritten to remove them — you MUST rotate any keys that were exposed.
- After the history rewrite, collaborators should re-clone the repository to avoid conflicts:
  ```bash
  git clone https://github.com/andrecodea/nexus-financial-analyst.git
  ```

Notes
- Do NOT commit `.env` or any secret files. Use `.env.example` as a template.
- If you want help scanning for other secrets or automating key rotation, ask and I can run a deeper scan.
