from db import connect


def main():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT @@VERSION")
    row = cur.fetchone()
    print(row[0])
    conn.close()


if __name__ == "__main__":
    main()
