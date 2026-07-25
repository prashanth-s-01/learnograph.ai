# Learnograph — Scaffold all PDD prompt modules and shared preamble

## Summary

Bootstrap the full PDD source layer for Learnograph: five prompt files, one shared preamble, one `context/test.prompt`, and the user story files each prompt's `<coverage>` section links to. These are the only files humans author by hand. All agent code (`dag_generator.py`, `content_classifier.py`, `node_enricher.py`, `comprehension.py`, `dag_regenerator.py`) is generated output — regenerated from these prompts, never hand-patched.

**Core loop:** generate → observe → validate → regenerate
**PDD rule:** if behavior needs to change, edit the prompt and regenerate. Never patch the generated code directly.

---

## Sponsor and tech stack map

Every sponsor must be used in the correct module. This table is the source of truth — check each prompt's `<capabilities>` section against it before marking the issue complete.

| Sponsor / Tool | Which prompt(s) use it | Exact role | Prize track |
|---|---|---|---|
| **PDD** | All five prompts | Prompts are the authored source of truth; code is regenerated output, never hand-patched | Required track — project does not qualify without it |
| **MiniMax** | `generate_dag`, `classify_content`, `comprehension_check`, `regenerate_dag` | Sole reasoning LLM across the whole pipeline. Long context window carries full DAG + mem0 progress state on every call | Silver — Best Use of MiniMax ($3k / $2k / $1k) |
| **Band** | All five prompts (orchestration only, not reasoning) | Agent-to-agent event bus. Each agent publishes a completion event when its work is done; Band routes that event to trigger the next agent in the pipeline. No agent calls another agent's function directly. | Silver — has its own $500 track |
| **Rtrvr.ai** | Pre-step for `classify_content` (scrapes active tab); `enrich_node` (finds and ranks resources) | Two distinct jobs: (1) extract real page text so the classifier has substance not just a URL; (2) search and validate external resource URLs per node | Bronze — $30/person credits |
| **mem0** | `generate_dag` (read), `regenerate_dag` (read) | Persistent learning-state memory: completed nodes, completion timestamps, triggering content, pace, and content-format preferences. Written to by the API layer after `comprehension_check` returns `pass`, not by the agents themselves | Bronze |
| **ElevenLabs** | Pre-step and post-step for `comprehension_check` | Pre-step: asks the user to explain the concept aloud and transcribes the spoken answer to text before the agent runs. Post-step (optional): reads feedback sentence aloud. The agent itself receives and returns text only | Supporter — 6 months Scale tier per team member for Best Project with ElevenLabs |
| **Render Workflows** | Deployment pipeline (`render.yaml`) | Five explicit pipeline steps: generate → enrich → classify → regenerate → comprehension_check. Each step is triggered by a Band event subscription rather than plain sequential order. Must not be a single monolithic handler | **Required for Grand Prize ($2,300 + VC pitch) / 2nd ($1,100) / 3rd ($500)** |

**Tech stack — full list for reference:**

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI |
| Agent models (Pydantic) | `backend/models/dag.py` |
| Database | Postgres — DAG snapshots, node metadata, session state |
| Memory layer | mem0 — learning state across sessions |
| Agent orchestration | Band — pub/sub event bus connecting the five agents |
| Frontend | React, Next.js |
| DAG visualization | React Flow |
| Realtime sync | WebSockets — extension fires, node lights up in React Flow |
| Browser extension | Chrome, Manifest V3 — content scripts only, no persistent background |
| Deployment | Render Workflows (5 explicit steps, each triggered by a Band event) |
| Auth | None — hardcoded single user for hackathon |

---

## Shared preamble — create first

**File:** `context/project_preamble.prompt`

Include this at the top of every prompt file via `<include>context/project_preamble.prompt</include>`.

Contents to define:

**Backend stack:**
- Language: Python 3.11, FastAPI, Pydantic v2
- Database: Postgres via `backend/db/postgres.py` — stores DAG snapshots and node state
- Memory: mem0 via `backend/memory/mem0_client.py` — stores learning state across sessions
- Orchestration: Band via `backend/orchestration/band_client.py` — agents publish/subscribe to named events; no agent calls another agent's function directly
- Realtime: WebSocket server at `WS /ws` — pushes node state changes to the React frontend the moment an agent updates state

**Frontend stack** (reference only — agents do not generate frontend code):
- React + Next.js, single page at `frontend/pages/index.tsx`
- DAG rendered with React Flow in `frontend/components/DAGCanvas.tsx`
- Voice check UI in `frontend/components/VoiceCheck.tsx` (calls ElevenLabs)
- WebSocket client hook at `frontend/hooks/useWebSocket.ts`

