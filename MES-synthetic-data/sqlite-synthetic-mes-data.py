import sqlite3
import json
import os
from faker import Faker
import random
from sqlalchemy import create_engine, MetaData, Table, insert, select
from sqlalchemy.orm import sessionmaker

# Initialize Faker
fake = Faker()

# Database settings
db_file = os.path.dirname(__file__) + '/../mes.db'

# Create SQLite database connection
conn = sqlite3.connect(db_file)
conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
cursor = conn.cursor()

# SQL commands to create tables
create_commands = (
    """
    CREATE TABLE IF NOT EXISTS Products (
        ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Description TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Machines (
        MachineID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Type TEXT,
        Status TEXT CHECK (Status IN ('running', 'idle', 'maintenance'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS WorkOrders (
        OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
        ProductID INTEGER NOT NULL,
        Quantity INTEGER NOT NULL CHECK (Quantity > 0),
        StartDate TEXT,
        EndDate TEXT,
        Status TEXT,
        FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Inventory (
        ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Quantity INTEGER NOT NULL CHECK (Quantity >= 0),
        ReorderLevel INTEGER NOT NULL CHECK (ReorderLevel >= 0)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS QualityControl (
        CheckID INTEGER PRIMARY KEY AUTOINCREMENT,
        OrderID INTEGER NOT NULL,
        Date TEXT NOT NULL,
        Result TEXT,
        Comments TEXT,
        FOREIGN KEY (OrderID) REFERENCES WorkOrders(OrderID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Employees (
        EmployeeID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Role TEXT,
        Shift TEXT
    );
    """
)

# Function to execute create commands
def create_tables():
    try:
        for command in create_commands:
            cursor.execute(command)
        conn.commit()
        print("All tables created successfully")
    except Exception as e:
        conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

# Load synthetically generated product information
def load_data_pools(filename):
    with open(filename, 'r', encoding="utf-8") as file:
        data = json.load(file)
    return data

data_pools = load_data_pools(os.path.dirname(__file__) + '/data_pools.json')
inventory_names = data_pools['inventory_names']
product_names = data_pools['product_names']
product_description = data_pools['product_descriptions']
qc_comments = data_pools['qc_comments']

# Insert synthetic data
def insert_data():
    create_tables()  # Create tables first

    # Create database engine
    engine = create_engine(f'sqlite:///{db_file}', echo=False)

    # Reflect the tables from the database
    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Create a Session class bound to the engine
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Products
        products_table = metadata.tables['Products']
        for name, description in zip(product_names, product_description):
            session.execute(insert(products_table).values(Name=name, Description=description))
        session.commit()
        product_ids = fetch_product_ids(session, metadata)

        # Machines
        machines_table = metadata.tables['Machines']
        for i in range(1, 6):  # Generating 5 machines
            session.execute(insert(machines_table).values(Name=f'Machine {i}', Type=random.choice(['Type A', 'Type B', 'Type C']), Status=random.choice(['running', 'idle', 'maintenance'])))
        session.commit()

        # Inventory
        inventory_table = metadata.tables['Inventory']
        for name in inventory_names:
            session.execute(insert(inventory_table).values(Name=name, Quantity=random.randint(0, 1000), ReorderLevel=random.randint(10, 100)))
        session.commit()

        # Work Orders
        work_orders_table = metadata.tables['WorkOrders']
        for _ in range(20):  # 20 work orders
            product_id = random.choice(product_ids)
            session.execute(insert(work_orders_table).values(
                ProductID=product_id,
                Quantity=random.randint(1, 100),
                StartDate=fake.date_between(start_date='-1y', end_date='today').isoformat(),
                EndDate=fake.date_between(start_date='today', end_date='+1y').isoformat(),
                Status=random.choice(['pending', 'in progress', 'completed', 'cancelled'])
            ))
        session.commit()
        order_ids = fetch_order_ids(session, metadata)

        # Employees
        employees_table = metadata.tables['Employees']
        for _ in range(10):  # 10 employees
            session.execute(insert(employees_table).values(
                Name=fake.name(),
                Role=random.choice(['Operator', 'Technician', 'Manager']),
                Shift=random.choice(['morning', 'evening', 'night'])
            ))
        session.commit()

        # Quality Control
        quality_control_table = metadata.tables['QualityControl']
        for _ in range(20):
            session.execute(insert(quality_control_table).values(
                OrderID=random.choice(order_ids),
                Date=fake.date_between(start_date='-1y', end_date='today').isoformat(),
                Result=random.choice(['pass', 'fail', 'rework']),
                Comments=random.choice(qc_comments)
            ))
        session.commit()

    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")
    finally:
        session.close()

# Helper functions for fetching IDs
def fetch_product_ids(session, metadata):
    products_table = metadata.tables['Products']
    return [id[0] for id in session.execute(select(products_table.c.ProductID)).fetchall()]

def fetch_order_ids(session, metadata):
    work_orders_table = metadata.tables['WorkOrders']
    return [id[0] for id in session.execute(select(work_orders_table.c.OrderID)).fetchall()]

if __name__ == '__main__':
    insert_data()
    print("Data insertion complete.")