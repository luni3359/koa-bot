import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()
cursor.execute("""CREATE TABLE users (
        user_id integer
        discord_id integer
    )""")

conn.commit()
conn.close()
