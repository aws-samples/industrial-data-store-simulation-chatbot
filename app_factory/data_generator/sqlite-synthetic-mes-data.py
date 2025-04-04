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
    
    def __init__(self, config_file, db_file, seed=None, lookback_days=90, lookahead_days=90):
        """
        Initialize the MES simulator.
        
        Args:
            config_file (str): Path to the configuration JSON file
            db_file (str): Path to the SQLite database file
            seed (int, optional): Random seed for reproducibility
            lookback_days (int): Days of historical data to generate
            lookahead_days (int): Days of future data to generate
        """
        self.db_file = db_file
        self.lookback_days = lookback_days
        self.lookahead_days = lookahead_days
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)
        
        # Load data pools configuration
        self.data_pools = self.load_data_pools(config_file)
        
        # Initialize production routing logic
        self.initialize_routing()
        
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
    
    def initialize_routing(self):
        """Initialize production routing logic based on product types"""
        # Define standard production routes for different product types
        self.production_routes = {
            # E-bike full products - route through complete production flow
            "eBike_Model": [
                {"work_center": "Frame Fabrication", "machine_type": "Frame Welding", "duration_factor": 1.0},
                {"work_center": "Paint and Finish", "machine_type": "Paint Booth", "duration_factor": 0.8},
                {"work_center": "Wheel Production", "machine_type": "Wheel Assembly", "duration_factor": 0.5},
                {"work_center": "Battery Production", "machine_type": "Battery Assembly", "duration_factor": 0.7},
                {"work_center": "Motor Assembly", "machine_type": "Motor Assembly", "duration_factor": 0.6},
                {"work_center": "Final Assembly Line 1", "machine_type": "Final Assembly", "duration_factor": 1.2},
                {"work_center": "Quality Control Station", "machine_type": "Quality Control", "duration_factor": 0.3},
                {"work_center": "Packaging and Shipping", "machine_type": "Packaging", "duration_factor": 0.4}
            ],
            # Components - partial routes
            "Frame": [
                {"work_center": "Frame Fabrication", "machine_type": "Frame Welding", "duration_factor": 1.0},
                {"work_center": "Paint and Finish", "machine_type": "Paint Booth", "duration_factor": 0.8}
            ],
            "Wheel": [
                {"work_center": "Wheel Production", "machine_type": "Wheel Assembly", "duration_factor": 1.0},
                {"work_center": "Quality Control Station", "machine_type": "Quality Control", "duration_factor": 0.2}
            ],
            "Battery": [
                {"work_center": "Battery Production", "machine_type": "Battery Assembly", "duration_factor": 1.0},
                {"work_center": "Quality Control Station", "machine_type": "Quality Control", "duration_factor": 0.3}
            ],
            "Motor": [
                {"work_center": "Motor Assembly", "machine_type": "Motor Assembly", "duration_factor": 1.0},
                {"work_center": "Quality Control Station", "machine_type": "Quality Control", "duration_factor": 0.2}
            ],
            "Control_Unit": [
                {"work_center": "Motor Assembly", "machine_type": "Motor Assembly", "duration_factor": 0.7},
                {"work_center": "Quality Control Station", "machine_type": "Quality Control", "duration_factor": 0.3}
            ],
            # Default for other components
            "default": [
                {"work_center": "Final Assembly Line 1", "machine_type": "Final Assembly", "duration_factor": 1.0},
                {"work_center": "Quality Control Station", "machine_type": "Quality Control", "duration_factor": 0.3}
            ]
        }
        
        # Define product levels for BOM hierarchy
        self.product_levels = {
            "Raw Material": ["Aluminum Tubing", "Steel Bolts", "Rubber Grips", "Brake Cables", 
                            "Gear Shifters", "Ball Bearings", "Wheel Spokes", "Tire Rubber",
                            "Chain Links", "Pedal Assemblies", "Lithium-ion Cells", 
                            "Control Circuits", "Seat Padding", "Handlebar Tubing"],
            "Component": ["Wheel", "Wheels", "Tires", "Brake_Lever", "Gear_Lever", "Front_Derailleur", 
                        "Rear_Derailleur", "Chain", "Bottom_Bracket", "Crank", "Bolt", "Washer"],
            "Subassembly": ["Frame", "Battery", "Motor", "Control_Unit", "Motor_Assembly", 
                          "Drive_Train", "Cassette", "Brakes", "Forks", "Seat", "Handlebar"],
            "Finished Product": ["eBike T101", "eBike T200", "eBike C150", "eBike M300"]
        }
        
        # Create a mapping of product to its level
        self.product_to_level = {}
        for level, products in self.product_levels.items():
            for product in products:
                self.product_to_level[product] = level
        
        # Create a mapping of product name to standard process time factor
        self.product_process_time_factor = {
            "Raw Material": 0.5,
            "Component": 1.0,
            "Subassembly": 1.5,
            "Finished Product": 2.5
        }
        
        # Create typical batch sizes by product level
        self.typical_batch_sizes = {
            "Raw Material": {"min": 500, "max": 2000},
            "Component": {"min": 100, "max": 500},
            "Subassembly": {"min": 50, "max": 200},
            "Finished Product": {"min": 10, "max": 100}
        }
    
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
            product_ids_map = self.insert_products(session)
            inventory_ids_map = self.insert_inventory(session, supplier_ids)
            self.insert_bill_of_materials(session, product_ids_map, inventory_ids_map)
            work_center_ids = self.insert_work_centers(session)
            machine_ids = self.insert_machines(session, work_center_ids)
            shift_ids = self.insert_shifts(session)
            employee_ids = self.insert_employees(session, shift_ids)
            
            # Create production batches with interdependent work orders
            self.create_production_batches(
                session, 
                product_ids_map, 
                inventory_ids_map, 
                work_center_ids, 
                machine_ids, 
                employee_ids
            )
            
            # Insert OEE metrics for machines
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
        """Insert product data with clear hierarchy levels."""
        logger.info("Inserting products")
        product_ids_map = {}  # Map product names to their IDs
        cost_range = self.data_pools['cost_ranges']['products']
        
        for i, (name, description) in enumerate(zip(
            self.data_pools['product_names'], 
            self.data_pools['product_descriptions']
        )):
            # Determine product level and category
            product_level = "Component"  # Default level
            for level, products in self.product_levels.items():
                if name in products:
                    product_level = level
                    break
            
            # Assign appropriate category
            if "eBike" in name:
                category = "Electric Bikes"
            elif product_level == "Raw Material":
                category = "Raw Material"
            elif product_level == "Component":
                category = "Components"
            elif product_level == "Subassembly":
                category = "Subassemblies"
            elif name in ["Bolt", "Washer"]:
                category = "Spare Parts"
            elif "MRO" in name:
                category = "MRO"
            else:
                category = "Accessories"
            
            # Generate process time based on product level
            base_process_time = self.product_process_time_factor.get(product_level, 1.0)
            process_time_variation = random.uniform(0.8, 1.2)
            std_process_time = base_process_time * process_time_variation
            
            # Generate cost based on product level
            if product_level == "Finished Product":
                cost_base = random.uniform(cost_range['min'] * 5, cost_range['max'])
            elif product_level == "Subassembly":
                cost_base = random.uniform(cost_range['min'] * 2, cost_range['max'] * 0.6)
            elif product_level == "Component":
                cost_base = random.uniform(cost_range['min'], cost_range['max'] * 0.3)
            else:  # Raw Material
                cost_base = random.uniform(cost_range['min'] * 0.1, cost_range['max'] * 0.1)
            
            result = session.execute(self.Products.insert().values(
                Name=name,
                Description=description,
                Category=category,
                Cost=round(cost_base, 2),
                StandardProcessTime=round(std_process_time, 2),
                IsActive=random.choices([True, False], weights=[95, 5], k=1)[0]
            ))
            product_id = result.inserted_primary_key[0]
            product_ids_map[name] = product_id
        
        session.commit()
        return product_ids_map
    
    def insert_inventory(self, session, supplier_ids):
        """Insert inventory data."""
        logger.info("Inserting inventory items")
        inventory_ids_map = {}  # Map inventory names to their IDs
        cost_range = self.data_pools['cost_ranges']['components']
        lead_time_range = self.data_pools['lead_time_range']
        
        # Material categories
        categories = self.data_pools['material_categories']
        
        # Storage locations
        locations = self.data_pools['storage_locations']
        
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
            
            # Generate realistic inventory levels - raw materials higher, finished goods lower
            if category == "Raw Material":
                quantity = random.randint(200, 2000)
                reorder_level = random.randint(100, 300)
            elif category in ["Electronic Component", "Mechanical Component"]:
                quantity = random.randint(50, 500)
                reorder_level = random.randint(30, 100)
            elif category == "Assembly":
                quantity = random.randint(20, 100)
                reorder_level = random.randint(10, 30)
            else:
                quantity = random.randint(10, 100)
                reorder_level = random.randint(5, 20)
            
            # Occasionally create inventory shortages
            if random.random() < 0.15:  # 15% chance of shortage
                quantity = max(0, int(reorder_level * random.uniform(0.3, 0.9)))
            
            # Create some critical shortages
            if random.random() < 0.05:  # 5% chance of critical shortage
                quantity = max(0, int(reorder_level * random.uniform(0, 0.3)))
            
            # Generate last received date
            last_received = datetime.now() - timedelta(days=random.randint(1, 90))
            
            result = session.execute(self.Inventory.insert().values(
                Name=name,
                Category=category,
                Quantity=quantity,
                ReorderLevel=reorder_level,
                SupplierID=random.choice(supplier_ids),
                LeadTime=random.randint(lead_time_range['min'], lead_time_range['max']),
                Cost=round(random.uniform(cost_range['min'], cost_range['max']), 2),
                LotNumber=f"LOT-{fake.uuid4()[:8]}",
                Location=random.choice(locations),
                LastReceivedDate=last_received
            ))
            inventory_id = result.inserted_primary_key[0]
            inventory_ids_map[name] = inventory_id
        
        session.commit()
        return inventory_ids_map
    
    def insert_bill_of_materials(self, session, product_ids_map, inventory_ids_map):
        """Insert bill of materials data with realistic hierarchical structure."""
        logger.info("Inserting bill of materials with hierarchical structure")
        
        # Create a more realistic BOM structure
        bom_structure = {
            # Finished products have subassemblies
            "eBike T101": ["Frame", "Wheels", "Battery", "Motor", "Control_Unit", "Brakes", "Seat", "Handlebar"],
            "eBike T200": ["Frame", "Wheels", "Battery", "Motor", "Control_Unit", "Brakes", "Seat", "Handlebar"],
            "eBike C150": ["Frame", "Wheels", "Battery", "Motor", "Control_Unit", "Brakes", "Seat", "Handlebar"],
            "eBike M300": ["Frame", "Wheels", "Battery", "Motor", "Control_Unit", "Brakes", "Seat", "Handlebar"],
            
            # Subassemblies have components
            "Frame": ["Aluminum Tubing", "Steel Bolts", "Rubber Grips", "Dropout Hangers"],
            "Wheels": ["Wheel Spokes", "Tire Rubber", "Rim Strips", "Valve Stems", "Ball Bearings"],
            "Battery": ["Lithium-ion Cells", "Battery Casings", "Control Circuits"],
            "Motor": ["Electric Motors", "Motor Magnets", "Aluminum Tubing"],
            "Control_Unit": ["Microcontrollers", "Control Circuits"],
            "Brakes": ["Brake Cables", "Brake Pads", "Brake_Lever", "Hydraulic Fluid"],
            "Seat": ["Seat Padding", "Aluminum Tubing", "Steel Bolts"],
            "Handlebar": ["Handlebar Tubing", "Rubber Grips", "Steel Bolts"]
        }
        
        # Components for items not explicitly defined
        default_components = ["Steel Bolts", "Aluminum Tubing", "Rubber Grips"]
        
        # Quantities by BOM level (parent to child ratio)
        quantity_ranges = {
            "Finished Product": {"min": 1, "max": 2},
            "Subassembly": {"min": 1, "max": 4},
            "Component": {"min": 2, "max": 10},
            "Raw Material": {"min": 5, "max": 20}
        }
        
        # Process each product in the BOM structure
        for product_name, components in bom_structure.items():
            if product_name not in product_ids_map:
                continue
                
            product_id = product_ids_map[product_name]
            product_level = self.get_product_level(product_name)
            
            # Check if this product already has a BOM
            has_bom = session.execute(
                self.BillOfMaterials.select().where(
                    self.BillOfMaterials.c.ProductID == product_id
                )
            ).fetchone() is not None
            
            if has_bom:
                continue  # Skip if already has BOM
            
            for component_name in components:
                # Skip if component isn't in our inventory
                if component_name not in inventory_ids_map:
                    continue
                    
                component_id = inventory_ids_map[component_name]
                component_level = self.get_product_level(component_name)
                
                # Determine appropriate quantity range based on levels
                if product_level in quantity_ranges:
                    qty_range = quantity_ranges[product_level]
                    quantity = random.randint(qty_range["min"], qty_range["max"])
                else:
                    quantity = random.randint(1, 5)
                
                # Higher scrap for raw materials, lower for components
                if component_level == "Raw Material":
                    scrap_factor = round(random.uniform(0.05, 0.15), 2)  # 5-15% scrap
                else:
                    scrap_factor = round(random.uniform(0.0, 0.05), 2)   # 0-5% scrap
                
                session.execute(self.BillOfMaterials.insert().values(
                    ProductID=product_id,
                    ComponentID=component_id,
                    Quantity=quantity,
                    ScrapFactor=scrap_factor
                ))
        
        # For products not in the structure, add default components
        for product_name, product_id in product_ids_map.items():
            if product_name in bom_structure:
                continue  # Skip if already processed
                
            # Check if this product already has a BOM
            has_bom = session.execute(
                self.BillOfMaterials.select().where(
                    self.BillOfMaterials.c.ProductID == product_id
                )
            ).fetchone() is not None
            
            if has_bom:
                continue  # Skip if already has BOM
                
            # Only create BOMs for products that should have them
            product_level = self.get_product_level(product_name)
            if product_level == "Raw Material":
                continue  # Raw materials don't have BOMs
                
            # Use a subset of default components
            num_components = random.randint(1, len(default_components))
            selected_components = random.sample(default_components, num_components)
            
            for component_name in selected_components:
                if component_name not in inventory_ids_map:
                    continue
                    
                component_id = inventory_ids_map[component_name]
                
                # Determine appropriate quantity range based on levels
                if product_level in quantity_ranges:
                    qty_range = quantity_ranges[product_level]
                    quantity = random.randint(qty_range["min"], qty_range["max"])
                else:
                    quantity = random.randint(1, 5)
                
                # Set scrap factor
                scrap_factor = round(random.uniform(0.01, 0.05), 2)
                
                session.execute(self.BillOfMaterials.insert().values(
                    ProductID=product_id,
                    ComponentID=component_id,
                    Quantity=quantity,
                    ScrapFactor=scrap_factor
                ))
        
        session.commit()
    
    def get_product_level(self, product_name):
        """Determine the product level (raw material, component, etc.)"""
        for level, products in self.product_levels.items():
            if product_name in products:
                return level
        
        # Default to component if not found
        return "Component"
    
    def insert_work_centers(self, session):
        """Insert work centers data."""
        logger.info("Inserting work centers")
        work_center_ids = {}
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
            work_center_id = result.inserted_primary_key[0]
            work_center_ids[wc['name']] = work_center_id
        
        session.commit()
        return work_center_ids
    
    def insert_machines(self, session, work_center_ids):
        """Insert machines data."""
        logger.info("Inserting machines")
        machine_ids = {}
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
            for wc_name, wc_id in work_center_ids.items():
                # Match machine types to work centers
                work_center = next((center for center in self.data_pools['work_centers'] 
                                   if center['name'] == wc_name), None)
                if work_center and any(machine_type.lower() in associated.lower() 
                                      for associated in work_center['associated_machines']):
                    suitable_work_centers.append((wc_name, wc_id))
            
            # If no suitable work center, pick random
            if not suitable_work_centers:
                suitable_work_centers = list(work_center_ids.items())
            
            # Create 1-3 machines of each type
            for j in range(random.randint(1, 3)):
                capacity_min, capacity_max = self.data_pools['nominal_capacity'][machine_type]
                wc_name, wc_id = random.choice(suitable_work_centers)
                
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
                
                machine_name = f'Machine {machine_type[:3]}-{i}{j}'
                result = session.execute(self.Machines.insert().values(
                    Name=machine_name,
                    Type=machine_type,
                    WorkCenterID=wc_id,
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
                machine_id = result.inserted_primary_key[0]
                machine_ids[(machine_name, machine_type, wc_name)] = machine_id
        
        session.commit()
        return machine_ids
    
    def insert_shifts(self, session):
        """Insert shifts data."""
        logger.info("Inserting shifts")
        shift_ids = {}
        
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
            shift_id = result.inserted_primary_key[0]
            shift_ids[name] = shift_id
        
        session.commit()
        return shift_ids
    
    def insert_employees(self, session, shift_ids):
        """Insert employees data."""
        logger.info("Inserting employees")
        employee_ids = {}
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
        
        for i in range(50):  # 50 employees
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
            
            # Assign a shift
            shift_name = random.choice(list(shift_ids.keys()))
            
            employee_name = fake.name()
            result = session.execute(self.Employees.insert().values(
                Name=employee_name,
                Role=role,
                ShiftID=shift_ids[shift_name],
                HourlyRate=hourly_rate,
                Skills=skills_str,
                HireDate=hire_date
            ))
            employee_id = result.inserted_primary_key[0]
            employee_ids[(employee_name, role, shift_name)] = employee_id
        
        session.commit()
        return employee_ids
    
    def create_production_batches(self, session, product_ids_map, inventory_ids_map, 
                                  work_center_ids, machine_ids, employee_ids):
        """
        Create production batches with interdependent work orders.
        This is the key function that implements the production flow logic.
        """
        logger.info("Creating production batches with interdependent work orders")
        
        # Time period for work orders
        end_date = datetime.now() + timedelta(days=self.lookahead_days)
        start_date = datetime.now() - timedelta(days=self.lookback_days)
        
        # Get finished products for batches
        finished_products = [
            (name, product_id) for name, product_id in product_ids_map.items() 
            if self.get_product_level(name) == "Finished Product"
        ]
        
        # Get subassemblies for component orders
        subassemblies = [
            (name, product_id) for name, product_id in product_ids_map.items() 
            if self.get_product_level(name) == "Subassembly"
        ]
        
        # Get components for pre-component orders
        components = [
            (name, product_id) for name, product_id in product_ids_map.items() 
            if self.get_product_level(name) == "Component"
        ]
        
        # Create batches over the time period
        current_date = start_date
        
        while current_date <= end_date:
            # Determine how many batches to start on this date (0-3)
            num_batches = random.choices([0, 1, 2, 3], weights=[10, 60, 25, 5], k=1)[0]
            
            for _ in range(num_batches):
                # Create a new production batch
                product_name, product_id = random.choice(finished_products)
                
                # Create a unique lot number for this batch
                lot_number = f"LOT-{fake.uuid4()[:8]}-{current_date.strftime('%m%d')}"
                
                # Determine batch size based on product type
                level = self.get_product_level(product_name)
                batch_size_range = self.typical_batch_sizes.get(level, {"min": 10, "max": 100})
                batch_size = random.randint(batch_size_range["min"], batch_size_range["max"])
                
                # Get the production routing for this product
                if "eBike" in product_name:
                    routing = self.production_routes.get("eBike_Model", [])
                else:
                    routing = self.production_routes.get(product_name, self.production_routes["default"])
                
                # Check if we have enough inventory for this batch
                # (simplistic implementation - in reality would be more complex)
                inventory_check = self.check_material_availability(
                    session, product_id, batch_size, product_ids_map, inventory_ids_map
                )
                
                # If insufficient inventory, reduce batch size or skip
                if not inventory_check["available"]:
                    if inventory_check["max_possible"] <= 0:
                        continue  # Skip this batch
                    batch_size = inventory_check["max_possible"]
                
                # Calculate the start date for the batch - use the current date if it's in the past
                batch_start_date = max(current_date, datetime.now() - timedelta(days=random.randint(1, 10)))
                
                # Create orders for this batch based on routing
                # The order status depends on the date
                self.create_batch_orders(
                    session,
                    product_id,
                    product_name,
                    batch_size,
                    lot_number,
                    batch_start_date,
                    routing,
                    work_center_ids,
                    machine_ids, 
                    employee_ids,
                    inventory_ids_map
                )
                
                # Create component orders for this batch
                self.create_component_orders(
                    session,
                    product_id,
                    product_name,
                    batch_size,
                    lot_number,
                    batch_start_date,
                    work_center_ids,
                    machine_ids,
                    employee_ids,
                    product_ids_map,
                    inventory_ids_map
                )
            
            # Move to next day
            current_date += timedelta(days=1)
        
        session.commit()
    
    def check_material_availability(self, session, product_id, quantity, product_ids_map, inventory_ids_map):
        """
        Check if there are enough materials in inventory for a work order.
        Returns a dict with availability status and max possible quantity.
        """
        # Get the BOM for this product
        bom_items = session.execute(
            self.BillOfMaterials.select().where(
                self.BillOfMaterials.c.ProductID == product_id
            )
        ).fetchall()
        
        if not bom_items:
            return {"available": True, "max_possible": quantity}
        
        max_possible = quantity
        
        for bom_item in bom_items:
            component_id = bom_item.ComponentID
            required_qty = bom_item.Quantity * quantity * (1 + bom_item.ScrapFactor)
            
            # Get inventory level
            inventory_item = session.execute(
                self.Inventory.select().where(
                    self.Inventory.c.ItemID == component_id
                )
            ).fetchone()
            
            if inventory_item:
                available_qty = inventory_item.Quantity
                possible_qty = int(available_qty / (bom_item.Quantity * (1 + bom_item.ScrapFactor)))
                
                # Update max possible quantity based on this component's availability
                max_possible = min(max_possible, possible_qty)
        
        return {
            "available": max_possible >= quantity,
            "max_possible": max_possible
        }
    
    def create_batch_orders(self, session, product_id, product_name, batch_size, lot_number, 
                           start_date, routing, work_center_ids, machine_ids, employee_ids,
                           inventory_ids_map):
        """Create a set of work orders for a production batch following the routing."""
        # Calculate the total production time for the batch (in hours)
        product = session.execute(
            self.Products.select().where(
                self.Products.c.ProductID == product_id
            )
        ).fetchone()
        
        base_process_time = product.StandardProcessTime
        current_date = start_date
        
        # Priority - random but weighted toward middle values
        priority = random.choices([1, 2, 3, 4, 5], weights=[5, 15, 60, 15, 5], k=1)[0]
        
        # Create orders for each step in the routing
        for step_idx, step in enumerate(routing):
            work_center_name = step["work_center"]
            machine_type = step["machine_type"]
            duration_factor = step["duration_factor"]
            
            # Get work center ID
            if work_center_name not in work_center_ids:
                continue
                
            work_center_id = work_center_ids[work_center_name]
            
            # Find a suitable machine
            suitable_machines = [
                (name, mid) for (name, mtype, wcname), mid in machine_ids.items()
                if mtype == machine_type and wcname == work_center_name
            ]
            
            if not suitable_machines:
                continue
                
            machine_name, machine_id = random.choice(suitable_machines)
            
            # Get a suitable employee (operator)
            operators = [
                (name, eid) for (name, role, _), eid in employee_ids.items()
                if role == 'Operator'
            ]
            
            if not operators:
                continue
                
            employee_name, employee_id = random.choice(operators)
            
            # Calculate process time for this step
            step_hours = base_process_time * duration_factor * (batch_size / 100)
            
            # Setup time (in minutes)
            setup_time = random.randint(15, 45)
            
            # Calculate planned start and end times
            planned_start = current_date
            planned_end = planned_start + timedelta(hours=step_hours)
            
            # Lead time (in hours) - typically a bit longer than the process time
            lead_time = int(step_hours * 1.2)
            
            # Determine order status and actual times based on planned dates
            now = datetime.now()
            
            if planned_end < now:
                # Order is in the past - it's completed
                status = 'completed'
                
                # Add some variability to actual start/end times
                actual_start_variation = random.uniform(-0.1, 0.1)  # ±10% variation
                actual_start = planned_start + timedelta(hours=step_hours * actual_start_variation)
                
                # Efficiency factor affects actual duration (80-120% of planned)
                efficiency = random.uniform(0.8, 1.2)
                actual_duration = step_hours * efficiency
                actual_end = actual_start + timedelta(hours=actual_duration)
                
                # Actual production and scrap
                scrap_rate = random.uniform(0.0, 0.05)  # 0-5% scrap
                scrap = int(batch_size * scrap_rate)
                actual_production = batch_size - scrap
                
                # Actual setup time
                setup_time_actual = int(setup_time * random.uniform(0.8, 1.2))
                
            elif planned_start < now and planned_end > now:
                # Order is currently in progress
                status = 'in_progress'
                
                # Actual start time is in the past
                actual_start_variation = random.uniform(-0.1, 0.1)  # ±10% variation
                actual_start = planned_start + timedelta(hours=step_hours * actual_start_variation)
                actual_end = None
                
                # Partial production
                progress = (now - actual_start) / (planned_end - planned_start)
                progress = max(0.1, min(0.9, progress))  # Ensure between 10-90%
                actual_production = int(batch_size * progress)
                scrap = int(actual_production * random.uniform(0.0, 0.05))
                actual_production -= scrap
                
                # Setup time
                setup_time_actual = int(setup_time * random.uniform(0.8, 1.2))
                
            else:
                # Order is in the future
                status = 'scheduled'
                actual_start = None
                actual_end = None
                actual_production = None
                scrap = 0
                setup_time_actual = None
            
            # 5% chance of cancellation for past orders
            if status == 'completed' and random.random() < 0.05:
                status = 'cancelled'
                actual_production = 0
                scrap = 0
            
            # Insert the work order
            work_order = {
                'ProductID': product_id,
                'WorkCenterID': work_center_id,
                'MachineID': machine_id,
                'EmployeeID': employee_id,
                'Quantity': batch_size,
                'PlannedStartTime': planned_start,
                'PlannedEndTime': planned_end,
                'ActualStartTime': actual_start,
                'ActualEndTime': actual_end,
                'Status': status,
                'Priority': priority,
                'LeadTime': lead_time,
                'LotNumber': lot_number,
                'ActualProduction': actual_production,
                'Scrap': scrap,
                'SetupTimeActual': setup_time_actual
            }
            
            result = session.execute(self.WorkOrders.insert().values(**work_order))
            order_id = result.inserted_primary_key[0]
            
            # Create quality control records for completed or in-progress orders
            if status in ['completed', 'in_progress']:
                self.create_quality_control(
                    session, order_id, status, product_name, work_center_name, employee_ids
                )
                
                # Create material consumption records
                self.create_material_consumption(
                    session, order_id, product_id, batch_size, status, 
                    lot_number, actual_end or datetime.now(), inventory_ids_map
                )
                
                # Create downtime records (random chance)
                if random.random() < 0.2:  # 20% chance of downtime
                    self.create_downtime_record(
                        session, machine_id, order_id, status, 
                        planned_start, planned_end, employee_ids
                    )
            
            # Move the current date forward for the next step
            # Add some buffer time between steps
            buffer_hours = random.uniform(0.5, 2.0)
            current_date = planned_end + timedelta(hours=buffer_hours)
    
    def create_component_orders(self, session, parent_product_id, parent_product_name, 
                               parent_batch_size, lot_number, start_date, work_center_ids, 
                               machine_ids, employee_ids, product_ids_map, inventory_ids_map):
        """Create component work orders that feed into this batch."""
        # Get the BOM for this product
        bom_items = session.execute(
            self.BillOfMaterials.select().where(
                self.BillOfMaterials.c.ProductID == parent_product_id
            )
        ).fetchall()
        
        if not bom_items:
            return
        
        for bom_item in bom_items:
            component_id = bom_item.ComponentID
            
            # Get component info
            component = session.execute(
                self.Inventory.select().where(
                    self.Inventory.c.ItemID == component_id
                )
            ).fetchone()
            
            if not component:
                continue
                
            component_name = component.Name
            
            # Only create component orders for subassemblies or major components
            level = self.get_product_level(component_name)
            if level not in ["Subassembly", "Component"]:
                continue
                
            # Find product ID for this component if it exists
            component_product_id = product_ids_map.get(component_name)
            if not component_product_id:
                continue
                
            # Calculate required quantity including scrap
            required_qty = int(bom_item.Quantity * parent_batch_size * (1 + bom_item.ScrapFactor))
            
            # Determine a reasonable component batch size (often larger than just what's needed)
            batch_size_range = self.typical_batch_sizes.get(level, {"min": 10, "max": 100})
            batch_multiplier = random.randint(1, 3)  # Sometimes make larger batches
            component_batch_size = max(required_qty, batch_multiplier * required_qty)
            
            # Component production should happen before parent production
            # Backdate the start time
            component_lead_days = random.randint(1, 5)
            component_start_date = start_date - timedelta(days=component_lead_days)
            
            # Get routing for this component
            if component_name in self.production_routes:
                routing = self.production_routes[component_name]
            else:
                routing = self.production_routes["default"]
            
            # Create work orders for this component
            self.create_batch_orders(
                session,
                component_product_id,
                component_name,
                component_batch_size,
                lot_number,  # Same lot number as parent for traceability
                component_start_date,
                routing,
                work_center_ids,
                machine_ids, 
                employee_ids,
                inventory_ids_map
            )
            
            # Recursively create orders for this component's components
            self.create_component_orders(
                session,
                component_product_id,
                component_name,
                component_batch_size,
                lot_number,
                component_start_date,
                work_center_ids,
                machine_ids,
                employee_ids,
                product_ids_map,
                inventory_ids_map
            )
    
    def create_quality_control(self, session, order_id, status, product_name, 
                              work_center_name, employee_ids):
        """Create quality control records for a work order."""
        # Get QC employees
        qc_employees = [
            (name, eid) for (name, role, _), eid in employee_ids.items()
            if role == 'Quality Control'
        ]
        
        if not qc_employees:
            qc_employees = list(employee_ids.items())
        
        _, inspector_id = random.choice(qc_employees)
        
        # Get the work order
        work_order = session.execute(
            self.WorkOrders.select().where(
                self.WorkOrders.c.OrderID == order_id
            )
        ).fetchone()
        
        if not work_order:
            return
            
        # Determine defect category based on work center and product
        if "Frame" in work_center_name:
            defect_category = 'frame'
        elif "Paint" in work_center_name:
            defect_category = 'paint'
        elif "Wheel" in work_center_name:
            defect_category = 'wheels'
        elif any(term in work_center_name for term in ['Battery', 'Motor']):
            defect_category = 'electronics'
        elif "Final Assembly" in work_center_name:
            defect_category = 'final_assembly'
        elif "Quality Control" in work_center_name:
            defect_category = random.choice(list(self.data_pools['qc_comments'].keys()))
        else:
            defect_category = 'general'
        
        # QC metrics - better for completed orders than in-progress
        if status == 'completed':
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
        
        # Get QC comments
        if defect_category in self.data_pools['qc_comments']:
            comments_pool = self.data_pools['qc_comments'][defect_category]
            comments = random.choice(comments_pool)
        else:
            comments = "Standard quality check performed."
        
        # Insert QC record
        qc_date = work_order.ActualEndTime if status == 'completed' else datetime.now()
        
        qc_record = {
            'OrderID': order_id,
            'Date': qc_date,
            'Result': result,
            'Comments': comments,
            'DefectRate': defect_rate,
            'ReworkRate': rework_rate,
            'YieldRate': yield_rate,
            'InspectorID': inspector_id
        }
        
        qc_result = session.execute(self.QualityControl.insert().values(**qc_record))
        check_id = qc_result.inserted_primary_key[0]
        
        # Create defects if there are any
        if defect_rate > 0:
            # Defect types for this category
            if defect_category in self.data_pools['qc_comments']:
                defect_pool = [
                    "Weld Failure", "Misalignment", "Surface Defect", 
                    "Color Mismatch", "Uneven Coating", "Out of True", 
                    "Chain Misalignment", "Uneven Braking", "Connection Issue",
                    "Missing Component", "Cosmetic Damage"
                ]
            else:
                defect_pool = [
                    "Cosmetic Damage", "Noise", "Vibration", 
                    "Documentation Error", "Packaging Damage"
                ]
            
            # Number of defect types found
            num_defect_types = random.randint(1, min(3, len(defect_pool)))
            
            # Select random defect types
            selected_defects = random.sample(defect_pool, num_defect_types)
            
            for defect_type in selected_defects:
                # Defect quantity based on defect rate and order quantity
                max_defects = max(1, int(work_order.Quantity * defect_rate / num_defect_types))
                defect_quantity = random.randint(1, max_defects)
                
                defect_record = {
                    'CheckID': check_id,
                    'DefectType': defect_type,
                    'Severity': random.randint(1, 5),  # 1-5 severity scale
                    'Quantity': defect_quantity,
                    'Location': random.choice(["Front", "Rear", "Left", "Right", "Center", "Top", "Bottom"]),
                    'RootCause': random.choice([
                        "Material Defect", "Operator Error", "Machine Calibration", 
                        "Design Issue", "Process Variation", "Tooling Wear"
                    ]),
                    'ActionTaken': random.choice([
                        "Reworked", "Scrapped", "Repaired", "Accepted with Deviation", 
                        "Returned to Supplier", "Process Adjusted"
                    ])
                }
                
                session.execute(self.Defects.insert().values(**defect_record))
    
    def create_material_consumption(self, session, order_id, product_id, batch_size, 
                                   status, lot_number, consumption_date, inventory_ids_map):
        """Create material consumption records for a work order."""
        # Get the bill of materials for this product
        bom_items = session.execute(
            self.BillOfMaterials.select().where(
                self.BillOfMaterials.c.ProductID == product_id
            )
        ).fetchall()
        
        # If no BOM items, create consumption from default items
        if not bom_items:
            default_items = ["Steel Bolts", "Aluminum Tubing", "Rubber Grips"]
            used_items = random.sample(default_items, random.randint(1, len(default_items)))
            
            for item_name in used_items:
                if item_name not in inventory_ids_map:
                    continue
                    
                item_id = inventory_ids_map[item_name]
                planned_qty = random.randint(1, 10) * batch_size / 100
                
                # Actual quantity varies from plan
                variance = random.uniform(-0.05, 0.1)  # -5% to +10% variance
                actual_qty = planned_qty * (1 + variance)
                
                # Only completed orders have full actual consumption
                if status == 'completed':
                    actual_value = actual_qty
                    variance_percent = variance * 100
                else:
                    # In-progress orders have partial consumption
                    progress = random.uniform(0.1, 0.9)
                    actual_value = planned_qty * progress
                    variance_percent = (actual_value / planned_qty - 1) * 100
                
                consumption_record = {
                    'OrderID': order_id,
                    'ItemID': item_id,
                    'PlannedQuantity': round(planned_qty, 2),
                    'ActualQuantity': round(actual_value, 2),
                    'VariancePercent': round(variance_percent, 2),
                    'ConsumptionDate': consumption_date,
                    'LotNumber': lot_number
                }
                
                session.execute(self.MaterialConsumption.insert().values(**consumption_record))
                
                # Reduce inventory for completed consumptions
                if status == 'completed':
                    # Get current inventory
                    inventory_item = session.execute(
                        self.Inventory.select().where(
                            self.Inventory.c.ItemID == item_id
                        )
                    ).fetchone()
                    
                    if inventory_item:
                        # Calculate new quantity, ensuring it doesn't go below zero
                        new_qty = max(0, inventory_item.Quantity - int(actual_value))
                        
                        session.execute(
                            self.Inventory.update().where(
                                self.Inventory.c.ItemID == item_id
                            ).values(
                                Quantity=new_qty
                            )
                        )
            
            return
        
        # Process actual BOM items
        for bom_item in bom_items:
            component_id = bom_item.ComponentID
            
            # Calculate planned quantity
            planned_qty = bom_item.Quantity * batch_size
            
            # Add scrap factor to planned quantity
            planned_qty = planned_qty * (1 + bom_item.ScrapFactor)
            
            # Actual quantity varies from plan
            variance = random.uniform(-0.05, 0.1)  # -5% to +10% variance
            actual_qty = planned_qty * (1 + variance)
            
            # Only completed orders have full actual consumption
            if status == 'completed':
                actual_value = actual_qty
                variance_percent = variance * 100
            else:
                # In-progress orders have partial consumption
                progress = random.uniform(0.1, 0.9)
                actual_value = planned_qty * progress
                variance_percent = (actual_value / planned_qty - 1) * 100
            
            consumption_record = {
                'OrderID': order_id,
                'ItemID': component_id,
                'PlannedQuantity': round(planned_qty, 2),
                'ActualQuantity': round(actual_value, 2),
                'VariancePercent': round(variance_percent, 2),
                'ConsumptionDate': consumption_date,
                'LotNumber': lot_number
            }
            
            session.execute(self.MaterialConsumption.insert().values(**consumption_record))
            
            # Reduce inventory for completed consumptions
            if status == 'completed':
                # Get current inventory
                inventory_item = session.execute(
                    self.Inventory.select().where(
                        self.Inventory.c.ItemID == component_id
                    )
                ).fetchone()
                
                if inventory_item:
                    # Calculate new quantity, ensuring it doesn't go below zero
                    new_qty = max(0, inventory_item.Quantity - int(actual_value))
                    
                    session.execute(
                        self.Inventory.update().where(
                            self.Inventory.c.ItemID == component_id
                        ).values(
                            Quantity=new_qty
                        )
                    )
    
    def create_downtime_record(self, session, machine_id, order_id, status, 
                              start_time, end_time, employee_ids):
        """Create a downtime record for a machine during a work order."""
        # Determine if planned or unplanned
        category = random.choices(['planned', 'unplanned'], weights=[60, 40], k=1)[0]
        
        # Get downtime reasons for this category
        reasons = self.data_pools['downtime_reasons'][category]
        reason = random.choice(reasons)
        
        # Duration depends on reason
        if reason == "Scheduled Maintenance":
            duration = random.randint(60, 240)  # 1-4 hours in minutes
        elif reason == "Equipment Failure":
            duration = random.randint(30, 180)  # 30min-3hrs
        elif reason in ["Setup/Changeover", "Cleaning"]:
            duration = random.randint(15, 60)  # 15-60 minutes
        else:
            duration = random.randint(10, 90)  # 10-90 minutes
        
        # Don't allow downtime to exceed the work order duration
        if status == 'completed' and start_time and end_time:
            max_duration = (end_time - start_time).total_seconds() / 60 * 0.8  # 80% of order time
            duration = min(duration, int(max_duration))
        
        # Calculate start/end times
        if status == 'completed' and start_time and end_time:
            # For completed orders, place downtime within the order timeframe
            order_duration_minutes = (end_time - start_time).total_seconds() / 60
            start_offset = random.uniform(0.1, 0.7) * order_duration_minutes  # Place in first 70%
            downtime_start = start_time + timedelta(minutes=start_offset)
            downtime_end = downtime_start + timedelta(minutes=duration)
            
            # Ensure downtime ends before order end
            if downtime_end > end_time:
                downtime_end = end_time
                duration = int((downtime_end - downtime_start).total_seconds() / 60)
        else:
            # For in-progress orders, place downtime recently
            now = datetime.now()
            downtime_start = now - timedelta(hours=random.uniform(1, 8))
            downtime_end = downtime_start + timedelta(minutes=duration)
            
            # If downtime would end in the future, it's still ongoing
            if downtime_end > now:
                downtime_end = None
                duration = None
        
        # Get a reporter (technician or operator)
        if category == 'planned':
            role = 'Technician'
        else:
            role = random.choice(['Operator', 'Technician'])
        
        reporters = [
            (name, eid) for (name, r, _), eid in employee_ids.items()
            if r == role
        ]
        
        if not reporters:
            reporters = list(employee_ids.items())
        
        _, reporter_id = random.choice(reporters)
        
        # Generate description
        descriptions = {
            "Equipment Failure": [
                "Machine motor overheated and stopped",
                "Control system failure",
                "Mechanical jam in unit"
            ],
            "Power Outage": [
                "Factory-wide power outage",
                "Electrical surge damaged circuit boards",
                "Backup generator failed to start"
            ],
            "Scheduled Maintenance": [
                "Routine maintenance check",
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
            description = f"{reason} on machine in work center"
        
        downtime_record = {
            'MachineID': machine_id,
            'OrderID': order_id,
            'StartTime': downtime_start,
            'EndTime': downtime_end,
            'Duration': duration,
            'Reason': reason,
            'Category': category,
            'Description': description,
            'ReportedBy': reporter_id
        }
        
        session.execute(self.Downtimes.insert().values(**downtime_record))
    
    def insert_oee_metrics(self, session, machine_ids):
        """Insert OEE (Overall Equipment Effectiveness) metrics."""
        logger.info("Inserting OEE metrics")
        
        # Time period for metrics
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # For each machine, create daily OEE metrics
        for machine_id in machine_ids.values():
            machine = session.execute(self.Machines.select().where(
                self.Machines.c.MachineID == machine_id
            )).fetchone()
            
            if not machine:
                continue
                
            current_date = start_date
            
            while current_date <= end_date:
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
                weekday = current_date.weekday()
                if weekday >= 5:  # Weekend
                    day_factor = 0.95  # 5% reduction
                else:
                    day_factor = 1.0
                
                # Random daily variation
                daily_variation = random.uniform(0.95, 1.05)
                
                # Consider machine efficiency factor
                machine_factor = machine.EfficiencyFactor
                
                # Calculate metrics with variation
                availability = min(1.0, base_availability * day_factor * daily_variation * machine_factor)
                performance = min(1.0, base_performance * day_factor * daily_variation * machine_factor)
                quality = min(1.0, base_quality * day_factor * daily_variation)
                
                # Calculate OEE
                oee = availability * performance * quality
                
                # Calculate derived values
                downtime = int(planned_time * (1 - availability))
                actual_time = planned_time - downtime
                
                oee_record = {
                    'MachineID': machine_id,
                    'Date': current_date,
                    'Availability': round(availability, 4),
                    'Performance': round(performance, 4),
                    'Quality': round(quality, 4),
                    'OEE': round(oee, 4),
                    'PlannedProductionTime': planned_time,
                    'ActualProductionTime': actual_time,
                    'Downtime': downtime
                }
                
                session.execute(self.OEEMetrics.insert().values(**oee_record))
                
                # Move to next day
                current_date += timedelta(days=1)
        
        session.commit()

def main():
    """Main function to run the MES simulator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate synthetic MES data')
    parser.add_argument('--config', default='data_pools.json', help='Path to configuration JSON file')
    parser.add_argument('--db', default='mes.db', help='Path to SQLite database file')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--lookback', type=int, default=90, help='Number of days to look back for historical data')
    parser.add_argument('--lookahead', type=int, default=90, help='Number of days to look ahead for future data')
    args = parser.parse_args()
    
    try:
        # Initialize and run simulator
        simulator = MESSimulator(
            args.config, 
            args.db, 
            args.seed,
            lookback_days=args.lookback,
            lookahead_days=args.lookahead
        )
        simulator.create_database()
        simulator.insert_data()
        logger.info(f"MES simulation database created successfully at {args.db}")
    except Exception as e:
        logger.error(f"Error creating MES simulation: {e}")
        raise

if __name__ == '__main__':
    main()