**Chrome extension** (reference only):
- Manifest V3 — content scripts per active tab, no persistent background listener
- `extension/content.js` extracts page title, meta, and visible text → POST to `/classify`
- Rtrvr.ai is called server-side after `/classify` receives the URL, not in the extension itself

**Band event map — the orchestration contract every agent must follow:**

| Event published | Published by | Subscribed by |
|---|---|---|
| `dag.generated` | `generate_dag` | `enrich_node` |
| `node.enriched` | `enrich_node` | (terminal for this branch — no further agent triggered) |
| `content.classified` | `classify_content` | `regenerate_dag` |
| `dag.regenerated` | `regenerate_dag` | (terminal for this branch — pushes to WebSocket) |
| `node.mastered` | API layer, after `comprehension_check` returns `pass` | `regenerate_dag` |

Each agent publishes exactly one event on successful completion and zero events on failure. No agent subscribes to an event it does not need, and no agent publishes an event outside this table.

**mem0 write path — owned by the API layer, not by any agent:**
- `generate_dag` reads mem0 (user profile) — never writes
- `regenerate_dag` reads mem0 (full state) — never writes
- The FastAPI route handler writes to mem0 after `comprehension_check` returns `pass` and the node status is updated to `mastered` in Postgres

**Project-wide MUST NOT rules (apply to all agents):**
- MUST NOT hand-patch generated output — edit the prompt and regenerate
- MUST NOT hardcode node IDs or match logic in code
- MUST NOT log API keys, bearer tokens, or mem0 secrets
- MUST NOT call another agent's function directly — communicate only via Band events (see table above) and shared DAG state in Postgres

**DAG node schema — shared contract for all agents:**

```json
{
  "id": "react-hooks",
  "title": "React Hooks",
  "description": "useState, useEffect, useContext — the three hooks that cover 90% of use cases",
  "prerequisites": ["react-components", "javascript-closures"],
  "difficulty": "beginner | intermediate | advanced",
  "estimated_hours": 3,
  "success_criteria": "Can explain what useEffect's dependency array does and why it matters",
  "status": "locked | available | seen | mastered",
  "resources": [],
  "completed_at": null,
  "triggering_content": null
}
```

---

## User story files — create alongside the prompts

Per the prompting guide's two-file split, each story lives as a human-authored file at `user_stories/story__<name>.md` (plain "As a / I want / so that", nothing else) plus a generated contract at `user_stories/contracts/<name>.contract.md`. Create the ten story files below; contracts are generated from these plus this issue, not hand-authored.

**`user_stories/story__generate_dag_new_user.md`**
```md
<!-- pdd-story-prompts: prompts/generate_dag.prompt -->

# User Story: New user gets a complete DAG

## Story

As a developer,
I want to enter "Learn React" and receive a DAG of learning nodes,
so that I have a structured roadmap with clear prerequisite ordering.
```

**`user_stories/story__generate_dag_returning_user.md`**
```md
<!-- pdd-story-prompts: prompts/generate_dag.prompt -->

# User Story: Returning user skips mastered nodes

## Story

As a returning developer,
I want nodes I have already mastered to be excluded from my new DAG,
so that the roadmap reflects where I actually am, not where I started.
```

**`user_stories/story__generate_dag_rejects_non_dev_topics.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/generate_dag.prompt -->

# User Story: Non-developer topic rejected

## Story

As a developer,
I want non-developer topics like "Learn to cook" to produce no roadmap nodes,
so that the tool stays scoped to software skills.
```

**`user_stories/story__classify_content_video_match.md`**
```md
<!-- pdd-story-prompts: prompts/classify_content.prompt -->

# User Story: YouTube video matches a node

## Story

As a developer watching a YouTube tutorial on React hooks,
I want the classifier to match that video to the "React Hooks" node,
so that my progress updates without any manual action.
```

**`user_stories/story__classify_content_offtopic_returns_null.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/classify_content.prompt -->

# User Story: Off-topic page returns no match

## Story

As a developer browsing an unrelated site,
I want the classifier to return no match,
so that unrelated browsing does not pollute my roadmap progress.
```

**`user_stories/story__classify_content_locked_node_never_matches.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/classify_content.prompt -->

# User Story: Locked node never matches

## Story

As a developer reading about an advanced topic whose prerequisites I haven't completed,
I want that node to remain locked and unmatched,
so that my DAG only progresses in a valid order.
```

**`user_stories/story__enrich_node_curated_resources.md`**
```md
<!-- pdd-story-prompts: prompts/enrich_node.prompt -->

# User Story: Node gets curated resources

## Story

As a developer viewing a "React Hooks" node,
I want to see a GitHub repo, an official doc link, and a YouTube tutorial,
so that I have curated starting points without searching manually.
```

