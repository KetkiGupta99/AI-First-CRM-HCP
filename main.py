from fastapi import FastAPI
from pydantic import BaseModel
from backend.langgraph_agent import agent
import traceback
app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    interaction: dict | None = None
try:

   # @app.post("/chat")
    async def chat(req: ChatRequest):
        state = {
            "input": "req.message",
            "interaction": req.interaction or {}
            #"input1": "Hello"
        }

        result = await agent.ainvoke(state)
        return result["interaction"]
except:
    traceback.print_exc()
# # if __name__ == "__main__":
# #     agent()

# from backend.langgraph_agent import agent

# result = agent.invoke({"input": "Explain LangGraph simply"})
# print(result["output"])
