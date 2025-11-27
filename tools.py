import sqlite3
import pandas as pd
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# Initialize a mock database for disaster resources
def init_db():
    conn = sqlite3.connect('resq_link.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS incidents
                 (id INTEGER PRIMARY KEY, severity TEXT, location TEXT, needs TEXT, status TEXT)''')
    
    # FIX: Added 'PRIMARY KEY' to 'item' so we don't get duplicates
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (item TEXT PRIMARY KEY, quantity INTEGER, location TEXT)''')
    
    # Seed data (INSERT OR IGNORE now works because of the PRIMARY KEY)
    c.execute("INSERT OR IGNORE INTO inventory (item, quantity, location) VALUES ('Water Packs', 50, 'Shelter A')")
    c.execute("INSERT OR IGNORE INTO inventory (item, quantity, location) VALUES ('First Aid Kits', 20, 'Shelter B')")
    
    conn.commit()
    conn.close()

# Run initialization
init_db()

@tool
def log_incident(severity: str, location: str, needs: str):
    """Logs a new incident into the central database. Use this when a user reports an emergency."""
    conn = sqlite3.connect('resq_link.db')
    c = conn.cursor()
    c.execute("INSERT INTO incidents (severity, location, needs, status) VALUES (?, ?, ?, 'OPEN')", 
              (severity, location, needs))
    conn.commit()
    incident_id = c.lastrowid
    conn.close()
    return f"Incident logged successfully. ID: {incident_id}. Dispatching protocols initiated."

@tool
def check_inventory(item_query: str):
    """Checks available relief supplies in the database."""
    conn = sqlite3.connect('resq_link.db')
    # Use parameterized query for safety
    query = "SELECT * FROM inventory WHERE item LIKE ?"
    params = (f'%{item_query}%',)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        return "No specific inventory found matching that request."
    
    # Returns a markdown table string
    return df.to_markdown(index=False)

@tool
def search_shelters(location: str):
    """Uses internet search to find emergency shelters near a location."""
    search = DuckDuckGoSearchRun()
    return search.run(f"emergency shelters near {location} disaster relief")

# Export toolkit list
triage_tools = [log_incident]
logistics_tools = [check_inventory, search_shelters]
medical_tools = []