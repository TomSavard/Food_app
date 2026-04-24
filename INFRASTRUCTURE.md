# Infrastructure — Food_app

> Working doc to scope the tech stack before migrating off Neon + Render.
> Success criteria (from NORTH_STAR.md): smooth UX, low operational overhead, sustained use for ≥1 month.

---

## ✅ Final decision

| Layer | Choice | Why |
|---|---|---|
| **Frontend + server** | **Vercel** (Next.js) | Zero frontend cold start, best-in-class DX, generous free tier. Directly solves the Render cold-start pain. |
| **Database** | **Neon** (Postgres, keep current) | Already set up, real Postgres (SQL → clean nutrition aggregation), permanent free tier, no migration cost. |
| **LLM model** | **Gemini 2.5 Flash** | Fast, cheap, supports tool-calling. |
| **LLM API access** | **Gemini API key via Google AI Studio** (free/unpaid tier — 250 requests/day) | No billing account needed, direct REST API, enough headroom for personal daily use. |

**Stack shape:**

```
[ Browser / Phone ]
        │
        ▼
   ┌─────────┐        ┌──────────────┐
   │ Vercel  │ ─────► │   Gemini     │
   │ Next.js │        │  (AI Studio) │
   └────┬────┘        └──────────────┘
        │
        ▼
   ┌─────────┐
   │  Neon   │  (Postgres)
   └─────────┘
```

### Rationale

- **Kept Neon** over Supabase: avoids a DB migration for marginal gain. Neon is real Postgres with a permanent free tier; the only thing Supabase adds (auto-generated APIs, auth) we don't strictly need and can add later if pain emerges.
- **Moved off Render → Vercel**: Render's free-tier cold starts directly conflict with the success metric (smooth, enjoyable, sustained daily use). Vercel eliminates that on the frontend.
- **Three providers, not unified:** accepted tradeoff. "Unified Google" was aesthetic, not functional. Each provider here is best-in-class at its job, all on permanent free tiers.

### Known tradeoffs to monitor

- Neon's free tier **auto-suspends** when idle → first request after a long pause has a small warm-up (~1–3s). If this becomes noticeable, options: (a) ping endpoint to keep warm, (b) upgrade Neon, (c) revisit Supabase.
- Vercel serverless API routes have their own small cold starts (much smaller than Render). Acceptable for now.
- Three separate accounts/billing to monitor — not a real burden at free-tier scale.

### Next steps

1. Migrate deployment from Render → Vercel (frontend + API routes).
2. Point the Vercel app at existing Neon DB (connection string only — no data migration needed).
3. Retire Render.
4. Wire Gemini API key into Vercel env vars.
5. Resume product work per [NORTH_STAR.md §6](NORTH_STAR.md).

---

---

## 1. The three pieces

A web app like this has three independent choices. They connect but can be decided separately:

```
   [ Browser / Phone ]
           │
           ▼
   ┌───────────────┐       ┌──────────────┐
   │   Frontend    │ ────► │     LLM      │  (Gemini 2.5 Flash via AI Studio)
   │  + Server     │       └──────────────┘
   │   (Hosting)   │
   └───────┬───────┘
           │
           ▼
   ┌───────────────┐
   │   Database    │
   └───────────────┘
```

- **Frontend + server (hosting):** the code that runs the UI and handles requests.
- **Database:** where recipes, meal plans, nutrition logs live.
- **LLM:** the assistant brain. Already decided: Gemini 2.5 Flash.

---

## 2. Database

### Goal
Store recipes, ingredients, meal plans, shopping lists, nutrition logs, and the CIQUAL reference table. Support CRUD from the app, and aggregation queries ("how many kcal this week?").

### SQL vs. NoSQL — the actual difference

