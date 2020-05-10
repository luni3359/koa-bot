import sqlite3

conn = sqlite3.connect(':memory:')
c = conn.cursor()

with open('db/database.sql') as f:
    sql_script = f.read()

c.executescript(sql_script)

c.execute("""CREATE TABLE discordUser (
        userId INTEGER,
        userName TEXT,
        userBirthday TEXT
    )""")

conn.execute("INSERT INTO users VALUES (123, 123)")

conn.commit()
conn.close()
