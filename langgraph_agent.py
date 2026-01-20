import traceback
from fastapi import FastAPI, Request
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel
from langgraph.checkpoint.memory import InMemorySaver  
from langgraph.graph import StateGraph, END
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq
from typing import Union
from langchain_core.tools import tool
from typing import TypedDict, Optional
from datetime import datetime
import json
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values


DB_URI = os.getenv("DB_URI")

# -------------------- Save Interaction to Postgres --------------------
def save_interaction_to_db(interaction_data):
    """
    Insert a new interaction or update existing one for the same HCP and date.
    """
    try:
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()

        materials = interaction_data.get("materials_shared", [])
        samples = interaction_data.get("samples_distributed", [])
        followups = interaction_data.get("follow_up_actions", [])

        # Check if entry already exists
        cursor.execute(
            """
            SELECT id FROM hcp_interactions
            WHERE hcp_name = %s AND date = %s
            """,
            (interaction_data.get("hcp_name"), interaction_data.get("date"))
        )
        row = cursor.fetchone()
        if row:
            # Update existing
            cursor.execute(
                """
                UPDATE hcp_interactions
                SET interaction_type = %s,
                    time = %s,
                    attendees = %s,
                    topics_discussed = %s,
                    sentiment = %s,
                    outcomes = %s,
                    materials_shared = %s,
                    samples_distributed = %s,
                    follow_up_actions = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    interaction_data.get("interaction_type"),
                    interaction_data.get("time"),
                    interaction_data.get("attendees"),
                    interaction_data.get("topics_discussed"),
                    interaction_data.get("sentiment"),
                    interaction_data.get("outcomes"),
                    materials,
                    samples,
                    followups,
                    row[0]
                )
            )
        else:
            # Insert new
            cursor.execute(
                """
                INSERT INTO hcp_interactions (
                    hcp_name, interaction_type, date, time, attendees, topics_discussed,
                    sentiment, outcomes, materials_shared, samples_distributed, follow_up_actions
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    interaction_data.get("hcp_name"),
                    interaction_data.get("interaction_type"),
                    interaction_data.get("date"),
                    interaction_data.get("time"),
                    interaction_data.get("attendees"),
                    interaction_data.get("topics_discussed"),
                    interaction_data.get("sentiment"),
                    interaction_data.get("outcomes"),
                    materials,
                    samples,
                    followups
                )
            )

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error saving interaction: {e}")