**SQL (relational, e.g. Postgres):**
- Data lives in **tables with fixed columns**. A `recipes` table has `id, name, servings, ...`. An `ingredients` table links rows together via IDs (**foreign keys**).
- You can **JOIN** tables in one query: "give me every ingredient of every recipe in this week's meal plan, summed by CIQUAL entry, grouped by day." One SQL query. The DB engine does the math.
- Schema is **rigid** — you declare columns up front and migrate to change them.
- Great when data is **highly relational** and you need aggregation.

**NoSQL (document, e.g. Firestore):**
- Data lives as **documents** (JSON-like). A recipe document can contain its ingredients nested inside. No fixed schema.
- **No JOINs.** To get "recipe + all ingredients with CIQUAL data," you fetch the recipe, then fetch each ingredient, then fetch each CIQUAL entry. You assemble it in application code.
- Schema is **flexible** — add a field whenever, no migration.
- Great when data is **document-shaped** (self-contained), reads are by-key, and you want real-time sync to clients.

### What our data actually looks like

- A meal plan references recipes.
- Each recipe has a list of ingredients.
- Each ingredient maps to a CIQUAL entry with nutrition values.
- To compute "kcal for this week," we must traverse: meal_plan → recipes → ingredients → ciqual → sum.

**This is a relational pattern.** SQL does it in one query. NoSQL does it in N+1 reads that you stitch together in code. Workable, but more code and more reads (Firestore bills per read).

### Candidates

#### SQL (Postgres / MySQL / MSSQL)

| Option | What it is | Free tier | Pros | Cons |
|---|---|---|---|---|
| **Neon (current)** | Serverless Postgres. Scales storage/compute independently, branches like git | Generous & permanent (0.5GB, project auto-suspends when idle) | Real Postgres, fast, modern DX, DB branching for testing, already set up | Idle suspend = cold start (~1–3s) on first request after pause; not tied to a big cloud |
| **Supabase** | Managed Postgres + auto-generated REST/GraphQL API + auth + realtime + file storage. "Firebase but on Postgres." | Permanent free tier (500MB DB, 50k monthly active users, auth included) | Real Postgres + SQL, but you also get auth, realtime subscriptions, storage out of the box. Huge DX win — can skip writing an API layer for simple CRUD | Free project pauses after 7 days of inactivity (cold start to resume); not a big cloud |
| **Azure SQL (free offer)** | Microsoft SQL Server, managed | 100k vCore-seconds/mo + 32GB — lasts 12 months, then auto-pauses to stay free | Big cloud, enterprise-grade, plenty of capacity | **MSSQL, not Postgres** — different SQL dialect, smaller ecosystem in the Node/Next.js world. Account setup heavier (credit card, subscription). Tied to Azure |
| **AWS RDS free tier** | Managed Postgres/MySQL/MariaDB on AWS | **12 months only**, then you pay (~$15+/mo) | Big cloud, mature | **Not permanent free.** After 12 months you're on the hook or you migrate. Also requires VPC/security-group setup — more ops friction |
| **Cloud SQL (GCP)** | GCP-managed Postgres | No true free tier (~$10/mo minimum for smallest instance) | Mature, GCP-unified | Costs money from day 1 |
| **SQLite on server** | File-based SQL | Free | Zero ops, real SQL | Doesn't work on serverless (no persistent filesystem). Only viable on a long-running VM |

#### NoSQL

| Option | What it is | Free tier | Pros | Cons |
|---|---|---|---|---|
| **Firestore (Firebase)** | GCP NoSQL document store. "Firebase" is the umbrella product; Firestore is its DB. Pairs with Firebase Auth, Hosting, Functions | Permanent generous free tier (1GB, 50k reads/day, 20k writes/day) | Realtime sync to clients, GCP-unified, easy mobile later, zero ops | No JOINs → nutrition aggregation = N+1 reads in app code. Per-read billing. Schema drift over time. NoSQL tax for our specific data shape |
| **DynamoDB (AWS)** | AWS NoSQL | 25GB permanent | Big cloud, serverless | Same NoSQL tax as Firestore, worse DX |
| **BigQuery** | GCP analytics warehouse | — | — | ❌ Wrong tool. Expensive per query, seconds of latency, not for app CRUD |

