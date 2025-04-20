import streamlit as st
import requests
from pandas import DataFrame
import time
import sqlite3
import bcrypt
import base64
import re

# ===== BACKGROUND IMAGE CSS =====
page_bg_img = """
<style>
.stApp {
    background-image: url("https://images.unsplash.com/photo-1597150899069-efb9c8c6010c?q=80&w=3438&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    color: #ffffff;
}
.stTextInput, .stButton>button, .stSelectbox, .stCheckbox, .stCaption, .stTable {
    background-color: rgba(255, 255, 255, 1);
    padding: 10px;
    border-radius: 5px;
}
.stAppHeader {
    background-color: transparent !important;
}
.stSidebar {
    background-color: rgba(255, 255, 255, 1);
}
.stChatMessage {
    background-color: rgba(255, 255, 255, 0.8);
    padding: 10px;
    border-radius: 5px;
}
.stButton>button {
    background-color: #4CAF50;
    color: white;
    border: none;
    width: 100%;
}
.stButton>button:hover {
    background-color: #45a049;
}
.st-emotion-cache-169dgwr {
    background-color: transparent !important;
}
.st-emotion-cache-128upt6 {
    background-color: transparent !important;
}
</style>
"""

# ===== DATABASE SETUP =====
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Initialize database
init_db()

# ===== AUTHENTICATION FUNCTIONS =====
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def register_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                 (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and check_password(password, result[0]):
        return True
    return False

# ===== CONFIG =====
try:
    API_KEY = st.secrets["OPENROUTER_API_KEY"]
except KeyError:
    st.error("API key not found. Please check your secrets.toml file")
    st.stop()

# ===== SESSION STATE INITIALIZATION =====
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", 
        "content": f"I'm here to help you make sustainable fashion choices! Ask me about:\n1. Eco-friendly clothing\n2. Sustainable brands\n3. Tips for caring for clothes\nExample: 'Suggest sustainable outfit ideas for work'\n\nI can also have normal conversations! 🌱",
        "table_data": None
    }]
if "last_response_df" not in st.session_state:
    st.session_state.last_response_df = None
if "deep_search" not in st.session_state:
    st.session_state.deep_search = False
if "previous_messages" not in st.session_state:
    st.session_state.previous_messages = None

# ===== SYSTEM MESSAGE =====
system_message = {
    "role": "system",
    "content": """
    You are an expert sustainable fashion advisor with deep knowledge of eco-friendly trends, materials, and practices. Respond with:
    1. Detailed advice on eco-friendly clothing choices, citing materials like organic cotton, Tencel, or recycled fibers
    2. Evidence-based tips for sustainable shopping, referencing ethical brands, certifications (e.g., Fair Trade, GOTS), or second-hand platforms
    3. Practical suggestions for outfit care to extend garment life and reduce environmental impact (e.g., low-impact washing, repair techniques)
    4. Curated resources or brand recommendations, including recent industry trends or data (e.g., carbon footprint stats, water usage)
    
    Format:
    - Use clear sections with emojis (🌿, 🛍️, 🧼, 📚)
    - Include a markdown table with columns: [Category, Recommendation, Impact]
    - Provide accurate, data-driven advice, citing sources or stats where possible
    - Use simple, engaging language
    - Exclude any rows in the table where any column (e.g., Category, Recommendation, Impact) is empty or contains only whitespace
    - Dont provide any images
    
    You can also have normal conversation but try to advertise your use by replying to their question.

    If anyone asks who made you or about the developers, say:
    "I was created by Aadi Jain."
    and their registration number is:
    - Aadi Jain: 12304968
    """
}

