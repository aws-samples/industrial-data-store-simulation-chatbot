import psycopg2
import json
import os

# Database connection settings
with open(os.path.dirname(__file__)+'/../postgres_creds.json', 'r', encoding="utf-8") as file:
    creds = json.load(file)

conn_str = "postgresql://{user}:{pwd}@{host}:{port}/{db_name}".format(**creds)

# SQL commands to create tables
create_commands = (
    """
    CREATE TABLE IF NOT EXISTS Products (
        ProductID SERIAL PRIMARY KEY,
        Name VARCHAR(255) NOT NULL,
        Description TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Machines (
        MachineID SERIAL PRIMARY KEY,
        Name VARCHAR(255) NOT NULL,
        Type VARCHAR(100),
        Status VARCHAR(50) CHECK (Status IN ('running', 'idle', 'maintenance'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS WorkOrders (
        OrderID SERIAL PRIMARY KEY,
        ProductID INT NOT NULL,
        Quantity INT NOT NULL CHECK (Quantity > 0),
        StartDate DATE,
        EndDate DATE,
        Status VARCHAR(50),
        FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Inventory (
        ItemID SERIAL PRIMARY KEY,
        Name VARCHAR(255) NOT NULL,
        Quantity INT NOT NULL CHECK (Quantity >= 0),
        ReorderLevel INT NOT NULL CHECK (ReorderLevel >= 0)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS QualityControl (
        CheckID SERIAL PRIMARY KEY,
        OrderID INT NOT NULL,
        Date DATE NOT NULL,
        Result VARCHAR(50),
        Comments TEXT,
        FOREIGN KEY (OrderID) REFERENCES WorkOrders(OrderID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Employees (
        EmployeeID SERIAL PRIMARY KEY,
        Name VARCHAR(255) NOT NULL,
        Role VARCHAR(100),
        Shift VARCHAR(50)
    );
    """
)

# Function to execute create commands
def create_tables():
    # Connect to your PostgreSQL database
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    try:
        for command in create_commands:
            cursor.execute(command)
        conn.commit()  # Commit after all commands are successfully executed
        print("All tables created successfully")
    except Exception as e:
        conn.rollback()  # Rollback in case of any error
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_tables()