### Neon vs. Supabase — the direct comparison you asked about

Both are serverless Postgres with permanent free tiers. Real differences:

- **Neon** is a pure database. You write your own API layer (Next.js API routes calling Neon via a Postgres driver).
- **Supabase** is database + batteries. You get auto-generated APIs, auth, realtime, storage — you can skip a lot of backend code for simple CRUD.
- **Neon's** killer feature is DB branching (a fresh DB copy per git branch) — nice for dev, not critical for a solo project.
- **Supabase's** killer feature is that for a personal app, you can go very far without writing a traditional backend.

For a solo, enjoyable build: **Supabase is likely better** — less glue code, more features for free. Neon is not worse; it's just more DIY.

### What "Firebase" actually means

Firebase is Google's app-building suite. It bundles:
- **Firebase Hosting** (CDN for your frontend)
- **Firestore** (NoSQL DB, see above)
- **Firebase Auth** (user login)
- **Cloud Functions** (serverless backend)
- **Realtime Database** (older, avoid in favor of Firestore)

It's the GCP equivalent of Supabase in *spirit*, but built on NoSQL. Great free tier, realtime sync, mobile-friendly. Same NoSQL tax for our nutrition joins.

### Bottom line for our case

- **Azure SQL free** — technically usable but MSSQL is an ecosystem detour we don't need. Skip.
- **AWS RDS free** — 12-month limit disqualifies it for a "use for years" personal tool. Skip.
- **Firestore / Firebase** — great tech, wrong shape for our relational nutrition data.
- **Cloud SQL** — costs money. Skip unless "learn GCP" is a goal.
- **Neon** — works today, just switch hosting off Render.
- **Supabase** — likely the best fit: Postgres + free auth + less backend code to write.

### My read

For our data shape + nutrition aggregation + long-term maintainability, **SQL wins**. The real choice is *which* Postgres.

---

## 3. Hosting (frontend + server)

### Goal
Serve a responsive web app (phone + desktop) from a URL. Run server-side code for the Gemini API calls and DB queries. No cold starts that make the app feel dead.

### Candidates

| Option | What it is | Pros | Cons |
|---|---|---|---|
| **Render (current)** | PaaS, deploys containers | Works today, simple | Cold starts on free tier (painful), not GCP |
| **Vercel** | Frontend-optimized platform for Next.js | Zero cold start on frontend, best-in-class DX, generous free tier | Serverless API routes have (small) cold starts; not GCP |
| **Cloud Run** | GCP serverless containers | GCP-unified, pay-per-use, scales to zero | ~1–2s cold start when idle (can mitigate with min-instances = $) |
| **Firebase Hosting + Cloud Functions** | GCP frontend CDN + serverless | GCP-unified, free tier, pairs natively with Firestore | Functions have cold starts; less slick DX than Vercel |
| **GCE / always-on VM** | A VM you manage | No cold starts | You maintain OS, updates, security — fails the maintainability test |

### Framework
Almost certainly **Next.js (React)**. It works on any of the above, has a huge ecosystem, and pairs with component libraries (shadcn/ui, Tailwind) that make "smooth and pleasing UX" achievable without designing from scratch.

### My read

**Vercel** if we optimize purely for UX + DX + "never think about ops."
**Cloud Run** if GCP-unified is a hard constraint.
Firebase Hosting is fine but only really shines paired with Firestore.

---

## 4. LLM

### Goal
Power an in-app chat assistant with tool-calling (read/write recipes, fill meal plan, etc.).

### Two separate questions

1. **Which model?** → Gemini 2.5 Flash (decided).
2. **How do we access it?** → the *API route*. Same model can be reached through different services, each with its own auth, quotas, and billing.

### API access options for Gemini

