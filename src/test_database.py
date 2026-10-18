from database import engine

try:

    connection = engine.connect()

    print("================================")
    print("MySQL connection successful!")
    print("================================")

    connection.close()

except Exception as error:

    print("================================")
    print("MySQL connection failed!")
    print("================================")

    print(error)