import sqlite3
import json
import os
from faker import Faker
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, ForeignKey, CheckConstraint
from sqlalchemy.orm import sessionmaker

# Initialize Faker
fake = Faker()

# Database settings
db_file = os.path.dirname(__file__) + '/../mes.db'

# Load data from data_pools.json
def load_data_pools(filename):
    with open(filename, 'r', encoding="utf-8") as file:
        return json.load(file)

data_pools = load_data_pools(os.path.dirname(__file__) + '/data_pools.json')

# Create database engine
engine = create_engine(f'sqlite:///{db_file}', echo=False)
metadata = MetaData()

# Define tables
Products = Table('Products', metadata,
    Column('ProductID', Integer, primary_key=True),
    Column('Name', String, nullable=False),
    Column('Description', String)
)

WorkCenters = Table('WorkCenters', metadata,
    Column('WorkCenterID', Integer, primary_key=True),
    Column('Name', String, nullable=False),
    Column('Description', String),
    Column('Capacity', Float, nullable=False),
    Column('CapacityUOM', String, nullable=False)
)

Machines = Table('Machines', metadata,
    Column('MachineID', Integer, primary_key=True),
    Column('Name', String, nullable=False),
    Column('Type', String),
    Column('WorkCenterID', Integer, ForeignKey('WorkCenters.WorkCenterID')),
    Column('Status', String, CheckConstraint("Status IN ('running', 'idle', 'maintenance')")),
    Column('NominalCapacity', Float, nullable=False),
    Column('CapacityUOM', String, nullable=False),
    Column('SetupTime', Integer, nullable=False),
    Column('EfficiencyFactor', Float, nullable=False),
    Column('MaintenanceFrequency', Integer, nullable=False),
    Column('LastMaintenanceDate', String),
    Column('ProductChangeoverTime', Integer, nullable=False)
)

Inventory = Table('Inventory', metadata,
    Column('ItemID', Integer, primary_key=True),
    Column('Name', String, nullable=False),
    Column('Quantity', Integer, nullable=False),
    Column('ReorderLevel', Integer, nullable=False)
)

Shifts = Table('Shifts', metadata,
    Column('ShiftID', Integer, primary_key=True),
    Column('Name', String, nullable=False),
    Column('StartTime', String, nullable=False),
    Column('EndTime', String, nullable=False)
)

Employees = Table('Employees', metadata,
    Column('EmployeeID', Integer, primary_key=True),
    Column('Name', String, nullable=False),
    Column('Role', String),
    Column('ShiftID', Integer, ForeignKey('Shifts.ShiftID'))
)

WorkOrders = Table('WorkOrders', metadata,
    Column('OrderID', Integer, primary_key=True),
    Column('ProductID', Integer, ForeignKey('Products.ProductID'), nullable=False),
    Column('WorkCenterID', Integer, ForeignKey('WorkCenters.WorkCenterID'), nullable=False),
    Column('MachineID', Integer, ForeignKey('Machines.MachineID'), nullable=False),
    Column('EmployeeID', Integer, ForeignKey('Employees.EmployeeID'), nullable=False),
    Column('Quantity', Integer, nullable=False),
    Column('PlannedStartTime', String, nullable=False),
    Column('PlannedEndTime', String, nullable=False),
    Column('ActualStartTime', String),
    Column('ActualEndTime', String),
    Column('Status', String, CheckConstraint("Status IN ('scheduled', 'in_progress', 'completed', 'cancelled')"))
)

QualityControl = Table('QualityControl', metadata,
    Column('CheckID', Integer, primary_key=True),
    Column('OrderID', Integer, ForeignKey('WorkOrders.OrderID'), nullable=False),
    Column('Date', String, nullable=False),
    Column('Result', String),
    Column('Comments', String)
)

# Create all tables
metadata.create_all(engine)

# Create a Session class bound to the engine
Session = sessionmaker(bind=engine)

def insert_products(session):
    for name, description in zip(data_pools['product_names'], data_pools['product_descriptions']):
        session.execute(Products.insert().values(Name=name, Description=description))
    session.commit()
    return [row[0] for row in session.execute(Products.select().with_only_columns(Products.c.ProductID))]

def insert_work_centers(session):
    for wc in data_pools['work_centers']:
        session.execute(WorkCenters.insert().values(
            Name=wc['name'],
            Description=wc['description'],
            Capacity=wc['capacity'],
            CapacityUOM=wc['capacity_uom']
        ))
    session.commit()
    return [row[0] for row in session.execute(WorkCenters.select().with_only_columns(WorkCenters.c.WorkCenterID))]

