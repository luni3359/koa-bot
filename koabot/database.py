import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()
# cursor.execute("""CREATE TABLE users (
#         user_id integer,
#         discord_id integer
#     )""")
conn.execute("INSERT INTO users VALUES (123, 123)")

conn.commit()
conn.close()
