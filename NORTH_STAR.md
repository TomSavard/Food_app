# North Star — Food_app

> Living document. Captures the "why" and the ideal end-state for the Food_app project.
> Resumed after a break — current stack (Neon DB + Render hosting) is functional but not optimal for daily use.

---

## 1. Raw notes (original dump)

Mon app pour la bouf c'est cool mais ce n'est probablement pas optimal pour un management scalable et facile des recettes. On doit passer par la database ou via l'app... Une approche utilisant simplement Obsidian pourrait être plus simple et permettre une intégration dans la nouvelle structure de Obsidian souhaitée ! (cf Karpathy).

La question à se poser, c'est : **qu'est-ce qui techniquement est intéressant à apprendre** (vLLM, Gemma et Qwen en local, les faire tourner en local via Claude Code) ? Ça, c'est plus sur le *comment*.

Concernant l'app, la question est : **qu'est-ce qui est chiant au quotidien ?** On ne veut pas faire un truc cool ou stylé — ça ne sert à rien. Ai-je un pain point, un truc qui vraiment me saoule ou prend du temps au quotidien ? Par exemple : savoir ce que je vais manger cette semaine. Faire les courses, c'est chronophage.

→ J'aimerais **industrialiser mon approche** : aller aux courses 1 fois par semaine (+ appoint au cas où) et avoir de la visibilité sur toute la semaine.

→ Il me faut :
- une base de données de recettes (en construction, mais pourrait être grandement agrandie via un LLM),
- une base de données d'apport nutritionnel — on a déjà la base **CIQUAL**, c'est le meilleur proxy actuel,
- un LLM local capable de faire du **matching d'un ingrédient avec sa référence dans la BDD**. Si la réf n'existe pas, peut-on update la BDD pour ajouter l'info ?
- une table de référence de la **saisonnalité** des fruits et légumes.

→ Je pense qu'il y a un véritable potentiel d'optimisation et de structuration de mon espace.

> **Raw data → LLM as a bookkeeper making a browsable and clean space → me having a view on what matters (recipes, shopping list, etc).**

The idea is mainly to focus on the **structuration**. How can we make the most controllable yet flexible and industrial system? How to make it scalable and not have to update everything each time?

I love the Obsidian approach: everything secure, locally. The question of the **display and app interface** still remains.

*→ To be well thought in the train and more :)*

---

## 2. Core principles (distilled)

1. **Solve a real pain point**, not build a cool toy. Pain #1: weekly meal planning + shopping. Pain #2: no visibility on actual nutritional intake.
2. **Proper app, not markdown.** Accessible from phone AND computer. v1 = web URL (responsive). Native mobile app is a later discussion.
3. **LLM as an in-app assistant.** A chat inside the app, with tool access to the recipe base, meal plan, shopping list, nutrition DB. It *fills* deterministic views on demand — it does not replace them.
4. **Deterministic UI, LLM-assisted filling.** The calendar / meal-plan / shopping-list views are hand-coded and deterministic. The LLM acts on them via documented "skills" (step-by-step procedures).
5. **Industrialize weekly rhythm:** 1 shop/week, full visibility on the week ahead.
6. **Google-unified stack (to validate).** Gemini 2.5 Flash via AI Studio for the LLM; prefer keeping DB + hosting under GCP for unification.

---

## 3. Ideal end-state

A web app (single URL, responsive, usable on phone and laptop) where I can:

- **Recipe base** — browse, search, edit recipes. LLM can propose new ones and add them on my validation.
- **Weekly meal plan** — deterministic 7-day calendar view. I can fill it by hand, or ask the assistant ("plan me a week, high protein, seasonal") and it populates the calendar slots.
- **Shopping list** — auto-derived from the week's plan, deduped, grouped by aisle, usable at the supermarket from my phone (checkboxes).
- **Nutrition tracking** — every recipe's ingredients are matched to the CIQUAL DB. For each day/week I see real intake (kcal, macros, micros). When an ingredient has no CIQUAL match, the LLM fills the gap from its own knowledge; that row is flagged as `source: llm` so I can audit it later.
- **In-app chat assistant** — sidebar/panel with Gemini, tool-enabled: read/write recipes, read/write the meal plan, trigger shopping-list regeneration, query nutrition, search CIQUAL, propose recipes.
- **Seasonality hint** — soft nudge, not hard filter.