**`user_stories/story__enrich_node_no_fabricated_urls.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/enrich_node.prompt -->

# User Story: No fabricated URLs

## Story

As a developer,
I want every linked resource to be a real, reachable URL,
so that I never click a broken link from my roadmap.
```

**`user_stories/story__comprehension_correct_explanation_passes.md`**
```md
<!-- pdd-story-prompts: prompts/comprehension_check.prompt -->

# User Story: Correct explanation earns pass

## Story

As a developer who correctly explains useEffect's dependency array,
I want the comprehension check to return a pass with confirming feedback,
so that my node status advances to "mastered".
```

**`user_stories/story__comprehension_verbatim_repeat_fails.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/comprehension_check.prompt -->

# User Story: Verbatim repeat does not pass

## Story

As a developer who repeats the success_criteria word for word without demonstrating understanding,
I want the check to return "needs_review",
so that rote repetition cannot inflate my progress.
```

**`user_stories/story__comprehension_empty_answer_needs_review.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/comprehension_check.prompt -->

# User Story: Empty answer returns needs_review

## Story

As a developer who says nothing or gives an off-topic answer,
I want the check to return "needs_review" with helpful feedback,
so that I know what I still need to cover.
```

**`user_stories/story__regenerate_dag_unlocks_dependants.md`**
```md
<!-- pdd-story-prompts: prompts/regenerate_dag.prompt -->

# User Story: Mastered node unlocks dependants

## Story

As a developer who just mastered "React Components",
I want the DAG to immediately unlock "React Hooks" and other direct dependants,
so that my available next steps reflect what I have actually learned.
```

**`user_stories/story__regenerate_dag_no_regression.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/regenerate_dag.prompt -->

# User Story: Mastered nodes cannot regress

## Story

As a developer,
I want nodes I have already mastered to stay mastered after every regeneration,
so that progress is never rolled back.
```

**`user_stories/story__regenerate_dag_no_nodes_lost.md`** *(negative)*
```md
<!-- pdd-story-prompts: prompts/regenerate_dag.prompt -->

# User Story: No nodes dropped or invented

## Story

As a developer,
I want my full roadmap to remain intact after every regeneration,
so that the graph never loses nodes I haven't reached yet.
```

Contracts (`user_stories/contracts/<name>.contract.md`) are generated from these Story files plus this issue — do not hand-author them. Use `pdd story add` / `pdd fix user_stories/story__*.md` as described in the guide once the prompts below exist.

---

## Prompt 1 — `prompts/generate_dag.prompt`

**Sponsors used:** MiniMax (reasoning LLM), mem0 (read user profile), Band (publishes `dag.generated`)
**Prize track:** Best Use of MiniMax — this is the primary reasoning call; pass the full mem0 profile in context on every call to exploit MiniMax's long context window

```xml
% Role:
% You are an expert Python engineer.
% Implement generate_dag.

<include>context/project_preamble.prompt</include>

<pdd-reason>Generates the initial developer learning DAG from a topic and mem0 user profile.</pdd-reason>

<pdd-interface>
{
  "type": "module",
  "module": {
    "functions": [
      {
        "name": "generate_dag",
        "signature": "(topic: str, user_profile: dict | None) -> list[DAGNode]",
        "returns": "list[DAGNode]"
      }
    ]
  }
}
</pdd-interface>

<responsibility>
Accepts a developer learning topic and a mem0 user profile snapshot, and returns a complete DAG of learning nodes with prerequisite relationships. Publishes a `dag.generated` Band event on success.
</responsibility>

<non_responsibilities>
- Does not enrich nodes with resources (`enrich_node` owns that, triggered via the `dag.generated` Band event).
- Does not classify content or update node status.
- Does not persist the DAG to Postgres.
</non_responsibilities>

<vocabulary>
- DAGNode: a single learning concept conforming to the shared node schema in the preamble.
- Prerequisite relationship: node A is a prerequisite of node B when B cannot be meaningfully learned without A.
- Available node: a node whose prerequisites are all mastered or empty.
- Developer topic: a software engineering skill, tool, language, or concept (e.g. "Learn React", "Master system design", "Understand TCP/IP").
</vocabulary>

<contract_rules>
R1 (MUST): Return a valid list of DAGNode objects conforming to the shared node schema for any developer topic input.
R2 (MUST): Set prerequisite relationships so no node depends on itself and no circular dependency exists.
R3 (MUST): Set status to "available" for root nodes (no prerequisites) and "locked" for all others.
R4 (MUST): Set success_criteria to a single testable sentence a human can self-assess against.
R5 (MUST NOT): Return fewer than 5 nodes or more than 30 nodes for any topic.
R6 (MUST NOT): Include non-developer topics (recipes, fitness, general knowledge) — scope is software engineering only.
R7 (MUST NOT): Hardcode specific node IDs — generate IDs as kebab-case slugs derived from the node title.
R8 (MUST): If user_profile contains mastered node IDs, exclude those nodes from the returned DAG and unlock their direct dependants.
</contract_rules>

<capabilities>
- MAY read user_profile from mem0 (read-only).
- MAY call MiniMax LLM API.
- MAY publish a `dag.generated` event to Band on success.
- MUST NOT write to Postgres.
- MUST NOT call Rtrvr.ai or ElevenLabs.
- MUST NOT modify user_profile.
- MUST NOT call another agent's function directly.
</capabilities>

<coverage>
R1: story__generate_dag_new_user.md
R2: story__generate_dag_new_user.md
R3: story__generate_dag_new_user.md
R4: story__generate_dag_new_user.md
R5: story__generate_dag_new_user.md
R6: story__generate_dag_rejects_non_dev_topics.md
R7: TODO add dedicated slug-collision story before production use
R8: story__generate_dag_returning_user.md
</coverage>
```

