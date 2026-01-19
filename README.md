# AI-First-CRM-HCP

This project implements an **AI-First Customer Relationship Management (CRM)** system tailored for **Healthcare Professionals (HCPs)**. The system allows field representatives to log interactions with HCPs, access a 360° view of past interactions, prepare for meetings, and get AI-driven next-best-action recommendations.  

The project uses a **React + Redux frontend**, **FastAPI backend**, **LangGraph AI agent**, and **Groq LLM** for natural language understanding. Interaction data is stored in **Postgres**.

---
## Tech Stack

- **Frontend:** React, Redux, Bootstrap
- **Backend:** Python, FastAPI
- **AI Agent Framework:** LangGraph
- **LLM:** Groq Gemma2-9b-it / llama-3.3-70b-versatile
- **Database:** Postgres (stores interactions)
- **Styling:** Google Inter font, Bootstrap for responsive design
- **Environment Management:** Python-dotenv
---

##  Features

1. **Log HCP interactions** via chat or structured form.  
2. **Edit Interaction**  allows modification of logged data.  
3. **HCP 360 overview**: engagement, sentiment, past interactions.  
4. **AI Meeting Preparation Assistant**: talking points, likely objections, product highlights, and opening script.  
5. **Automatic database persistence** for all interactions.  
6. Materials shared and samples distributed are automatically extracted and saved.

---

## Features

### 1. Log Interaction
- Log HCP interactions via **structured form** or **conversational chat**.
- Automatically extracts key details: HCP name, topics discussed, sentiment, materials shared, and samples distributed.
- Supports AI suggestions for follow-ups.

### 2. HCP 360 Overview
- Summarizes past interactions in a concise, bullet-point format.
- Shows engagement level, sentiment trend, last interaction highlights, and suggested next actions.

### 3. Meeting Preparation Assistant
- Generates **talking points**, **likely objections**, **product highlights**, and **opening scripts** for upcoming HCP meetings.
- Uses past interaction history for personalized insights.

### 4. Next Best Action (NBA)
- Suggests actionable steps for the field rep based on interaction history, HCP preferences, compliance rules, and product stage.

### 5. AI Tools
The **LangGraph agent** uses the following tools:

| Tool                       | Description                                                                                                     |
|----------------------------|-----------------------------------------------------------------------------------------------------------------|
| **Log Interaction**        | Extracts structured interaction data from user input using LLM. Updates Redux state and optionally saves to DB. |
| **Edit Interaction**       | Allows modification of logged interactions. Ensures only explicitly corrected fields are updated.               |
| **HCP 360 Overview**       | Generates a concise summary of past interactions for a given HCP.                                               |
| **Meeting Prep Assistant** | Provides personalized pre-meeting preparation including talking points and suggested scripts.                   |
| **Next Best Action**       | Recommends follow-ups and actions based on HCP behavior, sentiment, and product lifecycle.                      |

---
## Architecture & Code Flow

### 1. Frontend
- **InteractionForm** component in React logs user input.
- Dispatches `fillInteraction` to Redux for state management.
- Sends input to `/userdata` endpoint for AI extraction and processing.
- Displays:
  - HCP details
  - Interaction summary
  - Materials & Samples
  - AI-suggested follow-ups
  - Meeting prep suggestions
  - Next best actions

### 2. Backend
- **FastAPI** handles API requests from the frontend.
- **LangGraph** manages the interaction flow using nodes:
  - `router_node` → routes to appropriate node (`process_input`, `hcp_360`, `meeting_prep`, `clarification`, `next_best_action`)
  - `llm_extract_or_update` → extracts structured interaction details
  - `hcp_360_tool` → summarizes HCP history
  - `meeting_prep_node` → generates meeting prep content
  - `next_best_action_node` → calculates actionable recommendations
- **PostgresSaver/InMemorySaver** stores conversation checkpoints.
- `save_interaction_to_db` function persists structured interactions (materials, samples, follow-ups) in Postgres.

---

## Database Schema (Postgres)

```sql
CREATE TABLE hcp_interactions (
    id SERIAL PRIMARY KEY,
    hcp_name VARCHAR(255),
    interaction_type VARCHAR(50),
    date DATE,
    time TIME,
    attendees TEXT,
    topics_discussed TEXT,
    sentiment VARCHAR(20),
    outcomes TEXT,
    materials_shared TEXT[],
    samples_distributed TEXT[],
    follow_up_actions TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
