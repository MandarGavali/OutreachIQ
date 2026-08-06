from app.agent.agent_core import agent

response = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": """
Generate an outreach message.

Profile:

John Doe

AI Engineer

Working on LangGraph and RAG systems.

Recently posted about AI agents.

Product:
AI-powered outreach assistant.
"""
            }
        ]
    }
)

print(response["messages"][-1].content)