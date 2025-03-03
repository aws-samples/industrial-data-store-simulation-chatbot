import sqlite3
import json
import os
import logging
from faker import Faker
import random
from datetime import datetime, timedelta
import argparse
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, 
    Float, ForeignKey, CheckConstraint, DateTime, Boolean, Text
)
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MES-Simulator')

# Initialize Faker
fake = Faker()

class MESSimulator:
    """
    Simulator for a Manufacturing Execution System (MES) database
    with synthetic data generation for demonstration purposes.
    """
    
    def __init__(self, config_file, db_file, seed=None):
        """
        Initialize the MES simulator.
        
        Args:
            config_file (str): Path to the configuration JSON file
            db_file (str): Path to the SQLite database file
            seed (int, optional): Random seed for reproducibility
        """
        self.db_file = db_file
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)
        
        # Load data pools configuration
        self.data_pools = self.load_data_pools(config_file)
        
        # Create database engine
        self.engine = create_engine(f'sqlite:///{db_file}', echo=False)
        self.metadata = MetaData()
        
        # Initialize database session
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize database tables
        self.init_tables()
    
    def load_data_pools(self, filename):
        """Load data configuration from JSON file."""
        try:
            with open(filename, 'r', encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading data pools file: {e}")
            raise
    
    def init_tables(self):
        """Initialize database table definitions."""
        # Products table
        self.Products = Table('Products', self.metadata,
            Column('ProductID', Integer, primary_key=True),
            Column('Name', String, nullable=False, unique=True),
            Column('Description', String),
            Column('Category', String),  # Product category
            Column('Cost', Float, nullable=False),
            Column('StandardProcessTime', Float),  # Expected manufacturing time
            Column('IsActive', Boolean, default=True)  # Product status
        )
        
        # Bill of Materials table
        self.BillOfMaterials = Table('BillOfMaterials', self.metadata,
            Column('BOMID', Integer, primary_key=True),
            Column('ProductID', Integer, ForeignKey('Products.ProductID'), nullable=False),
            Column('ComponentID', Integer, ForeignKey('Inventory.ItemID'), nullable=False),
            Column('Quantity', Float, nullable=False),
            Column('ScrapFactor', Float, default=0.0)  # Expected waste percentage
        )
        
        # Suppliers table
        self.Suppliers = Table('Suppliers', self.metadata,
            Column('SupplierID', Integer, primary_key=True),
            Column('Name', String, nullable=False),
            Column('LeadTime', Integer, nullable=False),
            Column('ReliabilityScore', Float),  # Supplier reliability metric
            Column('ContactInfo', String)  # Contact information
        )
        
        # Inventory table
        self.Inventory = Table('Inventory', self.metadata,
            Column('ItemID', Integer, primary_key=True),
            Column('Name', String, nullable=False),
            Column('Category', String),  # Material category
            Column('Quantity', Integer, nullable=False),
            Column('ReorderLevel', Integer, nullable=False),
            Column('SupplierID', Integer, ForeignKey('Suppliers.SupplierID')),
            Column('LeadTime', Integer, nullable=False),
            Column('Cost', Float, nullable=False),
            Column('LotNumber', String),
            Column('Location', String),  # Storage location
            Column('LastReceivedDate', DateTime)  # Last inventory receipt
        )
        
        # Work Centers table
        self.WorkCenters = Table('WorkCenters', self.metadata,
            Column('WorkCenterID', Integer, primary_key=True),
            Column('Name', String, nullable=False),
            Column('Description', String),
            Column('Capacity', Float, nullable=False),
            Column('CapacityUOM', String, nullable=False),
            Column('CostPerHour', Float, nullable=False),
            Column('Location', String),  # Physical location
            Column('IsActive', Boolean, default=True)  # Work center status
        )
        
        # Machines table
        self.Machines = Table('Machines', self.metadata,
            Column('MachineID', Integer, primary_key=True),
            Column('Name', String, nullable=False),
            Column('Type', String),
            Column('WorkCenterID', Integer, ForeignKey('WorkCenters.WorkCenterID')),
            Column('Status', String, CheckConstraint("Status IN ('running', 'idle', 'maintenance', 'breakdown')")),
            Column('NominalCapacity', Float, nullable=False),
            Column('CapacityUOM', String, nullable=False),
            Column('SetupTime', Integer, nullable=False),
            Column('EfficiencyFactor', Float, nullable=False),
            Column('MaintenanceFrequency', Integer, nullable=False),
            Column('LastMaintenanceDate', DateTime),
            Column('NextMaintenanceDate', DateTime),
            Column('ProductChangeoverTime', Integer, nullable=False),
            Column('CostPerHour', Float, nullable=False),
            Column('InstallationDate', DateTime),  # Machine age tracking
            Column('ModelNumber', String)  # Machine model information
        )
        
        # Shifts table
        self.Shifts = Table('Shifts', self.metadata,
            Column('ShiftID', Integer, primary_key=True),
            Column('Name', String, nullable=False),
            Column('StartTime', String, nullable=False),
            Column('EndTime', String, nullable=False),
            Column('Capacity', Float, nullable=False),
            Column('IsWeekend', Boolean, default=False)  # Weekend shift indicator
        )
        
        # Employees table
        self.Employees = Table('Employees', self.metadata,
            Column('EmployeeID', Integer, primary_key=True),
            Column('Name', String, nullable=False),
            Column('Role', String),
            Column('ShiftID', Integer, ForeignKey('Shifts.ShiftID')),
            Column('HourlyRate', Float, nullable=False),
            Column('Skills', String),  # Employee skills/certifications
            Column('HireDate', DateTime)  # Employee tenure
        )
        
        # Work Orders table
        self.WorkOrders = Table('WorkOrders', self.metadata,
            Column('OrderID', Integer, primary_key=True),
            Column('ProductID', Integer, ForeignKey('Products.ProductID'), nullable=False),
            Column('WorkCenterID', Integer, ForeignKey('WorkCenters.WorkCenterID'), nullable=False),
            Column('MachineID', Integer, ForeignKey('Machines.MachineID'), nullable=False),
            Column('EmployeeID', Integer, ForeignKey('Employees.EmployeeID'), nullable=False),
            Column('Quantity', Integer, nullable=False),
            Column('PlannedStartTime', DateTime, nullable=False),
            Column('PlannedEndTime', DateTime, nullable=False),
            Column('ActualStartTime', DateTime),
            Column('ActualEndTime', DateTime),
            Column('Status', String, CheckConstraint("Status IN ('scheduled', 'in_progress', 'completed', 'cancelled')")),
            Column('Priority', Integer, nullable=False),
            Column('LeadTime', Integer, nullable=False),
            Column('LotNumber', String),
            Column('ActualProduction', Integer),  # Actual units produced
            Column('Scrap', Integer, default=0),  # Scrap quantity
            Column('SetupTimeActual', Integer)  # Actual setup time
        )
        
        # Downtime Tracking table
        self.Downtimes = Table('Downtimes', self.metadata,
            Column('DowntimeID', Integer, primary_key=True),
            Column('MachineID', Integer, ForeignKey('Machines.MachineID'), nullable=False),
            Column('OrderID', Integer, ForeignKey('WorkOrders.OrderID')),
            Column('StartTime', DateTime, nullable=False),
            Column('EndTime', DateTime),
            Column('Duration', Integer),  # Minutes
            Column('Reason', String, nullable=False),
            Column('Category', String, nullable=False),
            Column('Description', Text),
            Column('ReportedBy', Integer, ForeignKey('Employees.EmployeeID'))
        )
        
        # Quality Control table
        self.QualityControl = Table('QualityControl', self.metadata,
            Column('CheckID', Integer, primary_key=True),
            Column('OrderID', Integer, ForeignKey('WorkOrders.OrderID'), nullable=False),
            Column('Date', DateTime, nullable=False),
            Column('Result', String),
            Column('Comments', String),
            Column('DefectRate', Float),
            Column('ReworkRate', Float),
            Column('YieldRate', Float),
            Column('InspectorID', Integer, ForeignKey('Employees.EmployeeID'))  # QC inspector
        )
        
        # Defects table for detailed defect tracking
        self.Defects = Table('Defects', self.metadata,
            Column('DefectID', Integer, primary_key=True),
            Column('CheckID', Integer, ForeignKey('QualityControl.CheckID'), nullable=False),
            Column('DefectType', String, nullable=False),
            Column('Severity', Integer),  # 1-5 scale
            Column('Quantity', Integer, default=1),
            Column('Location', String),
            Column('RootCause', String),
            Column('ActionTaken', String)
        )
        
        # Material Consumption table
        self.MaterialConsumption = Table('MaterialConsumption', self.metadata,
            Column('ConsumptionID', Integer, primary_key=True),
            Column('OrderID', Integer, ForeignKey('WorkOrders.OrderID'), nullable=False),
            Column('ItemID', Integer, ForeignKey('Inventory.ItemID'), nullable=False),
            Column('PlannedQuantity', Float, nullable=False),
            Column('ActualQuantity', Float),
            Column('VariancePercent', Float),
            Column('ConsumptionDate', DateTime),
            Column('LotNumber', String)
        )
        
        # OEE Metrics table
        self.OEEMetrics = Table('OEEMetrics', self.metadata,
            Column('MetricID', Integer, primary_key=True),
            Column('MachineID', Integer, ForeignKey('Machines.MachineID'), nullable=False),
            Column('Date', DateTime, nullable=False),
            Column('Availability', Float),  # Percentage
            Column('Performance', Float),  # Percentage
            Column('Quality', Float),  # Percentage
            Column('OEE', Float),  # Overall Equipment Effectiveness
            Column('PlannedProductionTime', Integer),  # Minutes
            Column('ActualProductionTime', Integer),  # Minutes
            Column('Downtime', Integer)  # Minutes
        )
    
    def create_database(self):
        """Create all database tables."""
        try:
            self.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def insert_data(self):
        """Insert synthetic data into all tables."""
        session = self.Session()
        try:
            supplier_ids = self.insert_suppliers(session)
            product_ids = self.insert_products(session)
            inventory_ids = self.insert_inventory(session, supplier_ids)
            self.insert_bill_of_materials(session, product_ids, inventory_ids)
            work_center_ids = self.insert_work_centers(session)
            machine_ids = self.insert_machines(session, work_center_ids)
            shift_ids = self.insert_shifts(session)
            employee_ids = self.insert_employees(session, shift_ids)
            work_order_ids = self.insert_work_orders(session, product_ids, work_center_ids, machine_ids, employee_ids)
            
            # Insert related data for work orders
            self.insert_quality_control_and_defects(session, work_order_ids, employee_ids)
            self.insert_material_consumption(session, work_order_ids, inventory_ids)
            self.insert_downtimes(session, work_order_ids, machine_ids, employee_ids)
            self.insert_oee_metrics(session, machine_ids)
            
            session.commit()
            logger.info("Data insertion complete")
        except Exception as e:
            session.rollback()
            logger.error(f"Error inserting data: {e}")
            raise
        finally:
            session.close()
    
    def insert_suppliers(self, session):
        """Insert supplier data."""
        logger.info("Inserting suppliers")
        supplier_ids = []
        
        for supplier in self.data_pools['suppliers']:
            reliability = round(random.uniform(0.8, 0.99), 2)
            contact_info = f"Contact: {fake.name()}, Email: {fake.email()}, Phone: {fake.phone_number()}"
            
            result = session.execute(self.Suppliers.insert().values(
                Name=supplier['name'],
                LeadTime=supplier['lead_time'],
                ReliabilityScore=reliability,
                ContactInfo=contact_info
            ))
            supplier_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return supplier_ids
    
    def insert_products(self, session):
        """Insert product data."""
        logger.info("Inserting products")
        product_ids = []
        cost_range = self.data_pools['cost_ranges']['products']
        
        product_categories = ["Electric Bikes", "Components", "Accessories", "Spare Parts", "MRO"]
        
        for i, (name, description) in enumerate(zip(self.data_pools['product_names'], self.data_pools['product_descriptions'])):
            # Determine product category
            if "eBike" in name:
                category = "Electric Bikes"
            elif "MRO" in name:
                category = "MRO"
            elif name in ["Battery", "Motor", "Control_Unit", "Motor_Assembly"]:
                category = "Components"
            elif name in ["Bolt", "Washer"]:
                category = "Spare Parts"
            else:
                category = "Accessories"
            
            # Generate standard process time (in hours)
            if category == "Electric Bikes":
                std_process_time = random.uniform(4.0, 8.0)
            elif category == "Components":
                std_process_time = random.uniform(1.0, 3.0)
            else:
                std_process_time = random.uniform(0.5, 1.5)
            
            result = session.execute(self.Products.insert().values(
                Name=name,
                Description=description,
                Category=category,
                Cost=round(random.uniform(cost_range['min'], cost_range['max']), 2),
                StandardProcessTime=round(std_process_time, 2),
                IsActive=random.choices([True, False], weights=[95, 5], k=1)[0]
            ))
            product_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return product_ids
    
    def insert_inventory(self, session, supplier_ids):
        """Insert inventory data."""
        logger.info("Inserting inventory items")
        inventory_ids = []
        cost_range = self.data_pools['cost_ranges']['components']
        lead_time_range = self.data_pools['lead_time_range']
        
        # Material categories
        categories = ["Raw Material", "Electronic Component", "Mechanical Component", "Assembly", "Packaging", "MRO"]
        
        # Storage locations
        locations = ["Warehouse A", "Warehouse B", "Production Floor", "Assembly Area", "External Storage"]
        
        for name in self.data_pools['inventory_names']:
            # Determine category based on item name
            if any(term in name.lower() for term in ["aluminum", "steel", "rubber", "tire"]):
                category = "Raw Material"
            elif any(term in name.lower() for term in ["circuit", "cell", "motor", "electronic", "microcontroller"]):
                category = "Electronic Component"
            elif any(term in name.lower() for term in ["bolt", "bearing", "spring", "cog", "chain"]):
                category = "Mechanical Component"
            elif any(term in name.lower() for term in ["assembly", "bracket", "casing"]):
                category = "Assembly"
            elif "oil" in name.lower() or "fluid" in name.lower():
                category = "MRO"
            else:
                category = random.choice(categories)
            
            # Generate last received date
            last_received = datetime.now() - timedelta(days=random.randint(1, 90))
            
            result = session.execute(self.Inventory.insert().values(
                Name=name,
                Category=category,
                Quantity=random.randint(0, 1000),
                ReorderLevel=random.randint(10, 100),
                SupplierID=random.choice(supplier_ids),
                LeadTime=random.randint(lead_time_range['min'], lead_time_range['max']),
                Cost=round(random.uniform(cost_range['min'], cost_range['max']), 2),
                LotNumber=f"LOT-{fake.uuid4()[:8]}",
                Location=random.choice(locations),
                LastReceivedDate=last_received
            ))
            inventory_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return inventory_ids
    
    def insert_bill_of_materials(self, session, product_ids, inventory_ids):
        """Insert bill of materials data."""
        logger.info("Inserting bill of materials")
        
        for product_id in product_ids:
            # Get product name to make BOM more realistic
            product = session.execute(self.Products.select().where(
                self.Products.c.ProductID == product_id
            )).fetchone()
            
            # Number of components varies by product type
            if product.Category == "Electric Bikes":
                num_components = random.randint(15, 25)
            elif product.Category == "Components":
                num_components = random.randint(5, 10)
            else:
                num_components = random.randint(2, 5)
            
            # Select random components
            components = random.sample(inventory_ids, min(num_components, len(inventory_ids)))
            
            for component_id in components:
                # Quantity varies by component and product
                quantity = random.randint(1, 20)
                
                # Scrap factor - higher for raw materials
                component = session.execute(self.Inventory.select().where(
                    self.Inventory.c.ItemID == component_id
                )).fetchone()
                
                if component.Category == "Raw Material":
                    scrap_factor = round(random.uniform(0.05, 0.15), 2)  # 5-15% scrap
                else:
                    scrap_factor = round(random.uniform(0.0, 0.05), 2)   # 0-5% scrap
                
                session.execute(self.BillOfMaterials.insert().values(
                    ProductID=product_id,
                    ComponentID=component_id,
                    Quantity=quantity,
                    ScrapFactor=scrap_factor
                ))
        
        session.commit()
    
    def insert_work_centers(self, session):
        """Insert work centers data."""
        logger.info("Inserting work centers")
        work_center_ids = []
        cost_range = self.data_pools['cost_ranges']['work_centers']
        
        # Locations
        plant_areas = ["Building A", "Building B", "Main Factory", "North Wing", "South Wing"]
        
        for wc in self.data_pools['work_centers']:
            result = session.execute(self.WorkCenters.insert().values(
                Name=wc['name'],
                Description=wc['description'],
                Capacity=wc['capacity'],
                CapacityUOM=wc['capacity_uom'],
                CostPerHour=round(random.uniform(cost_range['min'], cost_range['max']), 2),
                Location=random.choice(plant_areas),
                IsActive=True
            ))
            work_center_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return work_center_ids
    
    def insert_machines(self, session, work_center_ids):
        """Insert machines data."""
        logger.info("Inserting machines")
        machine_ids = []
        cost_range = self.data_pools['cost_ranges']['machines']
        
        # Machine models by type
        machine_models = {
            "Frame Welding": ["W-1000", "W-2000", "W-3000"],
            "Wheel Assembly": ["WA-500", "WA-750", "WA-1000"],
            "Paint Booth": ["PB-200", "PB-300", "PB-500"],
            "Battery Assembly": ["BA-100", "BA-200", "BA-300"],
            "Motor Assembly": ["MA-500", "MA-750", "MA-1000"],
            "Final Assembly": ["FA-100", "FA-200", "FA-300"],
            "Quality Control": ["QC-500", "QC-750", "QC-1000"],
            "Packaging": ["PK-100", "PK-200", "PK-300"]
        }
        
        for i, machine_type in enumerate(self.data_pools['machine_types'], start=1):
            # Find appropriate work centers for this machine type
            suitable_work_centers = []
            for wc_id in work_center_ids:
                wc = session.execute(self.WorkCenters.select().where(
                    self.WorkCenters.c.WorkCenterID == wc_id
                )).fetchone()
                
                # Match machine types to work centers
                if any(machine_type.lower() in associated.lower() for associated in 
                        next((center['associated_machines'] for center in self.data_pools['work_centers'] 
                              if center['name'] == wc.Name), [])):
                    suitable_work_centers.append(wc_id)
            
            # If no suitable work center, pick random
            if not suitable_work_centers:
                suitable_work_centers = work_center_ids
            
            # Create 1-3 machines of each type
            for j in range(random.randint(1, 3)):
                capacity_min, capacity_max = self.data_pools['nominal_capacity'][machine_type]
                
                # Generate realistic dates
                installation_date = datetime.now() - timedelta(days=random.randint(90, 1000))
                last_maintenance = datetime.now() - timedelta(days=random.randint(1, 60))
                maintenance_frequency = random.randint(160, 200)  # hours
                next_maintenance = last_maintenance + timedelta(hours=maintenance_frequency)
                
                # Machine status weighted toward running
                status = random.choices(
                    ['running', 'idle', 'maintenance', 'breakdown'],
                    weights=[70, 15, 10, 5],
                    k=1
                )[0]
                
                # Lower efficiency for older machines
                days_since_installation = (datetime.now() - installation_date).days
                efficiency_factor = round(max(0.7, 0.98 - (days_since_installation / 10000)), 2)
                
                result = session.execute(self.Machines.insert().values(
                    Name=f'Machine {machine_type[:3]}-{i}{j}',
                    Type=machine_type,
                    WorkCenterID=random.choice(suitable_work_centers),
                    Status=status,
                    NominalCapacity=round(random.uniform(capacity_min, capacity_max), 2),
                    CapacityUOM=self.data_pools['capacity_uom'][machine_type],
                    SetupTime=random.randint(10, 30),
                    EfficiencyFactor=efficiency_factor,
                    MaintenanceFrequency=maintenance_frequency,
                    LastMaintenanceDate=last_maintenance,
                    NextMaintenanceDate=next_maintenance,
                    ProductChangeoverTime=random.randint(15, 45),
                    CostPerHour=round(random.uniform(cost_range['min'], cost_range['max']), 2),
                    InstallationDate=installation_date,
                    ModelNumber=random.choice(machine_models.get(machine_type, ["STD-100"]))
                ))
                machine_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return machine_ids
    
    def insert_shifts(self, session):
        """Insert shifts data."""
        logger.info("Inserting shifts")
        shift_ids = []
        
        shift_data = [
            ('Morning', '06:00', '14:00', 1.0, False),
            ('Afternoon', '14:00', '22:00', 0.9, False),
            ('Night', '22:00', '06:00', 0.8, False),
            ('Weekend Day', '08:00', '20:00', 0.7, True),
            ('Weekend Night', '20:00', '08:00', 0.6, True)
        ]
        
        for name, start, end, capacity, is_weekend in shift_data:
            result = session.execute(self.Shifts.insert().values(
                Name=name,
                StartTime=start,
                EndTime=end,
                Capacity=capacity,
                IsWeekend=is_weekend
            ))
            shift_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return shift_ids
    
    def insert_employees(self, session, shift_ids):
        """Insert employees data."""
        logger.info("Inserting employees")
        employee_ids = []
        rate_range = self.data_pools['employee_hourly_rate_range']
        
        # Define roles and their associated skills
        roles_and_skills = {
            'Operator': [
                'Machine Operation', 'Safety Procedures', 'Quality Inspection',
                'Basic Maintenance', 'Material Handling'
            ],
            'Technician': [
                'Machine Repair', 'Preventative Maintenance', 'Electrical Systems',
                'Mechanical Systems', 'Troubleshooting', 'Calibration'
            ],
            'Quality Control': [
                'Quality Standards', 'Inspection Techniques', 'Statistical Analysis',
                'Documentation', 'Root Cause Analysis', 'Regulatory Compliance'
            ],
            'Manager': [
                'Team Leadership', 'Process Improvement', 'Production Scheduling',
                'Performance Management', 'Safety Management', 'Lean Manufacturing'
            ],
            'Engineer': [
                'Process Design', 'Technical Documentation', 'Problem Solving',
                'CAD/CAM Systems', 'Automation', 'Industrial Engineering'
            ]
        }
        
        # Distribution of roles
        role_weights = {
            'Operator': 60,
            'Technician': 20,
            'Quality Control': 10,
            'Manager': 5,
            'Engineer': 5
        }
        
        for _ in range(50):  # 50 employees
            # Select role based on weight
            role = random.choices(
                list(role_weights.keys()),
                weights=list(role_weights.values()),
                k=1
            )[0]
            
            # Select 2-4 skills for this employee
            skills = random.sample(roles_and_skills[role], random.randint(2, min(4, len(roles_and_skills[role]))))
            skills_str = ', '.join(skills)
            
            # Generate hire date (weighted toward recent hires but some veterans)
            days_employed = random.choices(
                [random.randint(1, 90), random.randint(91, 365), random.randint(366, 1825)],
                weights=[20, 50, 30],
                k=1
            )[0]
            hire_date = datetime.now() - timedelta(days=days_employed)
            
            # Hourly rate varies by role and tenure
            base_rate = {
                'Operator': rate_range['min'],
                'Technician': rate_range['min'] + 5,
                'Quality Control': rate_range['min'] + 8,
                'Manager': rate_range['min'] + 15,
                'Engineer': rate_range['min'] + 12
            }
            
            # Tenure bonus (up to 20% for 5 years)
            tenure_bonus = min(days_employed / 1825 * 0.2, 0.2)
            hourly_rate = round(base_rate[role] * (1 + tenure_bonus), 2)
            
            result = session.execute(self.Employees.insert().values(
                Name=fake.name(),
                Role=role,
                ShiftID=random.choice(shift_ids),
                HourlyRate=hourly_rate,
                Skills=skills_str,
                HireDate=hire_date
            ))
            employee_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return employee_ids
    
    def insert_work_orders(self, session, product_ids, work_center_ids, machine_ids, employee_ids):
        """Insert work orders data."""
        logger.info("Inserting work orders")
        work_order_ids = []
        
        # Time period for work orders
        start_date = datetime.now() - timedelta(days=90)
        end_date = datetime.now() + timedelta(days=90)
        now = datetime.now()
        
        # Status weights
        status_weights = {
            'scheduled': 15,
            'in_progress': 20,
            'completed': 60,
            'cancelled': 5
        }
        
        for _ in range(200):  # 200 work orders
            # Select random product
            product_id = random.choice(product_ids)
            product = session.execute(self.Products.select().where(
                self.Products.c.ProductID == product_id
            )).fetchone()
            
            # Quantity based on product category
            if product.Category == "Electric Bikes":
                quantity = random.randint(10, 100)
            elif product.Category == "Components":
                quantity = random.randint(50, 500)
            else:
                quantity = random.randint(100, 1000)
            
            # Status based on weights
            status = random.choices(
                list(status_weights.keys()),
                weights=list(status_weights.values()),
                k=1
            )[0]
            
            # Dates based on status
            if status == 'completed':
                planned_start = fake.date_time_between_dates(start_date, now - timedelta(days=1))
            elif status == 'cancelled':
                planned_start = fake.date_time_between_dates(start_date, now)
            elif status == 'in_progress':
                planned_start = fake.date_time_between_dates(now - timedelta(days=7), now)
            else:  # scheduled
                planned_start = fake.date_time_between_dates(now, end_date)
            
            # Use product's standard process time for planning
            planned_duration = timedelta(hours=product.StandardProcessTime * quantity / 100)  # Scaled by quantity
            planned_end = planned_start + planned_duration
            
            # Actual times based on status
            actual_start = actual_end = None
            actual_production = None
            scrap = 0
            setup_time_actual = None
            
            if status == 'completed':
                # Actual start time varies from plan
                actual_start = planned_start + timedelta(minutes=random.randint(-30, 30))
                
                # Efficiency factor affects actual duration (80-120% of planned)
                efficiency = random.uniform(0.8, 1.2)
                actual_duration = planned_duration * efficiency
                actual_end = actual_start + actual_duration
                
                # Actual production and scrap
                scrap_rate = random.uniform(0.0, 0.05)  # 0-5% scrap
                scrap = int(quantity * scrap_rate)
                actual_production = quantity - scrap
                
                # Setup time variation
                setup_time_actual = random.randint(10, 40)  # Minutes
                
            elif status == 'in_progress':
                actual_start = planned_start + timedelta(minutes=random.randint(-30, 30))
                if actual_start > now:
                    actual_start = now - timedelta(hours=random.randint(1, 4))
                
                # Partial production for in-progress orders
                progress = random.uniform(0.1, 0.9)  # 10-90% complete
                actual_production = int(quantity * progress)
                scrap = int(actual_production * random.uniform(0.0, 0.05))
                
                # Setup time for in-progress
                setup_time_actual = random.randint(10, 40)  # Minutes
            
            # Find suitable machine and work center
            if product.Category == "Electric Bikes":
                suitable_machine_types = ["Final Assembly"]
            elif "Battery" in product.Name:
                suitable_machine_types = ["Battery Assembly"]
            elif "Motor" in product.Name:
                suitable_machine_types = ["Motor Assembly"]
            elif "Wheel" in product.Name:
                suitable_machine_types = ["Wheel Assembly"]
            elif "Frame" in product.Name:
                suitable_machine_types = ["Frame Welding"]
            else:
                suitable_machine_types = self.data_pools['machine_types']
            
            # Find machines of suitable type
            suitable_machines = []
            for machine_id in machine_ids:
                machine = session.execute(self.Machines.select().where(
                    self.Machines.c.MachineID == machine_id
                )).fetchone()
                
                if machine.Type in suitable_machine_types:
                    suitable_machines.append(machine)
            
            if not suitable_machines:
                # Fallback to any machine
                machine = random.choice(session.execute(self.Machines.select()).fetchall())
            else:
                machine = random.choice(suitable_machines)
            
            # Get work center for the machine
            work_center = session.execute(self.WorkCenters.select().where(
                self.WorkCenters.c.WorkCenterID == machine.WorkCenterID
            )).fetchone()
            
            # Find suitable employees (operators)
            operators = session.execute(self.Employees.select().where(
                self.Employees.c.Role == 'Operator'
            )).fetchall()
            
            if not operators:
                # Fallback to any employee
                employee_id = random.choice(employee_ids)
            else:
                employee_id = random.choice(operators).EmployeeID
            
            # Insert work order
            result = session.execute(self.WorkOrders.insert().values(
                ProductID=product_id,
                WorkCenterID=work_center.WorkCenterID,
                MachineID=machine.MachineID,
                EmployeeID=employee_id,
                Quantity=quantity,
                PlannedStartTime=planned_start,
                PlannedEndTime=planned_end,
                ActualStartTime=actual_start,
                ActualEndTime=actual_end,
                Status=status,
                Priority=random.randint(1, 5),  # Priority from 1 (lowest) to 5 (highest)
                LeadTime=random.randint(24, 168),  # Lead time between 1 and 7 days (in hours)
                LotNumber=f"LOT-{fake.uuid4()[:8]}",  # Generate a random lot number
                ActualProduction=actual_production,
                Scrap=scrap,
                SetupTimeActual=setup_time_actual
            ))
            work_order_ids.append(result.inserted_primary_key[0])
        
        session.commit()
        return work_order_ids
    
    def insert_quality_control_and_defects(self, session, work_order_ids, employee_ids):
        """Insert quality control and defect data."""
        logger.info("Inserting quality control and defects data")
        
        # Get QC employees
        qc_employees = session.execute(self.Employees.select().where(
            self.Employees.c.Role == 'Quality Control'
        )).fetchall()
        
        if not qc_employees:
            qc_employees = session.execute(self.Employees.select()).fetchall()
        
        # Defect types by category
        defect_types = {
            'frame': ["Weld Failure", "Misalignment", "Surface Defect", "Structural Weakness", "Dimension Error"],
            'paint': ["Color Mismatch", "Uneven Coating", "Drips", "Orange Peel", "Poor Adhesion"],
            'wheels': ["Out of True", "Spoke Tension", "Hub Play", "Bead Seating Issue", "Valve Stem Defect"],
            'drivetrain': ["Chain Misalignment", "Gear Indexing", "Crank Play", "Bottom Bracket Noise", "Derailleur Adjustment"],
            'brakes': ["Uneven Braking", "Lever Play", "Hydraulic Leak", "Rotor Warp", "Pad Wear"],
            'electronics': ["Battery Capacity", "Connection Issue", "Display Fault", "Sensor Malfunction", "Motor Output"],
            'final_assembly': ["Missing Component", "Loose Fastener", "Cable Routing", "Adjustment Error", "Interface Fit"],
            'general': ["Cosmetic Damage", "Noise", "Vibration", "Documentation Error", "Packaging Damage"]
        }
        
        # For each completed or in-progress work order, create QC records
        for order_id in work_order_ids:
            work_order = session.execute(self.WorkOrders.select().where(
                self.WorkOrders.c.OrderID == order_id
            )).fetchone()
            
            # Only create QC records for completed or in-progress orders
            if work_order.Status not in ['completed', 'in_progress']:
                continue
            
            # Get product info
            product = session.execute(self.Products.select().where(
                self.Products.c.ProductID == work_order.ProductID
            )).fetchone()
            
            # Get work center info
            work_center = session.execute(self.WorkCenters.select().where(
                self.WorkCenters.c.WorkCenterID == work_order.WorkCenterID
            )).fetchone()
            
            # Determine defect category based on work center and product
            if "Frame" in work_center.Name:
                defect_category = 'frame'
            elif "Paint" in work_center.Name:
                defect_category = 'paint'
            elif "Wheel" in work_center.Name:
                defect_category = 'wheels'
            elif any(term in work_center.Name for term in ['Battery', 'Motor']):
                defect_category = 'electronics'
            elif "Final Assembly" in work_center.Name:
                defect_category = 'final_assembly'
            elif "Quality Control" in work_center.Name:
                defect_category = random.choice(list(defect_types.keys()))
            else:
                defect_category = 'general'
            
            # QC metrics - better for completed orders than in-progress
            if work_order.Status == 'completed':
                defect_rate = round(random.uniform(0, 0.05), 4)  # 0-5% defect rate
                rework_rate = round(random.uniform(0, 0.1), 4)   # 0-10% rework rate
                yield_rate = round(1 - defect_rate - rework_rate, 4)  # Remaining percentage
            else:
                defect_rate = round(random.uniform(0, 0.1), 4)   # 0-10% defect rate (higher in progress)
                rework_rate = round(random.uniform(0, 0.15), 4)  # 0-15% rework rate (higher in progress)
                yield_rate = round(1 - defect_rate - rework_rate, 4)  # Remaining percentage
            
            # Weighted result
            if defect_rate + rework_rate < 0.05:
                result = 'pass'
            elif defect_rate + rework_rate < 0.15:
                result = 'rework'
            else:
                result = 'fail'
            
            # Insert QC record
            qc_comments = random.choice(self.data_pools['qc_comments'].get(defect_category, 
                                                                   self.data_pools['qc_comments']['final_assembly']))
            
            qc_result = session.execute(self.QualityControl.insert().values(
                OrderID=order_id,
                Date=datetime.now() if work_order.Status == 'in_progress' else work_order.ActualEndTime,
                Result=result,
                Comments=qc_comments,
                DefectRate=defect_rate,
                ReworkRate=rework_rate,
                YieldRate=yield_rate,
                InspectorID=random.choice(qc_employees).EmployeeID
            ))
            check_id = qc_result.inserted_primary_key[0]
            
            # Create defects if there are any
            if defect_rate > 0:
                # Number of defect types found
                num_defect_types = min(random.randint(1, 3), 
                                     len(defect_types.get(defect_category, defect_types['general'])))
                
                # Select random defect types
                selected_defects = random.sample(defect_types.get(defect_category, defect_types['general']), 
                                               num_defect_types)
                
                for defect_type in selected_defects:
                    # Defect quantity based on defect rate and order quantity
                    max_defects = int(work_order.Quantity * defect_rate / num_defect_types)
                    defect_quantity = random.randint(1, max(1, max_defects))
                    
                    # Insert defect record
                    session.execute(self.Defects.insert().values(
                        CheckID=check_id,
                        DefectType=defect_type,
                        Severity=random.randint(1, 5),  # 1-5 severity scale
                        Quantity=defect_quantity,
                        Location=random.choice(["Front", "Rear", "Left", "Right", "Center", "Top", "Bottom"]),
                        RootCause=random.choice([
                            "Material Defect", "Operator Error", "Machine Calibration", 
                            "Design Issue", "Process Variation", "Tooling Wear"
                        ]),
                        ActionTaken=random.choice([
                            "Reworked", "Scrapped", "Repaired", "Accepted with Deviation", 
                            "Returned to Supplier", "Process Adjusted"
                        ])
                    ))
        
        session.commit()
    
    def insert_material_consumption(self, session, work_order_ids, inventory_ids):
        """Insert material consumption data."""
        logger.info("Inserting material consumption data")
        
        # For each work order, create material consumption records based on BOM
        for order_id in work_order_ids:
            work_order = session.execute(self.WorkOrders.select().where(
                self.WorkOrders.c.OrderID == order_id
            )).fetchone()
            
            # Skip scheduled or cancelled orders
            if work_order.Status in ['scheduled', 'cancelled']:
                continue
            
            # Get the product's bill of materials
            bom_items = session.execute(self.BillOfMaterials.select().where(
                self.BillOfMaterials.c.ProductID == work_order.ProductID
            )).fetchall()
            
            # If no BOM items, create random material usage
            if not bom_items:
                # Use 3-5 random inventory items
                for _ in range(random.randint(3, 5)):
                    item_id = random.choice(inventory_ids)
                    
                    planned_qty = random.randint(1, 10) * work_order.Quantity / 100
                    
                    # Actual quantity varies from plan
                    variance = random.uniform(-0.05, 0.1)  # -5% to +10% variance
                    actual_qty = planned_qty * (1 + variance)
                    
                    # Only completed orders have actual consumption
                    if work_order.Status == 'completed':
                        actual_value = actual_qty
                        variance_percent = variance * 100
                        consumption_date = work_order.ActualEndTime
                    else:
                        # In-progress orders have partial consumption
                        progress = random.uniform(0.1, 0.9)
                        actual_value = planned_qty * progress
                        variance_percent = (actual_value / planned_qty - 1) * 100
                        consumption_date = datetime.now()
                    
                    session.execute(self.MaterialConsumption.insert().values(
                        OrderID=order_id,
                        ItemID=item_id,
                        PlannedQuantity=round(planned_qty, 2),
                        ActualQuantity=round(actual_value, 2),
                        VariancePercent=round(variance_percent, 2),
                        ConsumptionDate=consumption_date,
                        LotNumber=work_order.LotNumber
                    ))
            else:
                # Use actual BOM items
                for bom_item in bom_items:
                    # Calculate planned quantity based on BOM and order quantity
                    planned_qty = bom_item.Quantity * work_order.Quantity
                    
                    # Add scrap factor to planned quantity
                    planned_qty = planned_qty * (1 + bom_item.ScrapFactor)
                    
                    # Actual quantity varies from plan
                    variance = random.uniform(-0.05, 0.1)  # -5% to +10% variance
                    actual_qty = planned_qty * (1 + variance)
                    
                    # Only completed orders have full actual consumption
                    if work_order.Status == 'completed':
                        actual_value = actual_qty
                        variance_percent = variance * 100
                        consumption_date = work_order.ActualEndTime
                    else:
                        # In-progress orders have partial consumption
                        progress = random.uniform(0.1, 0.9)
                        actual_value = planned_qty * progress
                        variance_percent = (actual_value / planned_qty - 1) * 100
                        consumption_date = datetime.now()
                    
                    session.execute(self.MaterialConsumption.insert().values(
                        OrderID=order_id,
                        ItemID=bom_item.ComponentID,
                        PlannedQuantity=round(planned_qty, 2),
                        ActualQuantity=round(actual_value, 2),
                        VariancePercent=round(variance_percent, 2),
                        ConsumptionDate=consumption_date,
                        LotNumber=work_order.LotNumber
                    ))
        
        session.commit()
    
    def insert_downtimes(self, session, work_order_ids, machine_ids, employee_ids):
        """Insert downtime tracking data."""
        logger.info("Inserting downtime data")
        
        # Downtime reasons by category
        downtime_reasons = {
            'unplanned': [
                "Equipment Failure", "Power Outage", "Material Shortage", 
                "Operator Absence", "Quality Issue", "Tool Breakage"
            ],
            'planned': [
                "Scheduled Maintenance", "Shift Change", "Setup/Changeover", 
                "Cleaning", "Training", "Meeting"
            ]
        }
        
        # For each machine, create some downtime records
        for machine_id in machine_ids:
            machine = session.execute(self.Machines.select().where(
                self.Machines.c.MachineID == machine_id
            )).fetchone()
            
            # Number of downtime events varies by machine type
            if machine.Type in ["Frame Welding", "Battery Assembly", "Motor Assembly"]:
                # More complex machines have more downtime
                num_events = random.randint(3, 7)
            else:
                num_events = random.randint(1, 4)
            
            # Get work orders for this machine
            machine_orders = session.execute(self.WorkOrders.select().where(
                self.WorkOrders.c.MachineID == machine_id
            )).fetchall()
            
            # Create downtime events
            for _ in range(num_events):
                # Determine if planned or unplanned
                category = random.choices(['planned', 'unplanned'], weights=[60, 40], k=1)[0]
                reason = random.choice(downtime_reasons[category])
                
                # Duration depends on reason
                if reason == "Scheduled Maintenance":
                    duration = random.randint(120, 480)  # 2-8 hours
                elif reason == "Equipment Failure":
                    duration = random.randint(60, 240)  # 1-4 hours
                elif reason in ["Setup/Changeover", "Cleaning"]:
                    duration = random.randint(15, 60)  # 15-60 minutes
                else:
                    duration = random.randint(30, 120)  # 30-120 minutes
                
                # Dates - within last 90 days
                start_time = datetime.now() - timedelta(days=random.randint(1, 90))
                end_time = start_time + timedelta(minutes=duration)
                
                # Find a related work order if one exists
                order_id = None
                if machine_orders:
                    for order in machine_orders:
                        # Check if downtime falls within the order's timeframe
                        if order.ActualStartTime and order.ActualEndTime:
                            order_start = order.ActualStartTime
                            order_end = order.ActualEndTime
                            
                            # If downtime overlaps with order timeframe, associate it
                            if (start_time >= order_start and start_time <= order_end) or \
                               (end_time >= order_start and end_time <= order_end) or \
                               (start_time <= order_start and end_time >= order_end):
                                order_id = order.OrderID
                                break
                
                # Get a technician or operator who might report the issue
                if category == 'planned':
                    role = 'Technician'
                else:
                    role = random.choice(['Operator', 'Technician'])
                
                reporters = session.execute(self.Employees.select().where(
                    self.Employees.c.Role == role
                )).fetchall()
                
                if not reporters:
                    reporter_id = random.choice(employee_ids)
                else:
                    reporter_id = random.choice(reporters).EmployeeID
                
                # Generate description
                descriptions = {
                    "Equipment Failure": [
                        f"Machine {machine.Name} motor overheated and stopped",
                        f"Control system failure on {machine.Name}",
                        f"Mechanical jam in {machine.Type} unit"
                    ],
                    "Power Outage": [
                        "Factory-wide power outage",
                        "Electrical surge damaged circuit boards",
                        "Backup generator failed to start"
                    ],
                    "Scheduled Maintenance": [
                        f"Routine {machine.MaintenanceFrequency}hr maintenance check",
                        "Annual certification and inspection",
                        "Software update and calibration"
                    ],
                    "Setup/Changeover": [
                        "Product changeover from previous batch",
                        "Tool replacement and alignment",
                        "Setup for new product specifications"
                    ]
                }
                
                if reason in descriptions:
                    description = random.choice(descriptions[reason])
                else:
                    description = f"{reason} on {machine.Name} in {machine.Type} area"
                
                session.execute(self.Downtimes.insert().values(
                    MachineID=machine_id,
                    OrderID=order_id,
                    StartTime=start_time,
                    EndTime=end_time,
                    Duration=duration,
                    Reason=reason,
                    Category=category,
                    Description=description,
                    ReportedBy=reporter_id
                ))
        
        session.commit()
    
    def insert_oee_metrics(self, session, machine_ids):
        """Insert OEE (Overall Equipment Effectiveness) metrics."""
        logger.info("Inserting OEE metrics")
        
        # For each machine, create daily OEE metrics for the past 30 days
        for machine_id in machine_ids:
            machine = session.execute(self.Machines.select().where(
                self.Machines.c.MachineID == machine_id
            )).fetchone()
            
            for day in range(30):
                date = datetime.now() - timedelta(days=day)
                
                # Planned production time (in minutes)
                planned_time = 480  # 8 hours by default
                
                # Machine-specific base metrics
                if machine.Type in ["Frame Welding", "Battery Assembly"]:
                    base_availability = 0.85
                    base_performance = 0.8
                    base_quality = 0.95
                elif machine.Type in ["Final Assembly", "Quality Control"]:
                    base_availability = 0.9
                    base_performance = 0.85
                    base_quality = 0.98
                else:
                    base_availability = 0.88
                    base_performance = 0.82
                    base_quality = 0.96
                
                # Day-specific variation (weekends might be worse)
                weekday = date.weekday()
                if weekday >= 5:  # Weekend
                    day_factor = 0.95  # 5% reduction
                else:
                    day_factor = 1.0
                
                # Random daily variation
                daily_variation = random.uniform(0.95, 1.05)
                
                # Calculate metrics with variation
                availability = min(1.0, base_availability * day_factor * daily_variation)
                performance = min(1.0, base_performance * day_factor * daily_variation)
                quality = min(1.0, base_quality * day_factor * daily_variation)
                
                # Calculate OEE
                oee = availability * performance * quality
                
                # Calculate derived values
                downtime = int(planned_time * (1 - availability))
                actual_time = planned_time - downtime
                
                session.execute(self.OEEMetrics.insert().values(
                    MachineID=machine_id,
                    Date=date,
                    Availability=round(availability, 4),
                    Performance=round(performance, 4),
                    Quality=round(quality, 4),
                    OEE=round(oee, 4),
                    PlannedProductionTime=planned_time,
                    ActualProductionTime=actual_time,
                    Downtime=downtime
                ))
        
        session.commit()

def main():
    """Main function to run the MES simulator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate synthetic MES data')
    parser.add_argument('--config', default='MES-synthetic-data/data_pools.json', help='Path to configuration JSON file')
    parser.add_argument('--db', default='mes.db', help='Path to SQLite database file')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    args = parser.parse_args()
    
    try:
        # Initialize and run simulator
        simulator = MESSimulator(args.config, args.db, args.seed)
        simulator.create_database()
        simulator.insert_data()
        logger.info(f"MES simulation database created successfully at {args.db}")
    except Exception as e:
        logger.error(f"Error creating MES simulation: {e}")
        raise

if __name__ == '__main__':
    main()