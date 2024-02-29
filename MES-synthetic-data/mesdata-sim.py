from faker import Faker
import random
import json
import os
from sqlalchemy import create_engine, MetaData, insert, select
from sqlalchemy.orm import sessionmaker

# Initialize Faker
fake = Faker()

# Database connection settings
with open(os.path.dirname(__file__)+'/../postgres_creds.json', 'r', encoding="utf-8") as file:
    creds = json.load(file)

conn_str = "postgresql://{user}:{pwd}@{host}:{port}/{db_name}".format(**creds)

# Create database engine
engine = create_engine(conn_str)

# Reflect the tables from the database
metadata = MetaData()
metadata.reflect(bind=engine)

# Create a Session class bound to the engine
Session = sessionmaker(bind=engine)

# Load synthetically generated product information
def load_data_pools(filename):
    with open(filename, 'r', encoding="utf-8") as file:
        data = json.load(file)
    return data

data_pools = load_data_pools(os.path.dirname(__file__)+'/data_pools.json')
inventory_names = data_pools['inventory_names']
product_names = data_pools['product_names']
product_description = data_pools['product_descriptions']
qc_comments = data_pools['qc_comments']

# Insert synthetic data
def fetch_product_ids(session):
    products_table = metadata.tables['products']
    return [id[0] for id in session.execute(select(products_table.c.productid)).fetchall()]

def fetch_order_ids(session):
    work_orders_table = metadata.tables['workorders']
    return [id[0] for id in session.execute(select(work_orders_table.c.orderid)).fetchall()]

def insert_data():
    session = Session()
    try:
        # Products
        products_table = metadata.tables['products']
        for name, description in zip(product_names, product_description):
            session.execute(insert(products_table).values(name=name, description=description))
        session.commit()
        product_ids = fetch_product_ids(session)

        # Machines
        machines_table = metadata.tables['machines']
        for i in range(1, 6):  # Generating 5 machines
            session.execute(insert(machines_table).values(name=f'Machine {i}', type=random.choice(['Type A', 'Type B', 'Type C']), status=random.choice(['running', 'idle', 'maintenance'])))
        session.commit()

        # Inventory
        inventory_table = metadata.tables['inventory']
        for name in inventory_names:
            session.execute(insert(inventory_table).values(name=name, quantity=random.randint(0, 1000), reorderlevel=random.randint(10, 100)))
        session.commit()

        # Work Orders
        work_orders_table = metadata.tables['workorders']
        for _ in range(20):  # 20 work orders
            product_id = random.choice(product_ids)
            session.execute(insert(work_orders_table).values(
                productid=product_id,
                quantity=random.randint(1, 100),
                startdate=fake.date_between(start_date='-1y', end_date='today'),
                enddate=fake.date_between(start_date='today', end_date='+1y'),
                status=random.choice(['pending', 'in progress', 'completed', 'cancelled'])
            ))
        session.commit()
        order_ids = fetch_order_ids(session) 

        # Employees
        employees_table = metadata.tables['employees']
        for _ in range(10): #10 employees
            session.execute(insert(employees_table).values(
                name=fake.name(),
                role=random.choice(['Operator', 'Technician', 'Manager']),
                shift=random.choice(['morning', 'evening', 'night'])
            ))
        session.commit()

        # Quality Control
        quality_control_table = metadata.tables['qualitycontrol']
        for _ in range(20):
            session.execute(insert(quality_control_table).values(
                orderid=random.choice(order_ids),
                date=fake.date_between(start_date='-1y', end_date='today'),
                result=random.choice(['pass', 'fail', 'rework']),
                comments=random.choice(qc_comments)
            ))
        session.commit()

    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    insert_data()
    print("Data insertion complete.")