---

## Prompt 2 — `prompts/classify_content.prompt`

**Sponsors used:** Rtrvr.ai (pre-step — scrapes active tab before this agent runs), MiniMax (reasoning LLM), Band (publishes `content.classified`)
**Rtrvr.ai pre-step (runs in the `/classify` FastAPI route before calling this agent):**
1. Receive `page_url` from the Chrome extension
2. Call Rtrvr.ai to extract clean page text (strips nav, ads, boilerplate)
3. Pass the extracted `page_text` + `page_url` into this agent

This agent never calls Rtrvr.ai directly — it receives `page_text` as a pre-scraped input.

```xml
% Role:
% You are an expert Python engineer.
% Implement classify_content.

<include>context/project_preamble.prompt</include>

<pdd-reason>Classifies scraped tab content against the current DAG to identify the matching node.</pdd-reason>

<pdd-interface>
{
  "type": "module",
  "module": {
    "functions": [
      {
        "name": "classify_content",
        "signature": "(page_text: str, page_url: str, available_nodes: list[dict]) -> str | None",
        "returns": "str | None — matched node ID, or null if no confident match"
      }
    ]
  }
}
</pdd-interface>

<responsibility>
Accepts scraped text from the user's active browser tab and the current list of available node IDs and titles, and returns the single best-matching node ID or `null`. Publishes a `content.classified` Band event when a match is found.
</responsibility>

<non_responsibilities>
- Does not scrape content (Rtrvr.ai owns that, called before this agent).
- Does not update node status in Postgres.
- Does not decide what to do after a match is found (`regenerate_dag` owns that, triggered via the `content.classified` Band event).
</non_responsibilities>

<vocabulary>
- Confident match: the page text substantively covers the concept described by the node's title and success_criteria, not merely mentions the word.
- available_nodes: nodes with status `available` or `seen` — locked nodes must not be matched.
- page_text: plain text extracted from the active tab by Rtrvr.ai, stripped of navigation and boilerplate.
</vocabulary>

<contract_rules>
R1 (MUST): Return a node ID only when the page text substantively covers that node's concept.
R2 (MUST): Return null when no available node is a confident match.
R3 (MUST NOT): Return a node ID for a locked node (status = "locked").
R4 (MUST NOT): Match on keyword presence alone — the content must address the node's success_criteria.
R5 (MUST NOT): Return more than one node ID — one match or null, never a list.
R6 (MUST): Operate only on the nodes passed in available_nodes — must not invent or assume other nodes exist.
</contract_rules>

<capabilities>
- MAY call MiniMax LLM API.
- MAY publish a `content.classified` event to Band when a match is found.
- MUST NOT write to Postgres or mem0.
- MUST NOT call Rtrvr.ai (content is already scraped and passed in as page_text).
- MUST NOT call ElevenLabs.
- MUST NOT call another agent's function directly.
</capabilities>

<coverage>
R1: story__classify_content_video_match.md
R2: story__classify_content_offtopic_returns_null.md
R3: story__classify_content_locked_node_never_matches.md
R4: story__classify_content_video_match.md, story__classify_content_offtopic_returns_null.md
R5: TODO add dedicated multi-candidate-match story before production use
R6: TODO add dedicated invented-node-id story before production use
</coverage>
```

---

## Prompt 3 — `prompts/enrich_node.prompt`

**Sponsors used:** Rtrvr.ai (searches and validates all resource URLs — no LLM needed for this step), Band (subscribes to `dag.generated`, publishes `node.enriched`)
**Rtrvr.ai usage here:** two search calls per node — (1) search GitHub for the most-starred relevant repo; (2) search for and validate the official maintainer doc URL and a developer YouTube video. This agent defines the query strategy and ranking criteria; Rtrvr.ai executes the searches.

