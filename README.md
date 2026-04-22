# ShopSight Prototype

[Architecture](strawmanarch.png)

<img width="993" height="501" alt="image" src="https://github.com/user-attachments/assets/2872a924-4313-4e19-8e5e-ab50c2c9827c" />

## 1) What I chose to build and why

I built a prototype that allows users to process natural language into a susbet of actions like obtaining historical revenue, revenue in the last N days, count of products paired with relevant insights and graphs. The prototype primarily leverages React.js, FastAPI, an Openai LLM and SQLite.

I choise this because it offers the most value for a short amount of time, presenting the user with a natural experience that one would expect when interacting with LLMs and their data.
With my **constrained action catalog** I am able to simplify the actions since the system only executes known analytics flows instead of generating arbitrary queries (known analytics include historical revenue, historical product counts, and revenue within last n days where 2020-09-12 is the present).

## 2) How I scoped the problem to fit ~1 hour

To keep scope small, I limited the prototype to:

- **One chat page** (plus a simple intro page).
- **A single API endpoint**: `POST /chat` returning a structured payload the frontend can render.
- **A small action set** (a few supported `action_type`s) rather than trying to cover every analytics question.
- **One dataset contract** for the first implementation (a “transactions” style schema), and only the analytics that can be derived from that schema.
- On the backend, I implemented a **single orchestrator** that:
  - selects an action from the action catalog
  - runs the corresponding analytics query
  - returns a UI-ready response payload
  The orchestrator is the "agentic layer" in the demo.

By using cursor's planning I was able to complete 70-80% of the project in the first few minutes. Using an agent allows to complete the task much more rapidly.

## 3) Assumptions I made

Data/schema assumptions for the first runnable version:

- The dataset can be loaded into SQLite from:
  - `Shop/backend/infrastructure/data/transactions_sampled_articles.csv`
- I explored the data source provided and simplified the transactions on a smalle subset of the data, the schema I am using is bellow:
  - `t_dat` (date)
  - `price`
  - `prod_name` (product name)
  - (and an article identifier such as `article_id`)
- Some richer dimensions (like product categories) may not exist in this simplified dataset.
- I did not present images of products because it is a nice to have given the 1 hour time constraint, I wanted to focus on presenting a natural flow of user query to visualizing results and insights.
LLM assumptions:
- If `OPENAI_API_KEY` and `OPENAI_MODEL` are present, in the backend folder (.env) we can use OpenAI for classification/insight generation (depending on the action path).
- If those env vars are missing, the backend still works using deterministic selection and demo/fallback outputs.

## 4) How to run it locally

### Backend (FastAPI)

1. Open a terminal in:
  - `Shop/backend`
2. Create a venv and activate it (python version 3.12.2)
3. Install dependencies:
  - `pip install -r requirements.txt`
4. Ensure a `.env` exists:
  - `Shop/backend/.env`
  - (This repo includes an `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`.)
5. Start the server:
  - `uvicorn app:app --host 127.0.0.1 --port 8000`

The first time a query runs, if SQLite hasn’t been bootstrapped yet, the backend attempts to import the CSV into:

- `Shop/backend/shopsight.db`

### Frontend (React)

1. Open a terminal in:
  - `Shop/frontend`
2. Install dependencies:
  - `npm install`
3. Start the dev server:
  - `npm run dev`
4. Open the app in your browser and click Get started.

The frontend calls:

- `http://localhost:8000/chat`

## 5) What is real vs. mocked

Real (when the dataset is present / SQLite import succeeds):

- **Analytics execution**: action queries are run against **SQLite**. The data is small subset of 960 transactions (transactions in hm_with_images/images/010 and 011), the values were scaled by 1000 to make them larger as observed in the notebook (hence the larger results).
- **Visual payloads**: chart/table/KPI values returned from the backend are rendered by the frontend using data from the queries.
**LLM-driven insight/followups**: some paths can generate the `insight` and `followups` using OpenAI (if configured).

Mocked / fallback behavior (keeps the demo usable even before data is ready):

- If SQLite import fails (missing CSV, missing expected columns, etc.), the backend returns **deterministic demo outputs** with realistic chart/table shapes so the UI still works.
- Not all natural language prompts work, only those primarily for historical revenue, revenue in N days and historical item count are valid options for the LLM to leverage.
- Days are parsed out of the user prompt to return the revenue aggregation within N days.

## 6) What I would build next with more time

If I had more time, I would:

- Explore how KumoRFM can be used in this problem by obtaining the expected PQL. This would take the demo to the next level by performing predictive tasks such as churn, revenue forecasting, more sophisticated queries...
- I would research ways to build trust with the users, such as having agents double check that the queries actually performed the expected workflow (add a green check as a visual).
- Present images of relevant products in given queries.
- I would allow the agent to plan how to answer the query of the user, which would include formulating the PQL to use, what type of plots to construct, what insights to get and potential follow up options/metadata for the user.
- Replace deterministic selection with a more reliable agent flow:
  - explicit “new query vs follow-up” handling using conversation state.
- Remove actions and attempt to dynamically generate queries no matter the natural language input by the user.
- Add backend streaming so the UI can show partial progress (loading states, intermediate parsing).
- Cache queries by the user.
- Containerize all the components in this applications for seamless deployment using a cloud provider or kubernetes.
- Add lightweight unit tests around:
  - action selection correctness
  - timeframe parsing and SQL query parameterization
- Improve the agents ability to extract all relevant information as well as determining different plots to use.

