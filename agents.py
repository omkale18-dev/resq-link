import os
from dotenv import load_dotenv
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from tools import triage_tools, logistics_tools, medical_tools

# Load environment variables
load_dotenv()

# --- Config ---
# FIX: Changed to valid Gemini model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

# --- State Definition ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    next_agent: str

# --- Helper Function ---
def normalize_message_content(message):
    """Ensures message content is always a string."""
    if not hasattr(message, 'content'):
        return message
    
    content = message.content
    
    # If content is a list, extract text parts
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
            else:
                text_parts.append(str(part))
        message.content = ' '.join(text_parts).strip()
    
    return message


def _ensure_human_message(msgs: List[BaseMessage]) -> List[BaseMessage]:
    """Return messages guaranteed to include at least one HumanMessage.

    Some LLM backends (Gemini) require at least one non-system message. If none
    exists, append a harmless fallback HumanMessage.
    """
    if any(isinstance(m, HumanMessage) for m in msgs):
        return msgs
    return msgs + [HumanMessage(content="Hello, I need assistance.")]

# --- Node Definitions ---

def supervisor_node(state: AgentState):
    """The Router. Decides which specialist handles the next step."""
    history = state.get('messages', [])
    
    # Convert history to text for the router
    history_text = ""
    for msg in history:
        msg = normalize_message_content(msg)
        if isinstance(msg, HumanMessage):
            history_text += f"User: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            history_text += f"AI: {msg.content}\n"
            
    if not history_text:
        history_text = "User: Hello."

    prompt = f"""
    You are the Supervisor of ResQ-Link.
    
    RULES:
    1. If user reports emergency/injury (e.g., "dog bite", "bleeding", "trapped") -> 'Triage'
    2. If user asks about supplies/shelter -> 'Logistics'
    3. If user asks for general medical knowledge (not an active emergency) -> 'Medical'
    4. If goodbye/thanks -> 'FINISH'
    
    HISTORY:
    {history_text}
    
    Output ONLY the next agent name.
    """
    
    try:
        response = llm.invoke(prompt)
        next_agent = response.content.strip().replace("'", "").replace(".", "")
    except Exception as e:
        print(f"Supervisor error: {e}")
        next_agent = "Triage"

    if next_agent not in ["Triage", "Logistics", "Medical", "FINISH"]:
        next_agent = "Triage"
        
    return {"next_agent": next_agent}

def triage_node(state: AgentState):
    """
    Intelligent Triage with Crash Prevention.
    """
    # 1. Get messages from state
    msgs = state.get('messages', [])
    
    # --- SAFETY NET: FIX THE CRASH ---
    if not msgs:
        msgs = [HumanMessage(content="User reported an incident. Please ask for details.")]
    
    # Normalize all messages
    msgs = [normalize_message_content(msg) for msg in msgs]
    
    # Filter out SystemMessages to avoid Gemini API error
    non_system_msgs = [msg for msg in msgs if not isinstance(msg, SystemMessage)]
    
    # Ensure we have at least one non-system message
    if not non_system_msgs:
        non_system_msgs = [HumanMessage(content="User needs assistance. Please respond.")]

    # 2. Bind tools
    tools_llm = llm.bind_tools(triage_tools)
    
    # 3. Create system context as first user message instead of SystemMessage
    system_context = """You are an intelligent Triage Officer for ResQ-Link.
    
    YOUR PRIORITIES:
    1. **Safety First:** If the user is hurt (e.g., "dog bite", "cut", "trapped"), IMMEDIATELY give brief life-saving advice.
    2. **Data Collection:** To send help, you MUST log the incident using the 'log_incident' tool.
    
    HOW TO BEHAVE:
    - If the user report is incomplete, give safety advice FIRST, then ask for the missing details.
    - The 'log_incident' tool requires 3 things: 
      (1) Severity (Critical/Moderate/Minor)
      (2) Location
      (3) Needs (Medical/Rescue)
    
    Be concise and professional."""
    
    # Prepend system context to first message if it's from user
    if non_system_msgs and isinstance(non_system_msgs[0], HumanMessage):
        non_system_msgs[0].content = f"[System Context: {system_context}]\n\nUser: {non_system_msgs[0].content}"
    
    # 4. Invoke LLM
    try:
        msgs_to_send = _ensure_human_message(non_system_msgs)
        response = tools_llm.invoke(msgs_to_send)
        response = normalize_message_content(response)
    except Exception as e:
        print(f"Triage error: {e}")
        response = AIMessage(content=f"⚠️ Triage system encountered an error. Please try rephrasing your request.")
    
    return {"messages": [response]}