```xml
% Role:
% You are an expert Python engineer.
% Implement enrich_node.

<include>context/project_preamble.prompt</include>

<pdd-reason>Populates a DAG node with 3 curated developer resources (GitHub repo, doc, video) via Rtrvr.ai.</pdd-reason>

<pdd-interface>
{
  "type": "module",
  "module": {
    "functions": [
      {
        "name": "enrich_node",
        "signature": "(node_title: str, success_criteria: str) -> list[Resource]",
        "returns": "list[Resource] — exactly 3 items: [github_repo, official_doc, youtube_video]"
      }
    ]
  }
}
</pdd-interface>

<responsibility>
Accepts a node title and success_criteria and returns exactly 3 ranked developer resources for that node: one GitHub repo, one official documentation page, one developer-focused YouTube video. Runs once per node in response to the `dag.generated` Band event; publishes `node.enriched` on success.
</responsibility>

<non_responsibilities>
- Does not generate or modify the DAG.
- Does not classify content or check comprehension.
- Does not persist resources — returns them for the caller to attach to the node.
</non_responsibilities>

<vocabulary>
- Resource: `{ "type": "github" | "doc" | "youtube", "title": str, "url": str, "reason": str }`.
- Official documentation: the primary documentation site published by the maintainer of the technology (e.g. react.dev for React, docs.python.org for Python).
- Developer-focused YouTube video: a tutorial or explanation video from a channel focused on software engineering education.
</vocabulary>

<contract_rules>
R1 (MUST): Return exactly 3 resources in order: github_repo, official_doc, youtube_video.
R2 (MUST): Each resource must include type, title, url, and reason fields.
R3 (MUST NOT): Return resources that are not scoped to software engineering or developer education.
R4 (MUST NOT): Return the same URL more than once in a single response.
R5 (MUST): The official_doc resource must link to the maintainer's own documentation, not a third-party tutorial site.
R6 (MUST NOT): Fabricate URLs — only return URLs that Rtrvr.ai scraping confirms exist.
</contract_rules>

<capabilities>
- MAY call Rtrvr.ai to search and validate resource URLs.
- MAY subscribe to the `dag.generated` Band event and publish `node.enriched` on success.
- MUST NOT call MiniMax LLM API — this is a scraping step, not a reasoning step.
- MUST NOT call ElevenLabs.
- MUST NOT write to Postgres or mem0.
- MUST NOT call another agent's function directly.
</capabilities>

<coverage>
R1: story__enrich_node_curated_resources.md
R2: story__enrich_node_curated_resources.md
R3: TODO add dedicated out-of-scope-resource story before production use
R4: TODO add dedicated duplicate-URL story before production use
R5: story__enrich_node_curated_resources.md
R6: story__enrich_node_no_fabricated_urls.md
</coverage>
```

---

## Prompt 4 — `prompts/comprehension_check.prompt`

**Sponsors used:** ElevenLabs (voice I/O pre-step and optional post-step), MiniMax (scoring LLM), Band (publishes `node.mastered` — via the API layer, not this agent directly)
**Prize track:** Best Project with ElevenLabs — 6 months Scale tier per team member

**ElevenLabs integration — two steps around this agent (neither is inside the agent):**
- **Pre-step (in `VoiceCheck.tsx` frontend component):**
  1. ElevenLabs TTS asks the question aloud: `"Explain [success_criteria concept] in your own words."`
  2. ElevenLabs STT records and transcribes the user's spoken answer to plain text
  3. The transcribed text is sent to `POST /comprehension/score` alongside the node's `success_criteria`
- **Post-step (optional, same component):**
  1. ElevenLabs TTS reads the `feedback` sentence from `ComprehensionResult` aloud
  2. If verdict is `pass`, plays a confirmation; if `needs_review`, reads the feedback as coaching

This agent receives and returns **text only** — it never calls ElevenLabs directly. On a `pass` verdict, the FastAPI route handler (not this agent) publishes a `node.mastered` Band event after writing to Postgres and mem0.