def insert_machines(session, work_center_ids):
    for i, machine_type in enumerate(data_pools['machine_types'], start=1):
        capacity_min, capacity_max = data_pools['nominal_capacity'][machine_type]
        session.execute(Machines.insert().values(
            Name=f'Machine {i}',
            Type=machine_type,
            WorkCenterID=random.choice(work_center_ids),
            Status=random.choice(['running', 'idle', 'maintenance']),
            NominalCapacity=round(random.uniform(capacity_min, capacity_max), 2),
            CapacityUOM=data_pools['capacity_uom'][machine_type],
            SetupTime=random.randint(10, 30),
            EfficiencyFactor=round(random.uniform(0.85, 0.95), 2),
            MaintenanceFrequency=random.randint(160, 200),
            LastMaintenanceDate=(datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            ProductChangeoverTime=random.randint(15, 45)
        ))
    session.commit()
    return [row[0] for row in session.execute(Machines.select().with_only_columns(Machines.c.MachineID))]

def insert_inventory(session):
    for name in data_pools['inventory_names']:
        session.execute(Inventory.insert().values(
            Name=name, 
            Quantity=random.randint(0, 1000), 
            ReorderLevel=random.randint(10, 100)
        ))
    session.commit()
    return [row[0] for row in session.execute(Inventory.select().with_only_columns(Inventory.c.ItemID))]

def insert_shifts(session):
    shift_data = [
        ('Morning', '06:00', '14:00'),
        ('Afternoon', '14:00', '22:00'),
        ('Night', '22:00', '06:00')
    ]
    for name, start, end in shift_data:
        session.execute(Shifts.insert().values(Name=name, StartTime=start, EndTime=end))
    session.commit()
    return [row[0] for row in session.execute(Shifts.select().with_only_columns(Shifts.c.ShiftID))]

def insert_employees(session, shift_ids):
    for _ in range(50):  # 50 employees
        session.execute(Employees.insert().values(
            Name=fake.name(),
            Role=random.choice(['Operator', 'Technician', 'Manager', 'Quality Control']),
            ShiftID=random.choice(shift_ids)
        ))
    session.commit()
    return [row[0] for row in session.execute(Employees.select().with_only_columns(Employees.c.EmployeeID))]

def insert_work_orders(session, product_ids, work_center_ids, machine_ids, employee_ids):
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now() + timedelta(days=90)
    now = datetime.now()
    work_order_ids = []

    for _ in range(200):  # 200 work orders
        # Use weighted random choice for status
        status = random.choices(
            ['scheduled', 'in_progress', 'completed', 'cancelled'],
            weights=[15, 20, 60, 5],
            k=1
        )[0]
        
        # Determine planned start based on status
        if status == 'completed':
            planned_start = fake.date_time_between_dates(start_date, now - timedelta(days=1))
        elif status == 'cancelled':
            planned_start = fake.date_time_between_dates(start_date, now)
        elif status == 'in_progress':
            planned_start = fake.date_time_between_dates(now - timedelta(days=7), now)
        else:  # scheduled
            planned_start = fake.date_time_between_dates(now, end_date)
        
        planned_duration = timedelta(hours=random.randint(1, 8))
        planned_end = planned_start + planned_duration
        
        actual_start = actual_end = None

        if status == 'completed':
            actual_start = planned_start + timedelta(minutes=random.randint(-30, 30))
            actual_duration = planned_duration * random.uniform(0.9, 1.1)
            actual_end = min(actual_start + actual_duration, now)
        elif status == 'in_progress':
            actual_start = planned_start + timedelta(minutes=random.randint(-30, 30))
            if actual_start > now:
                actual_start = now - timedelta(hours=random.randint(1, 4))
        
        work_order_id = session.execute(WorkOrders.insert().values(
            ProductID=random.choice(product_ids),
            WorkCenterID=random.choice(work_center_ids),
            MachineID=random.choice(machine_ids),
            EmployeeID=random.choice(employee_ids),
            Quantity=random.randint(10, 1000),
            PlannedStartTime=planned_start.isoformat(),
            PlannedEndTime=planned_end.isoformat(),
            ActualStartTime=actual_start.isoformat() if actual_start else None,
            ActualEndTime=actual_end.isoformat() if actual_end else None,
            Status=status
        )).inserted_primary_key[0]
        work_order_ids.append(work_order_id)

    session.commit()
    return work_order_ids

def insert_quality_control(session, work_order_id, work_center_name):
    qc_comments = data_pools['qc_comments']
    
    if 'Frame Fabrication' in work_center_name:
        comment_category = 'frame'
    elif 'Paint and Finish' in work_center_name:
        comment_category = 'paint'
    elif 'Wheel Production' in work_center_name:
        comment_category = 'wheels'
    elif any(term in work_center_name for term in ['Battery', 'Motor']):
        comment_category = 'electronics'
    elif 'Final Assembly' in work_center_name:
        comment_category = 'final_assembly'
    elif 'Quality Control' in work_center_name:
        comment_category = 'quality_control'
    elif 'Packaging and Shipping' in work_center_name:
        comment_category = 'packaging'
    else:
        comment_category = random.choice(list(qc_comments.keys()))

    session.execute(QualityControl.insert().values(
        OrderID=work_order_id,
        Date=datetime.now().isoformat(),
        Result=random.choice(['pass', 'fail', 'rework']),
        Comments=random.choice(qc_comments[comment_category])
    ))

def insert_data():
    session = Session()
    try:
        product_ids = insert_products(session)
        work_center_ids = insert_work_centers(session)
        machine_ids = insert_machines(session, work_center_ids)
        inventory_ids = insert_inventory(session)
        shift_ids = insert_shifts(session)
        employee_ids = insert_employees(session, shift_ids)
        work_order_ids = insert_work_orders(session, product_ids, work_center_ids, machine_ids, employee_ids)

        # Insert Quality Control records
        work_centers = session.execute(WorkCenters.select()).fetchall()
        work_center_dict = {wc.WorkCenterID: wc.Name for wc in work_centers}

        for order_id in work_order_ids:
            work_order = session.execute(WorkOrders.select().where(WorkOrders.c.OrderID == order_id)).first()
            work_center_name = work_center_dict[work_order.WorkCenterID]
            insert_quality_control(session, order_id, work_center_name)

        session.commit()
        print("Data insertion complete.")
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    insert_data()