import streamlit as st
from agents import app_graph
from langchain_core.messages import HumanMessage, AIMessage
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CHECK API KEY FIRST ---
if not os.environ.get("GOOGLE_API_KEY"):
    st.error("⚠️ GOOGLE_API_KEY not found in environment variables!")
    st.info("📝 Create a `.env` file in the project directory with:\n\n`GOOGLE_API_KEY=your_actual_api_key_here`")
    st.stop()

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ResQ-Link | Gemini Interface",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS STYLING (The Magic Section) ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&display=swap');
    
    /* GLOBAL THEME */
    .stApp {
        background-color: #0E0E0E;
        font-family: 'Outfit', sans-serif;
        color: #ffffff;
    }
    
    /* --- ANIMATION DEFINITIONS --- */
    @keyframes gemini-line-flow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes gemini-flow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* --- INPUT BOX STYLING --- */
    div[data-testid="stChatInput"] {
        background-color: transparent !important;
    }
    
    div[data-testid="stChatInput"] > div {
        background-color: #1e1f20 !important; 
        border: 1px solid #333; 
        border-radius: 24px !important; 
        color: #fff !important;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    div[data-testid="stChatInput"] > div::after {
        content: "";
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #4285F4, #DB4437, #F4B400, #0F9D58);
        background-size: 200% 200%;
        animation: gemini-line-flow 4s linear infinite;
        opacity: 0.9;
    }
    
    textarea[data-testid="stChatInputTextArea"] {
        color: #ffffff !important;
        caret-color: #4285F4;
    }

    /* --- CHAT BUBBLES --- */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 20px;
        padding-bottom: 50px;
    }
    
    .user-message {
        align-self: flex-end;
        background: linear-gradient(270deg, #1c4b96, #4285F4, #8ab4f8);
        background-size: 200% 200%;
        animation: gemini-flow 6s ease infinite;
        color: white;
        padding: 14px 20px;
        border-radius: 24px 24px 4px 24px;
        max-width: 70%;
        text-align: right;
        margin-left: auto;
        box-shadow: 0 4px 15px rgba(66, 133, 244, 0.2);
        display: block;
        width: fit-content;
    }
    
    .agent-message {
        align-self: flex-start;
        position: relative;
        background: #1e1f20;
        color: #e3e3e3;
        padding: 14px 20px;
        border-radius: 24px 24px 24px 4px;
        max-width: 75%;
        text-align: left;
        margin-right: auto;
        display: block;
        width: fit-content;
        border: 2px solid transparent;
        background-clip: padding-box;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .agent-message::before {
        content: "";
        position: absolute;
        top: -2px; bottom: -2px; left: -2px; right: -2px;
        z-index: -1;
        border-radius: 26px 26px 26px 6px;
        background: linear-gradient(45deg, #4285F4, #DB4437, #F4B400, #0F9D58);
        background-size: 300% 300%;
        animation: gemini-line-flow 4s linear infinite;
    }

    /* --- DASHBOARD CARDS --- */
    .dashboard-card {
        background: #1e1f20;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        text-align: center;
        transition: all 0.3s ease;
    }
    .dashboard-card:hover {
        border-color: #4285F4;
        transform: translateY(-2px);
    }
    .card-label {
        font-size: 12px;
        color: #9aa0a6;
        letter-spacing: 1px;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    .card-value {
        font-size: 22px;
        font-weight: 600;
        background: -webkit-linear-gradient(0deg, #4285F4, #9b72cb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Sidebar & Footer Cleanup */
    section[data-testid="stSidebar"] {
        background-color: #1e1f20;
        border-right: 1px solid #111;
    }
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='font-size:35px;margin-top:-30px;color: white;'>ResQ-Link</h2>", unsafe_allow_html=True)
    st.caption("Your Disaster Response AI")
    
    st.divider()
    
    if os.environ.get("GOOGLE_API_KEY"):
        st.success("✅ Uplink Online")
    else:
        st.error("❌ Uplink Offline")

    st.markdown("### 🤖 Agent Status")
    st.markdown("""
    <div style="line-height: 2.5;">
    🚨 <b>Triage:</b> <span style="color:#0F9D58">Active</span><br>
    📦 <b>Logistics:</b> <span style="color:#0F9D58">Active</span><br>
    🚑 <b>Medical:</b> <span style="color:#0F9D58">Active</span><br>
    🦹 <b>Supervisor:</b> <span style="color:#0F9D58">Active</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if st.button("🔄 Reboot System", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- 4. MAIN HEADER ---
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 20px; margin-top: -50px; font-size: 3rem;'>
        <span style='background: linear-gradient(90deg, #4285F4, #DB4437, #F4B400, #0F9D58); 
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            ResQ-Link
        </span> <span style='font-size: 1.5rem; color: #888;'>| Disaster Response AI</span>
    </h1>
""", unsafe_allow_html=True)

# --- 5. DASHBOARD METRICS ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""
    <div class="dashboard-card">
        <div class="card-label">SYSTEM STATUS</div>
        <div class="card-value">ONLINE</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="dashboard-card">
        <div class="card-label">ACTIVE NODES</div>
        <div class="card-value">4</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="dashboard-card">
        <div class="card-label">DATABASE</div>
        <div class="card-value">SYNCED</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
    <div class="dashboard-card">
        <div class="card-label">INTELLIGENCE</div>
        <div class="card-value">GEMINI</div>
    </div>
    """, unsafe_allow_html=True)

st.write("") 

# --- 6. HELPER FUNCTION ---
def extract_text_content(content):
    """Safely extract text from AIMessage content (handles list or string)."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
        return " ".join(text_parts)
    return str(content)

# --- 7. CHAT DISPLAY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            st.markdown(
                f'<div class="user-message">{msg.content}</div>',
                unsafe_allow_html=True
            )
        elif isinstance(msg, AIMessage):
            content = extract_text_content(msg.content)
            
            # Colorize agent names
            content = content.replace("**Triage**", "<strong style='color:#DB4437'>Triage</strong>")
            content = content.replace("**Logistics**", "<strong style='color:#F4B400'>Logistics</strong>")
            content = content.replace("**Medical**", "<strong style='color:#4285F4'>Medical</strong>")
            content = content.replace("**Supervisor**", "<strong style='color:#4285F4'>Supervisor</strong>")
            
            st.markdown(
                f'<div class="agent-message">{content}</div>',
                unsafe_allow_html=True
            )

# --- 8. USER INPUT & EXECUTION ---
user_input = st.chat_input("ResQ-Link is waiting for your message...")

if user_input:
    # Append user message
    st.session_state.messages.append(HumanMessage(content=user_input))
    
    # Display user message
    with chat_placeholder:
        st.markdown(
            f'<div class="user-message">{user_input}</div>',
            unsafe_allow_html=True
        )

    # Process with AI
    try:
        with st.spinner("✨ ResQ-Link is thinking..."):
            inputs = {"messages": st.session_state.messages}
            
            final_response_text = ""
            iteration_count = 0
            max_iterations = 10
            
            # Stream graph execution
            for output in app_graph.stream(inputs):
                iteration_count += 1
                if iteration_count > max_iterations:
                    st.warning("⚠️ Max iterations reached. Stopping to prevent infinite loop.")
                    break
                
                for key, value in output.items():
                    if key == "Supervisor": 
                        continue
                    
                    if 'messages' in value and value['messages']:
                        last_msg = value['messages'][-1]
                        
                        # Show tool usage notification
                        if hasattr(last_msg, 'tool_calls') and len(last_msg.tool_calls) > 0:
                            tool_name = last_msg.tool_calls[0]['name']
                            st.toast(f"⚡ {key} is running: {tool_name}", icon="🛠️")
                        
                        # Capture response text
                        if hasattr(last_msg, 'content') and last_msg.content:
                            final_response_text = extract_text_content(last_msg.content)
            
            # Append and display agent response
            if final_response_text:
                st.session_state.messages.append(AIMessage(content=final_response_text))
                st.rerun()
            else:
                st.warning("⚠️ No response generated. Please try again.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("💡 Try rephrasing your message or check your API key.")