| Access route | Auth | Free tier | When to use |
|---|---|---|---|
| **Google AI Studio API key** (chosen) | Simple API key | **250 requests/day, unpaid** — no billing account required | Personal projects, prototyping, low-volume production |
| **Gemini API paid tier** (via AI Studio) | API key + billing enabled | Pay-per-token | When you outgrow 250 req/day |
| **Vertex AI** (GCP) | GCP service account, IAM, project setup | Bundled in GCP free credits | Enterprise use, needs full GCP integration, audit logs, VPC |
| **OpenRouter / LiteLLM / other aggregators** | Their API key | Varies | Only if multi-provider abstraction matters |

### Decided: Google AI Studio API key, free/unpaid tier

- **Quota:** 250 requests/day on Gemini 2.5 Flash, unpaid.
- **Auth:** single API key stored in Vercel env vars (`GEMINI_API_KEY`).
- **No billing account required** — stays truly free until we exceed the quota.
- Simpler than Vertex AI (no GCP project, no service account, no IAM roles).

### Headroom check
250 requests/day is ample for a single-user app: a full weekly meal-plan generation session might use 10–30 tool-calls; ad-hoc chat another 20–50/day. Plenty of margin.

### Upgrade path
If the quota becomes binding: flip on billing in AI Studio (same API key, now pay-per-token, Gemini 2.5 Flash is ~cents/day at personal volume). No code change. Vertex AI only becomes interesting if we want real GCP-native features — not on the horizon.

### Independence from the rest of the stack
API-key access means the LLM layer is decoupled from DB and hosting. We host on Vercel, use Neon, and call Gemini via HTTPS. Nothing about "unified Google" is gained or lost here.

---

## 5. How the pieces integrate

Two realistic bundles, given our constraints:

### Bundle A — "Best UX, mixed providers"
- **Hosting:** Vercel (Next.js)
- **DB:** Supabase (Postgres) or Neon (keep current DB, just change host)
- **LLM:** Gemini
- **Pros:** smoothest UX/DX, generous free tiers everywhere, SQL for nutrition, fastest to ship.
- **Cons:** three providers to manage accounts for, not unified.

### Bundle B — "Unified Google"
- **Hosting:** Cloud Run (Next.js in a container)
- **DB:** Cloud SQL (Postgres) *or* Firestore
- **LLM:** Gemini
- **Pros:** one cloud, one bill, one set of credentials, good for learning GCP.
- **Cons:** Cloud SQL isn't free (~$10/mo). Firestore is free but forces us into NoSQL and N+1 reads for nutrition. Cloud Run has small cold starts.

### Variant B' — "Unified Google, free"
- **Hosting:** Firebase Hosting + Cloud Functions
- **DB:** Firestore
- **LLM:** Gemini
- **Pros:** fully free, fully Google, realtime sync, easiest path to mobile later.
- **Cons:** NoSQL tax on nutrition aggregation (more code, more reads). Cold starts on functions.

---

## 6. Tradeoffs that actually matter

Ranked against our success criteria (smooth UX, low ops, 1-month sustained use):

1. **Cold starts kill daily usage.** Opening the app and waiting 2s every morning is a friction that compounds. This penalizes Render, Cloud Functions, and (mildly) Cloud Run. Favors Vercel + Firebase Hosting frontends.
2. **NoSQL pays a tax on nutrition.** It's workable but every aggregation query becomes app code + multiple DB reads. More code to maintain, more chances to break. Penalizes Firestore *for this specific product*.
3. **"Unified Google" is aesthetic, not functional.** Three providers with good free tiers is not meaningfully harder to maintain than one. Unless you want to learn GCP specifically — which is a valid separate goal.
4. **Free tier must actually be free.** Cloud SQL's ~$10/mo is cheap but non-zero. Over a year that's $120 for a personal project, and it'll nag you to kill it if you stop using it.

---

## 7. Questions to close out

1. Is "learn GCP" a goal of this project, or just a preference for tidiness?
2. How much do you care about the $0 vs. $10/mo distinction?
3. Have you used React / Next.js before, or would a different framework be less friction?
4. Do you want realtime sync (changes appear live across devices)? Firestore gives it free; Postgres requires extra work.