```xml
% Role:
% You are an expert Python engineer.
% Implement score_comprehension.

<include>context/project_preamble.prompt</include>

<pdd-reason>Scores a transcribed spoken answer against a node success_criteria; returns pass/needs_review plus feedback.</pdd-reason>

<pdd-interface>
{
  "type": "module",
  "module": {
    "functions": [
      {
        "name": "score_comprehension",
        "signature": "(success_criteria: str, transcribed_answer: str) -> ComprehensionResult",
        "returns": "ComprehensionResult"
      }
    ]
  }
}
</pdd-interface>

<responsibility>
Accepts a node's success_criteria and the user's spoken answer (already transcribed to text by ElevenLabs), and returns a pass/fail verdict plus one sentence of feedback.
</responsibility>

<non_responsibilities>
- Does not record audio or transcribe speech (ElevenLabs owns that — see pre-step above).
- Does not update node status in Postgres (the caller does that on pass).
- Does not generate the question to ask the user — derived from success_criteria by the caller.
- Does not write to mem0 or publish the `node.mastered` Band event (the API layer does both, after receiving a pass verdict).
</non_responsibilities>

<vocabulary>
- pass: the transcribed answer demonstrates that the user can address the success_criteria in their own words, even if imperfectly phrased.
- needs_review: the answer is missing, off-topic, or does not address the core concept in success_criteria.
- success_criteria: a single testable sentence from the node schema (e.g. "Can explain what useEffect's dependency array does and why it matters").
</vocabulary>

<contract_rules>
R1 (MUST): Return verdict "pass" only when the answer substantively addresses the success_criteria.
R2 (MUST): Return verdict "needs_review" when the answer is empty, incoherent, or off-topic.
R3 (MUST): Return feedback as exactly one sentence, specific to what the user actually said.
R4 (MUST NOT): Return "pass" for answers that merely repeat the success_criteria verbatim without demonstrating understanding.
R5 (MUST NOT): Penalise imperfect phrasing, filler words, or non-native English — assess conceptual understanding only.
R6 (MUST NOT): Include the success_criteria text in the feedback response.
R7 (MUST NOT): Ask follow-up questions in the feedback — one sentence of forward-pointing feedback only.
</contract_rules>

<capabilities>
- MAY call MiniMax LLM API.
- MUST NOT call ElevenLabs (transcription is done before this agent is called).
- MUST NOT write to Postgres or mem0.
- MUST NOT call Rtrvr.ai.
- MUST NOT publish Band events directly — the API layer publishes `node.mastered` after receiving this agent's `pass` verdict.
- MUST NOT call another agent's function directly.
</capabilities>

<coverage>
R1: story__comprehension_correct_explanation_passes.md
R2: story__comprehension_empty_answer_needs_review.md
R3: story__comprehension_correct_explanation_passes.md, story__comprehension_empty_answer_needs_review.md
R4: story__comprehension_verbatim_repeat_fails.md
R5: TODO add dedicated non-native-phrasing story before production use
R6: TODO add dedicated feedback-leakage story before production use
R7: TODO add dedicated no-follow-up-question story before production use
</coverage>
```

---

## Prompt 5 — `prompts/regenerate_dag.prompt`

**Sponsors used:** MiniMax (reasoning LLM), Band (subscribes to `content.classified` and `node.mastered`, publishes `dag.regenerated`), mem0 (read full learning state)

```xml
% Role:
% You are an expert Python engineer.
% Implement regenerate_dag.

<include>context/project_preamble.prompt</include>

<pdd-reason>Restructures the DAG after a node state change using MiniMax, orchestrated via Band agent messaging.</pdd-reason>

<pdd-interface>
{
  "type": "module",
  "module": {
    "functions": [
      {
        "name": "regenerate_dag",
        "signature": "(current_dag: list[DAGNode], mem0_state: dict) -> list[DAGNode]",
        "returns": "list[DAGNode] — same nodes, updated status and ordering"
      }
    ]
  }
}
</pdd-interface>

<responsibility>
Accepts the full current DAG JSON and the full mem0 state, and returns an updated DAG with reordered recommendations, newly unlocked nodes, and updated priorities based on what the user has actually mastered. Runs whenever Band delivers a `content.classified` or `node.mastered` event; publishes `dag.regenerated` on success.
</responsibility>

<non_responsibilities>
- Does not classify content or score comprehension.
- Does not add new top-level topics — only restructures the existing DAG.
- Does not write to Postgres or mem0 (the caller persists the result).
</non_responsibilities>

<vocabulary>
- Unlocked node: a node whose prerequisites have all transitioned to status `mastered`.
- mem0_state: the full user memory object from mem0, including completed node IDs, completion timestamps, content format preferences, and learning pace.
- Reordering: changing the recommended next-node priority based on what was just mastered and the user's observed learning pace — not changing prerequisite relationships.
</vocabulary>

<contract_rules>
R1 (MUST): Return every node from the input DAG — never drop nodes.
R2 (MUST): Unlock every node whose prerequisites are all mastered in the returned DAG.
R3 (MUST): Preserve all prerequisite relationships exactly as received — never add or remove edges.
R4 (MUST NOT): Change any node's id, title, description, or success_criteria fields.
R5 (MUST NOT): Change the status of a mastered node to any other status.
R6 (MUST): Use mem0_state.completed_at timestamps to infer learning pace and reorder available nodes by estimated fit.
R7 (MUST NOT): Invent new nodes — only update existing ones.
</contract_rules>

<capabilities>
- MAY call MiniMax LLM API.
- MAY read mem0_state (read-only).
- MAY subscribe to `content.classified` and `node.mastered` Band events, and publish `dag.regenerated` on success.
- MUST NOT write to mem0.
- MUST NOT call Rtrvr.ai or ElevenLabs.
- MUST NOT write to Postgres.
- MUST NOT call another agent's function directly.
</capabilities>

<coverage>
R1: story__regenerate_dag_no_nodes_lost.md
R2: story__regenerate_dag_unlocks_dependants.md
R3: story__regenerate_dag_no_nodes_lost.md
R4: TODO add dedicated field-immutability story before production use
R5: story__regenerate_dag_no_regression.md
R6: TODO add dedicated pace-reordering story before production use
R7: story__regenerate_dag_no_nodes_lost.md
</coverage>
```