---

## 4. Settled decisions

- **Interface:** web app (URL), responsive for phone + desktop. Not Obsidian. Not markdown.
- **Nutrition:** full tracking is a required feature, not optional. CIQUAL is the backbone; LLM fills gaps with a provenance flag.
- **LLM provider:** Gemini 2.5 Flash via Google AI Studio (free tier). Not local vLLM for v1. Local LLM becomes a separate "learn" track, decoupled from product.
- **LLM role:** in-app chat assistant with tools. Does not replace deterministic UI — it fills it.
- **Meal plan view:** deterministic, hand-coded calendar. Assistant operates on it via a documented skill (step-by-step procedure it follows).
- **Ingredient → CIQUAL:** fuzzy match via LLM; if miss, LLM writes a new row tagged `source: llm`.

---

## 5. Open questions

### Stack (needs validation before committing)

1. **Hosting.** Vercel is attractive (no cold start, great DX for Next.js). But it's not GCP. Tradeoff: unified-Google vs. best-tool. Options to compare:
   - Vercel (Next.js frontend + serverless API routes) + GCP for DB.
   - Google Cloud Run (containers, scales to zero — has cold start but small) — unified.
   - Firebase Hosting + Cloud Functions — unified, mobile-friendly later.
   **Question:** is "unified Google" a hard constraint, or a preference you'd trade for DX?

2. **Database on GCP.** Quick reality check:
   - **BigQuery is the wrong tool here.** It's an analytical warehouse — expensive per query, high latency, not meant for app CRUD.
   - **Cloud SQL (Postgres)** — closest equivalent to Neon. Has a free-ish tier but not truly free.
   - **Firestore** — NoSQL, generous free tier, great for app data, syncs to mobile later. Weaker for relational queries (nutrition joins could get awkward).
   - **AlloyDB / Spanner** — overkill.
   **Recommendation to discuss:** Firestore for app data (recipes, plans, shopping list) + a static CIQUAL reference table (could be a Firestore collection or bundled with the app). Keeps everything in GCP free tier.

3. **Framework.** Next.js (React) is the default for Vercel and works fine on Cloud Run too. OK with that, or do you want to explore alternatives?

### Product

4. **Existing app fate.** Migrate data from Neon → new DB, then shut Neon + Render down. Confirm?
5. **"Skill" for the meal-plan.** You mentioned a step-by-step guide the LLM follows. Want to draft its steps in this doc, or defer until we have the UI?
6. **Success metric — settled.** Continuous, unbroken usage of the app for at least one month. The experience must be smooth, pleasing, and enjoyable — friction kills it. Maintainability matters equally: if I can't keep it running without pain, it fails. Implication: UX polish and low operational overhead are first-class concerns, not afterthoughts.

---

## 6. Backtracked plan (draft)

1. **Stack decision** → pick hosting + DB (answer Q1-Q3 above).
2. **Data model** → define schemas: `recipe`, `ingredient`, `ciqual_entry`, `meal_plan`, `shopping_list`, `nutrition_log`.
3. **Migrate** recipes from Neon → new DB. Retire Neon + Render.
4. **Scaffold** web app (auth = just me for now, single user).
5. **Build deterministic views** in order of payoff:
   a. Recipe CRUD.
   b. Weekly calendar (meal plan).
   c. Shopping list (derived from plan).
   d. Nutrition dashboard.
6. **Integrate Gemini** as in-app chat with tool-calling.
7. **Write the meal-plan "skill"** (procedure doc the LLM follows).
8. **CIQUAL matcher** + LLM fallback with `source` flag.
9. **Seasonality hint** in recipe suggestions.
