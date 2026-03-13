import pandas as pd
import sqlite3

def get_mood_data():

    conn = sqlite3.connect("mindlog.db")

    df = pd.read_sql_query("SELECT * FROM entries", conn)

    return df