try:
    load_dotenv()
    GROQ_API_KEY=os.getenv("GROQ_API_KEY")

    llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile"
    )
    app = FastAPI()

    app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

    class User(BaseModel):
        raw_input: str
        session_id: str
 
    class InteractionState(TypedDict):
        raw_input: str
        interaction_data: dict

    class NBARequest(BaseModel):
        hcp_name: str
        interaction_data: dict
        open_followups: Optional[list] = []

    SYSTEM_PROMPT = """
    You are an AI CRM assistant for life sciences field reps.

    Your task:
    1. Extract structured interaction details from the user's text.
    2. If some fields already exist, update ONLY the fields explicitly corrected by the user.
    3. Do NOT overwrite fields unless the user clearly mentions a correction.
    4. It's not necessary to fill all fields - leave missing if not mentioned.
    

    IMPORTANT EXTRACTION RULES:
    - If the user mentions brochures, decks, PDFs, links, emails → add them to `materials_shared`
    - If the user mentions samples, starter packs, units → add them to `samples_distributed`
    - Do NOT put materials or samples inside topics or outcomes.

    DATE EXTRACTION RULES:
    - If user says "today", use current date
    - If user says "yesterday", subtract 1 day from current date
    - If user provides a date in ANY format, convert it to YYYY-MM-DD
    - If no date is mentioned, do NOT invent one


    Fields:
    - hcp_name
    - interaction_type (Meeting / Sample Meeting)
    - date
    - time
    - attendees
    - topics_discussed
    - sentiment (Positive / Neutral / Negative)
    - outcomes
    - follow_up_actions
    - materials_shared: list of materials shared
    - samples_distributed: list of samples given
    - ai_suggestions_follow_ups: List of suggested follow-ups by AI

    Return output strictly as valid JSON.
    """

    def llm_extract_or_update(state: InteractionState):
        existing_data = state.get("interaction_data", {})
        #
        #print("hello")

        prompt = f"""
        Existing interaction data:
        {json.dumps(existing_data, indent=2)}
        User input:"{state['raw_input']}"
        {SYSTEM_PROMPT}
        """
        #print("hellooo")

        response = llm.invoke(prompt)
        #print(response.content)
        #print("1")
        try:
            extracted_data = json.loads(response.content.strip("```json").strip("```"))
            #print("2")

            # Merge updates safely
            updated_data = existing_data.copy()
            #print("3")
            for key, value in extracted_data.items():
                if value not in [None, "", []]:
                    updated_data[key] = value
            #print("4")

            # Default date & time if missing
            # updated_data.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
            date_was_present = "date" in extracted_data

            updated_data = existing_data.copy()
            for key, value in extracted_data.items():
                if value not in [None, "", []]:
                    updated_data[key] = value

            if not date_was_present:
                updated_data["date"] = datetime.now().strftime("%Y-%m-%d")

            updated_data.setdefault("time", datetime.now().strftime("%H:%M"))
        except:
            updated_data = response.content
        
        # Normalize materials & samples
        if "materials_shared" in updated_data:
            updated_data["materials_shared"] = list(set(updated_data["materials_shared"]))

        if "samples_distributed" in updated_data:
            updated_data["samples_distributed"] = list(set(updated_data["samples_distributed"]))

        # --- AI Suggested Follow-ups ---
        if "ai_suggestions_follow_ups" not in updated_data or not updated_data["ai_suggestions_follow_ups"]:
            followup_prompt = f"""
            You are a pharma CRM AI.

            Based on this interaction, suggest 2-3 short follow-up actions.
            Keep each suggestion under 8 words.
            Do NOT add numbering.
            Return ONLY a JSON list.

            Interaction:
            {json.dumps(updated_data, indent=2)}
            """

            followup_response = llm.invoke(followup_prompt)

            try:
                updated_data["ai_suggestions_follow_ups"] = json.loads(
                    followup_response.content.strip("```json").strip("```")
                )
            except:
                updated_data["ai_suggestions_follow_ups"] = []

        return {
            "interaction_data": updated_data
        }
    
    def hcp_360_tool(state: InteractionState):
        user_input = state["raw_input"]

        #  Very simple HCP name extraction (improve later)
        if "dr." in user_input.lower():
            hcp_name = user_input.split("Dr.")[-1].strip().split()[0]
            hcp_name = "Dr. " + hcp_name
        else:
            hcp_name = "Unknown HCP"

        #  Mock interaction history (replace with DB later)
        interaction_history = [
            "Discussed Product X efficacy. Sentiment: Positive.",
            "Shared digital brochure. Follow-up requested.",
            "Answered dosage-related questions."
            ]

        prompt = f"""
        You are a life sciences CRM assistant.
        Generate a SHORT HCP 360 overview with:
        - Engagement level (1 line)
        - Sentiment trend (1 line)
        - Products discussed (comma-separated)
        - Last interaction highlight (1 line)
        - Suggested next action (1 line)

        Use bullet points.
        Avoid paragraphs.

        HCP Name: {hcp_name}
        Interaction History:
        {interaction_history}
        """
        response = llm.invoke(prompt)

        return {
            "interaction_data": {
                "hcp_name": hcp_name,
                "hcp_360_summary": response.content
            }
        }
    
    def meeting_prep_node(state: InteractionState):
        user_input = state["raw_input"]

        # Very simple HCP extraction (reuse later from DB)
        if "dr." in user_input.lower():
            hcp_name = "Dr. " + user_input.lower().split("dr.")[-1].strip().split()[0].capitalize()
        else:
            hcp_name = "HCP"

        # Mock past data (replace with DB later)
        past_interactions = [
            "Last sentiment: Negative due to efficacy concerns",
            "Asked for real-world evidence",
            "Open follow-up: Share new study"
        ]

        prompt = f"""
        You are an AI Meeting Preparation Assistant for a pharma field rep.

        Prepare the rep for an upcoming meeting using the information below.

        HCP: {hcp_name}
        Past Interactions:
        {past_interactions}

        Generate:
        1. Talking Points (3 bullets)
        2. Likely Objections (2 bullets)
        3. Product Highlights (2 bullets)
        4. Suggested Opening Script (2-3 lines)

        Keep responses concise.
        Use bullet points.
        """

        response = llm.invoke(prompt)

        return {
            "interaction_data": {
                "meeting_prep": response.content
            }
        }
 
    def next_best_action_node(state: InteractionState):
        interaction_data = state.get("interaction_data", {})

        interaction = {
            "sentiment": interaction_data.get("sentiment"),
            "product_stage": interaction_data.get("product_stage", "Launch"),
            "days_since_last_contact": interaction_data.get("days_since_last_contact", 10)
        }

        hcp = {
            "preference": interaction_data.get("hcp_preference", "Clinical Data")
        }

        open_followups = interaction_data.get("follow_up_actions", [])

        actions = []

        # --- Compliance guardrail ---
        if interaction["days_since_last_contact"] < 7:
            actions.append({
                "action": "Avoid Contact",
                "reason": "Compliance rule: minimum gap of 7 days"
            })
        else:
            if interaction["sentiment"] == "Positive":
                actions.append({
                    "action": "Schedule Follow-up Visit",
                    "reason": "Positive engagement in last interaction"
                })

            if hcp["preference"] == "Clinical Data":
                actions.append({
                    "action": "Share Clinical Study",
                    "reason": "HCP prefers evidence-based information"
                })

            if interaction["product_stage"] == "Launch":
                actions.append({
                    "action": "Invite to Webinar",
                    "reason": "Product is in launch phase"
                })

            if open_followups:
                actions.append({
                    "action": "Close Open Follow-ups",
                    "reason": f"{len(open_followups)} pending follow-ups"
                })

        return {
            "interaction_data": {
                **interaction_data,
                "next_best_actions": actions
            }
        }
 
    checkpointer = InMemorySaver()  

    def router_condition(state: InteractionState):
        text = state["raw_input"].lower()

        if "prepare me for meeting" in text or "meeting prep" in text:
            return "meeting_prep"

        # Ambiguous input - clarification
        if text.startswith("dr") and len(text.split()) <= 2:
            return "clarification"

        # Explicit HCP 360 intent
        if "overview" in text or "summary" in text or "360" in text:
            return "hcp_360"

        return "process_input"

        # if "overview" in text or "summary" in text:
        #     return "hcp_360"
        # else:
        #     return "process_input"

    def clarification_node(state: InteractionState):
        hcp_name = state["raw_input"]

        return {
            "interaction_data": {
                "clarification_required": True,
                "hcp_name": hcp_name,
                "message": f"What would you like to do for {hcp_name}?",
                "options": [
                    "Log a new interaction",
                    "Edit the last interaction",
                    "View HCP 360 overview"
                    ]
                }
            }
    
    def router_node(state: InteractionState):
        return state
    
    # API Endpoints
    
    @app.post("/next-best-action")
    async def next_best_action(request: Request):
        """
        Accept any JSON payload from frontend, pass to next_best_action_node.
        Returns: list of recommended actions.
        """
        try:
            payload = await request.json()  # accept arbitrary JSON
        except Exception as e:
            return {"error": "Invalid JSON", "details": str(e)}

        # Build state for LangGraph node
        state = {
            "raw_input": "trigger next_best_action",  # dummy input
            "interaction_data": payload.get("interaction_data", {})
        }

        # Call your existing node
        result = next_best_action_node(state)

        return result["interaction_data"]["next_best_actions"]

    @app.post("/userdata")
    def read_root(user: User):
        with PostgresSaver.from_conn_string(DB_URI) as checkpointer1:  

            graph = StateGraph(InteractionState)

            # Nodes
            graph.add_node("router", router_node)
            graph.add_node("process_input", llm_extract_or_update)
            graph.add_node("hcp_360", hcp_360_tool)
            graph.add_node("clarification", clarification_node)
            graph.add_node("next_best_action", next_best_action_node)
            graph.add_node("meeting_prep", meeting_prep_node)

            graph.add_edge("process_input", "next_best_action")
            graph.add_edge("next_best_action", END)

            # Routing
            graph.add_conditional_edges(
                "router",
                router_condition,
                {
                    "clarification": "clarification",
                    "hcp_360": "hcp_360",
                    "meeting_prep": "meeting_prep",
                    "process_input": "process_input"
                }
            )

            graph.set_entry_point("router")
            graph.set_finish_point("next_best_action")
            graph.set_finish_point("hcp_360")
            graph.set_finish_point("clarification")
            graph.set_finish_point("meeting_prep")


            interaction_graph = graph.compile(checkpointer=checkpointer)

            # state = {
            #     "raw_input": "Yesterday, I met with Dr. Smith and discussed product X efficency. The sentiment was positive and I shared the brochures \n\n today date: 18/1/25",
            #     "interaction_data": {}
            # }
            result = interaction_graph.invoke({"raw_input":user.raw_input},
                                              config={"configurable": {"thread_id": user.session_id}})
            interaction_data = result["interaction_data"]

            # Save interaction to Postgres if HCP name exists
            if "hcp_name" in interaction_data:
                save_interaction_to_db(interaction_data)

        return json.dumps(result["interaction_data"], indent=2)
    

except:
    print(traceback.format_exc())
