import sqlite3

conn = sqlite3.connect(':memory:')
c = conn.cursor()

c.execute("""CREATE TABLE discordUser (
        userId INTEGER,
        userName TEXT,
        userBirthday TEXT
    )""")

conn.execute("INSERT INTO users VALUES (123, 123)")

conn.commit()
conn.close()