def logistics_node(state: AgentState):
    """Finds resources."""
    tools_llm = llm.bind_tools(logistics_tools)
    msgs = state.get('messages', [])
    
    # Normalize messages
    msgs = [normalize_message_content(msg) for msg in msgs]
    
    # Filter out SystemMessages
    non_system_msgs = [msg for msg in msgs if not isinstance(msg, SystemMessage)]
    
    # Ensure we have at least one message
    if not non_system_msgs:
        non_system_msgs = [HumanMessage(content="User needs logistics assistance.")]
    
    # Add system context to first user message
    system_context = """You are the Logistics Coordinator. 
    Your job is to check inventory or find shelters.
    Always be concise. If the database is empty, suggest searching online.
    Be professional and helpful."""
    
    if non_system_msgs and isinstance(non_system_msgs[0], HumanMessage):
        non_system_msgs[0].content = f"[System Context: {system_context}]\n\nUser: {non_system_msgs[0].content}"
    
    try:
        msgs_to_send = _ensure_human_message(non_system_msgs)
        response = tools_llm.invoke(msgs_to_send)
        response = normalize_message_content(response)
    except Exception as e:
        print(f"Logistics error: {e}")
        response = AIMessage(content=f"⚠️ Logistics system encountered an error. Please try again.")
    
    return {"messages": [response]}

def medical_node(state: AgentState):
    """Provides general medical advice."""
    msgs = state.get('messages', [])
    
    # Normalize messages
    msgs = [normalize_message_content(msg) for msg in msgs]
    
    # Filter out SystemMessages
    non_system_msgs = [msg for msg in msgs if not isinstance(msg, SystemMessage)]
    
    # Ensure we have at least one message
    if not non_system_msgs:
        non_system_msgs = [HumanMessage(content="User needs medical advice.")]
    
    # Add system context to first user message
    system_context = """You are a Medical AI Assistant. 
    Provide clear, step-by-step first aid or medical advice.
    Keep it concise and authoritative.
    Always remind users to seek professional medical help for serious conditions."""
    
    if non_system_msgs and isinstance(non_system_msgs[0], HumanMessage):
        non_system_msgs[0].content = f"[System Context: {system_context}]\n\nUser: {non_system_msgs[0].content}"
    
    try:
        msgs_to_send = _ensure_human_message(non_system_msgs)
        response = llm.invoke(msgs_to_send)
        response = normalize_message_content(response)
    except Exception as e:
        print(f"Medical error: {e}")
        response = AIMessage(content=f"⚠️ Medical system encountered an error. Please try again.")
    
    return {"messages": [response]}

# --- Tool Node ---
tool_node = ToolNode(triage_tools + logistics_tools)

# --- Graph Construction ---
workflow = StateGraph(AgentState)

workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Triage", triage_node)
workflow.add_node("Logistics", logistics_node)
workflow.add_node("Medical", medical_node)
workflow.add_node("Tools", tool_node)

workflow.set_entry_point("Supervisor")

workflow.add_conditional_edges(
    "Supervisor",
    lambda x: x['next_agent'],
    {"Triage": "Triage", "Logistics": "Logistics", "Medical": "Medical", "FINISH": END}
)

def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    # If the LLM decided to call a tool, go to "Tools" node
    if hasattr(last_message, 'tool_calls') and len(last_message.tool_calls) > 0:
        return "Tools"
    # Otherwise, stop and show the text response to the user
    return "END"

workflow.add_conditional_edges("Triage", should_continue, {"Tools": "Tools", "END": END})
workflow.add_conditional_edges("Logistics", should_continue, {"Tools": "Tools", "END": END})
workflow.add_edge("Medical", END)
workflow.add_edge("Tools", "Supervisor") # Loop back to supervisor to confirm action

app_graph = workflow.compile()