---

## Render Workflows — `render.yaml`

**Required for Grand Prize ($2,300 + VC pitch) / 2nd place ($1,100) / 3rd place ($500).**
Plain Render hosting without Workflows does not qualify. The pipeline must be structured as five explicit, named steps — not a single monolithic API handler. Each step is a Band event subscriber, not a plain sequential script call.

```yaml
# render.yaml — Learnograph pipeline
services:
  - type: worker
    name: learnograph-pipeline
    workflows:
      - name: generate-and-enrich
        steps:
          - name: generate_dag
            # Calls Agent 1 — prompts/generate_dag.prompt
            # LLM: MiniMax (reasoning)
            # Reads: mem0 user profile
            # Writes: DAG snapshot to Postgres
            # Publishes: dag.generated (Band)
            run: python -m backend.agents.dag_generator

          - name: enrich_nodes
            # Calls Agent 3 — prompts/enrich_node.prompt
            # Tool: Rtrvr.ai (no LLM)
            # Triggered by: dag.generated (Band), runs in parallel per node
            # Writes: resource lists back to DAG in Postgres
            # Publishes: node.enriched (Band)
            run: python -m backend.agents.node_enricher

      - name: classify-and-update
        steps:
          - name: classify_content
            # Calls Agent 2 — prompts/classify_content.prompt
            # Pre-step: Rtrvr.ai scrapes the URL first (inline, same step)
            # LLM: MiniMax (fast call)
            # Writes: node status update to Postgres + WebSocket push
            # Publishes: content.classified (Band)
            run: python -m backend.agents.content_classifier

          - name: regenerate_dag
            # Calls DAG Regenerator — prompts/regenerate_dag.prompt
            # LLM: MiniMax
            # Triggered by: content.classified or node.mastered (Band)
            # Reads: full mem0 state
            # Writes: updated DAG to Postgres + WebSocket push
            # Publishes: dag.regenerated (Band)
            run: python -m backend.agents.dag_regenerator

      - name: comprehension
        steps:
          - name: comprehension_check
            # Calls Agent 4 — prompts/comprehension_check.prompt
            # Pre-step: ElevenLabs STT transcribes user's spoken answer (handled in frontend)
            # LLM: MiniMax (scorer)
            # On pass: API layer writes mastered status to Postgres + mem0, publishes node.mastered (Band)
            run: python -m backend.agents.comprehension
```

**Acceptance check for this section:**
- [ ] `render.yaml` exists with all five named steps
- [ ] Each step references the correct agent module
- [ ] Steps are in separate named workflows, not collapsed into one
- [ ] `POST /dag/regenerate` explicitly calls the MiniMax-backed step, triggered via Band, not a direct sequential call

---

## `context/test.prompt` — test generation guidance

Create this file so `pdd test` generates contract-aware tests for all five modules.

Contents:

```
When generating tests from a PDD prompt for Learnograph:

1. Read the <contract_rules> section for the module.
2. For every MUST and MUST NOT rule, generate at least one test unless explicitly marked non-testable.
3. Name tests to reference the rule ID: test_R1_returns_valid_dag_nodes, test_R3_locked_node_not_matched.
4. Include a negative test for every MUST NOT rule.
5. Assert observable behavior only — return values, status fields, error types.
6. MUST NOT assert private helper names, internal class structure, or exact error message strings.
7. For exception assertions, use pytest.raises(ErrorType, match=r"keyword1|keyword2").
8. Preserve existing tests — never overwrite accumulated regression tests (use --merge).
9. If a rule cannot be tested without a fixture that does not exist yet, add a comment describing the missing fixture.

Framework: pytest
Mocks: use unittest.mock for MiniMax, Rtrvr.ai, ElevenLabs, and Band publish/subscribe calls — never call real APIs or a real Band connection in tests.
DAG fixture: use the shared node schema in context/project_preamble.prompt as the base fixture shape.
```