# ===== AUTHENTICATION PAGES =====
def show_login_page():
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title("Login 🌱")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login_user(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.page = "main"
            st.session_state.messages = [{
                "role": "assistant", 
                "content": f"Welcome, {username}! I'm here to help you make sustainable fashion choices! Ask me about:\n1. Eco-friendly clothing\n2. Sustainable brands\n3. Tips for caring for clothes\nExample: 'Suggest sustainable outfit ideas for work'\n\nI can also have normal conversations! 🌱",
                "table_data": None
            }]
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")
    if st.button("Go to Register"):
        st.session_state.page = "register"
        st.rerun()

def show_register_page():
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title("Register 🌱")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Register"):
        if register_user(username, password):
            st.success("Registered successfully! Please log in.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Username already exists")
    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()

# ===== MAIN APP =====
def show_main_app():
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title(f"Welcome, {st.session_state.username}! 🌱 Sustainable Fashion Advisor")

    # Sidebar
    with st.sidebar:
        st.header("About 🌿")
        st.markdown("""
        Welcome to Sustainable Fashion Advisor! 
        
        This app helps you:
        - Discover eco-friendly clothing options
        - Learn sustainable shopping practices
        - Reduce your fashion footprint
        """)
        st.markdown("---")
        st.subheader("User Info 👤")
        st.markdown(f"Logged in as: {st.session_state.username}")
        if st.button("Logout 🚪"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.page = "login"
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "You have logged out. Please log in to continue! 🌿",
                "table_data": None
            }]
            st.session_state.previous_messages = None
            st.rerun()
        st.markdown("---")
        st.subheader("Developer Info 🛠️")
        st.markdown("Name: Aadi Jain  \n*Registration No:* 12304968")
        st.markdown("---")
        st.subheader("Controls 🎛️")
        if st.button("New Chat 🌟", key="new_chat"):
            st.session_state.previous_messages = st.session_state.messages.copy()
            st.session_state.messages = [{
                "role": "assistant", 
                "content": f"New chat started, {st.session_state.username}! Ask me about sustainable fashion or anything else! 🌱",
                "table_data": None
            }]
            st.session_state.last_response_df = None
            st.rerun()
        if st.session_state.previous_messages and st.button("Resume Chat 🔄", key="resume_chat"):
            st.session_state.messages = st.session_state.previous_messages.copy()
            st.session_state.previous_messages = None
            st.rerun()
        if st.button("Clear Chat History 🗑️"):
            st.session_state.previous_messages = st.session_state.messages.copy()
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "Chat history cleared! Ask me about sustainable fashion or anything else! 🌿",
                "table_data": None
            }]
            st.session_state.last_response_df = None
            st.rerun()
        st.checkbox("Enable DeepSearch Mode 🔍", key="deep_search")
        category_filter = st.selectbox(
            "Filter Table by Category 📊",
            options=["All", "Clothing", "Shopping", "Care", "Resources"],
            index=0
        )
        st.markdown("---")
        st.caption("Built with Streamlit and OpenRouter AI 🚀")

    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message.get("table_data") is not None and not message["table_data"].empty:
                df = message["table_data"]
                if category_filter != "All":
                    df = df[df["Category"].str.contains(category_filter, case=False, na=False)]
                if not df.empty:
                    st.table(df)
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask about sustainable fashion or chat... 💬"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt, "table_data": None})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Placeholder for assistant response
        response_placeholder = st.empty()
        
        # Display assistant response
        with response_placeholder.container():
            with st.spinner("Thinking... ⏳"):
                try:
                    # Prepare messages for API
                    api_messages = [
                        {k: v for k, v in msg.items() if k in ["role", "content"]} 
                        for msg in st.session_state.messages
                    ]
                    
                    # Insert system message
                    if len(api_messages) == 1 or api_messages[0]["role"] != "system":
                        api_messages.insert(0, system_message)
                    
                    # Simulate DeepSearch or Think Mode
                    if st.session_state.deep_search:
                        api_messages[-1]["content"] += " (Perform an iterative web search for the latest sustainable fashion trends and data to enhance the response)"
                        time.sleep(2)
                    else:
                        time.sleep(1)
                    
                    # Get AI response
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {API_KEY}",
                            "HTTP-Referer": "http://localhost:8501",
                            "X-Title": "Sustainable Fashion Advisor"
                        },
                        json={
                            "model": "deepseek/deepseek-r1:free",
                            "messages": api_messages,
                        },
                        timeout=30
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    reply = data["choices"][0]["message"]["content"]
                    
                    # Extract table data
                    table_data = []
                    lines = reply.split('\n')
                    in_table = False
                    table_lines = []
                    for line in lines:
                        if '|' in line:
                            if '---' in line:
                                in_table = True
                                table_lines.append(line)
                                continue
                            if in_table and 'Category' not in line:
                                columns = [col.strip() for col in line.split('|') if col.strip()]
                                if len(columns) >= 3 and all(col for col in columns[:3]):
                                    table_data.append({
                                        "Category": columns[0],
                                        "Recommendation": columns[1],
                                        "Impact": columns[2]
                                    })
                                table_lines.append(line)
                        elif in_table:
                            in_table = False
                    
                    # Create DataFrame
                    df = DataFrame(table_data) if table_data else None
                    
                    # Remove table from reply to prevent duplicate display
                    if table_lines:
                        table_pattern = '\n'.join(re.escape(line) for line in table_lines)
                        reply = re.sub(table_pattern, '', reply).strip()
                        # Clean up any extra newlines
                        reply = re.sub(r'\n\s*\n', '\n', reply)
                    
                    # Clear placeholder and display response
                    with st.chat_message("assistant"):
                        if "Eco-Friendly Clothing" in reply:
                            st.image(
                                "https://images.unsplash.com/photo-1512428813834-c177b71b73a2?ixlib=rb-4.0.3&auto=format&fit=crop&w=30&q=80",
                                caption="Plant",
                                width=30
                            )
                        if df is not None and not df.empty:
                            filtered_df = df
                            if category_filter != "All":
                                filtered_df = df[df["Category"].str.contains(category_filter, case=False, na=False)]
                            if not filtered_df.empty:
                                st.table(filtered_df)
                            st.session_state.last_response_df = df
                        else:
                            st.session_state.last_response_df = None
                        
                        st.markdown(reply)
                        
                        # Add Save Recommendations button
                        if st.session_state.last_response_df is not None and not st.session_state.last_response_df.empty:
                            csv = st.session_state.last_response_df.to_csv(index=False)
                            st.download_button(
                                label="Save Recommendations as CSV 📥",
                                data=csv,
                                file_name="sustainable_fashion_recommendations.csv",
                                mime="text/csv"
                            )
                    
                    # Append assistant message to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": reply,
                        "table_data": df
                    })
                
                except requests.exceptions.RequestException as e:
                    with st.chat_message("assistant"):
                        st.error("Network error. Please check your connection and try again. 🚫")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "I'm having trouble connecting. Please try again later.",
                            "table_data": None
                        })
                except Exception as e:
                    with st.chat_message("assistant"):
                        st.error(f"An error occurred: {str(e)}")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "Sorry, I encountered an error. Please rephrase your request.",
                            "table_data": None
                        })

# ===== PAGE ROUTING =====
if not st.session_state.authenticated:
    if st.session_state.page == "login":
        show_login_page()
    elif st.session_state.page == "register":
        show_register_page()
else:
    show_main_app()