---

## Coverage summary

| Prompt | R-count | Story files linked | TODO (rules with no story yet) |
|---|---|---|---|
| generate_dag | R1–R8 | 3 | R7 |
| classify_content | R1–R6 | 3 | R5, R6 |
| enrich_node | R1–R6 | 2 | R3, R4 |
| comprehension_check | R1–R7 | 3 | R5, R6, R7 |
| regenerate_dag | R1–R7 | 3 | R4, R6 |

Rules marked as `TODO` in each prompt's `<coverage>` section are at contract evidence level 1 (prompt-only) — story-backed coverage should be added for these before the module is treated as production-safe. All others are at level 2 (story-backed) on creation. Promote to level 3 (test-backed) by running:

```bash
pdd test prompts/generate_dag.prompt backend/agents/dag_generator.py
pdd test prompts/classify_content.prompt backend/agents/content_classifier.py
pdd test prompts/enrich_node.prompt backend/agents/node_enricher.py
pdd test prompts/comprehension_check.prompt backend/agents/comprehension.py
pdd test prompts/regenerate_dag.prompt backend/agents/dag_regenerator.py
```

---

## Acceptance criteria for this issue

**PDD source files:**
- [ ] `context/project_preamble.prompt` exists with DAG node schema, full tech stack reference, Band event map, mem0 write path, and project-wide MUST NOT rules
- [ ] All five prompt files exist in `prompts/` using the guide's XML tag structure (`<pdd-reason>`, `<pdd-interface>`, `<responsibility>`, `<non_responsibilities>`, `<vocabulary>`, `<contract_rules>`, `<capabilities>`, `<coverage>`) — not plain markdown headers
- [ ] All fourteen story files exist in `user_stories/` following the human-Story template (Story section only — no contract sections hand-authored)
- [ ] `context/test.prompt` exists with contract-aware test generation instructions
- [ ] Running `pdd generate prompts/generate_dag.prompt` produces `backend/agents/dag_generator.py` without error
- [ ] Running `pdd generate` on each remaining prompt produces its agent file without error
- [ ] No generated agent file is hand-patched

**Sponsor coverage checks:**
- [ ] `generate_dag.prompt` capabilities: MAY call MiniMax, MAY read mem0, MAY publish `dag.generated` to Band — no other LLM or sponsor
- [ ] `classify_content.prompt` capabilities: MAY call MiniMax, MAY publish `content.classified` to Band — Rtrvr.ai is a pre-step in the route handler, not inside this agent
- [ ] `enrich_node.prompt` capabilities: MAY call Rtrvr.ai, MAY subscribe to `dag.generated` / publish `node.enriched` — MUST NOT call MiniMax
- [ ] `comprehension_check.prompt` capabilities: MAY call MiniMax — ElevenLabs is a pre/post-step in the frontend, not inside this agent; Band event is published by the API layer, not this agent
- [ ] `regenerate_dag.prompt` capabilities: MAY call MiniMax, MAY subscribe to `content.classified` / `node.mastered`, MAY publish `dag.regenerated`
- [ ] `render.yaml` exists with five named steps, each described as a Band event subscriber

**Prize track readiness:**
- [ ] MiniMax is used in all four reasoning agents (generate_dag, classify_content, comprehension_check, regenerate_dag) — Best Use of MiniMax track
- [ ] Band orchestrates all five agents via the event map in the preamble — Band's $500 track
- [ ] ElevenLabs pre/post-step is wired in `VoiceCheck.tsx` — Best Project with ElevenLabs track
- [ ] `render.yaml` uses named Workflow steps, not plain hosting — Grand Prize track

## Out of scope for this issue

- Writing the actual agent code (that is generated output from `pdd generate`)
- Frontend components (`DAGCanvas.tsx`, `VoiceCheck.tsx`, `useWebSocket.ts`)
- Chrome extension (`content.js`, `manifest.json`)
- Generating the `.contract.md` files from the story files above — that's a `pdd story` / `pdd fix` step, not hand-authoring
- Two open decisions that must be resolved before the relevant prompts are complete:
  - **Comprehension pass threshold** — the score/rubric a user must hit before a node flips from `seen` to `mastered`; add to `comprehension_check.prompt` once decided
  - **Extension domain allowlist** — the list of permitted domains the content script observes (e.g. YouTube, GitHub, MDN, dev.to, Stack Overflow); add to `classify_content.prompt` once decided
