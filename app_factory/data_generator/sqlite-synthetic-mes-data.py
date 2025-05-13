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
        """Insert inventory data with realistic supply patterns"""
        logger.info("Inserting inventory items with realistic supply patterns")
        inventory_ids_map = {}  # Map inventory names to their IDs
        cost_range = self.data_pools['cost_ranges']['components']
        lead_time_range = self.data_pools['lead_time_range']
        
        # Material categories
        categories = self.data_pools['material_categories']
        
        # Storage locations
        locations = self.data_pools['storage_locations']
        
        # Items that should never run out completely
        critical_raw_materials = ["Steel Bolts", "Rubber Grips", "Aluminum Tubing"]
        
        # Items that may have low inventory
        shortage_candidates = [
            "Lithium-ion Cells", "Control Circuits", "Microcontrollers", 
            "Battery Casings", "Derailleur Springs", "Dropout Hangers", 
            "Electric Motors", "Chainring Bolts"
        ]
        
        # Select a subset of items that will have shortages
        random.shuffle(shortage_candidates)
        active_shortage_items = shortage_candidates[:3]  # Only 3 items will have shortages
        
        # Store inventory status for reporting
        inventory_status = {
            "well_stocked": 0,
            "adequate": 0,
            "low": 0,
            "critical": 0,
            "overrides": 0
        }
        
        # Prepare the inventory data
        inventory_data = []
        
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
            
            # Get supplier
            supplier_id = random.choice(supplier_ids)
            
            # Determine lead time
            lead_time = random.randint(
                lead_time_range['min'], 
                lead_time_range['max']
            )
            
            # Generate quantity based on item type
            if category == "Raw Material":
                quantity = random.randint(40, 120)
            elif category in ["Electronic Component", "Mechanical Component"]:
                quantity = random.randint(20, 80)
            elif category == "Assembly":
                quantity = random.randint(15, 60)
            else:
                quantity = random.randint(10, 50)
                
            # Adjust quantities for shortage items
            if name in active_shortage_items:
                quantity = random.randint(8, 25)
                
            # Set reorder levels based on item type
            if name in critical_raw_materials:
                # Critical raw materials - slightly below current stock
                reorder_level = int(quantity * random.uniform(0.75, 0.9))
                inventory_status["low"] += 1
            elif name in active_shortage_items:
                # Shortage items - reorder level above current stock
                reorder_level = int(quantity * random.uniform(1.3, 1.8))
                inventory_status["critical"] += 1
            else:
                # Determine stock status category
                stock_status = random.choices(
                    ["well_stocked", "adequate"],
                    weights=[40, 60],  # Distribution of stock levels
                    k=1
                )[0]
                
                if stock_status == "well_stocked":
                    # Well-stocked items
                    reorder_level = int(quantity * random.uniform(0.4, 0.7))
                    inventory_status["well_stocked"] += 1
                else:
                    # Adequate items
                    reorder_level = int(quantity * random.uniform(0.7, 0.9))
                    inventory_status["adequate"] += 1
            
            # Ensure reorder level is at least 1
            reorder_level = max(1, reorder_level)
            
            # Generate last received date
            if quantity < reorder_level:
                # Recently received a small batch
                last_received = datetime.now() - timedelta(days=random.randint(1, 15))
            else:
                # Normal receipt pattern
                last_received = datetime.now() - timedelta(days=random.randint(1, 90))
            
            # Create inventory record
            inventory_record = {
                'Name': name,
                'Category': category,
                'Quantity': quantity,
                'ReorderLevel': reorder_level,
                'SupplierID': supplier_id,
                'LeadTime': lead_time,
                'Cost': round(random.uniform(cost_range['min'], cost_range['max']), 2),
                'LotNumber': f"LOT-{fake.uuid4()[:8]}",
                'Location': random.choice(locations),
                'LastReceivedDate': last_received
            }
            
            # Add to inventory data list
            inventory_data.append(inventory_record)
        
        # Insert all inventory records
        for record in inventory_data:
            result = session.execute(self.Inventory.insert().values(**record))
            inventory_id = result.inserted_primary_key[0]
            inventory_ids_map[record['Name']] = inventory_id
        
        # Log inventory status summary
        logger.info(f"Inventory status distribution:")
        logger.info(f"  Well stocked items: {inventory_status['well_stocked']}")
        logger.info(f"  Adequate items: {inventory_status['adequate']}")
        logger.info(f"  Low inventory items: {inventory_status['low']}")
        logger.info(f"  Critical shortage items: {inventory_status['critical']}")
        
        session.commit()
        return inventory_ids_map

    def insert_bill_of_materials(self, session, product_ids_map, inventory_ids_map):
        """Insert bill of materials data with realistic hierarchical structure."""
        logger.info("Inserting bill of materials with hierarchical structure")
        
        # realistic BOM structure with fixed quantities
        bom_structure = {
            # Finished products have subassemblies with quantities
            "eBike T101": {"Frame": 1, "Wheel": 2, "Battery": 1, "Motor": 1, "Control_Unit": 1, "Brakes": 2, "Seat": 1, "Handlebar": 1},
            "eBike T200": {"Frame": 1, "Wheel": 2, "Battery": 1, "Motor": 1, "Control_Unit": 1, "Brakes": 2, "Seat": 1, "Handlebar": 1},
            "eBike C150": {"Frame": 1, "Wheel": 2, "Battery": 1, "Motor": 1, "Control_Unit": 1, "Brakes": 2, "Seat": 1, "Handlebar": 1},
            "eBike M300": {"Frame": 1, "Wheel": 2, "Battery": 1, "Motor": 1, "Control_Unit": 1, "Brakes": 2, "Seat": 1, "Handlebar": 1},
            
            # Subassemblies have components with quantities
            "Frame": {"Aluminum Tubing": 4, "Steel Bolts": 8, "Rubber Grips": 2, "Dropout Hangers": 2},
            "Wheel": {"Wheel Spokes": 32, "Tire Rubber": 1, "Rim Strips": 1, "Valve Stems": 1, "Ball Bearings": 2},
            "Battery": {"Lithium-ion Cells": 20, "Battery Casings": 1, "Control Circuits": 1},
            "Motor": {"Electric Motors": 1, "Motor Magnets": 4, "Aluminum Tubing": 1},
            "Control_Unit": {"Microcontrollers": 1, "Control Circuits": 2},
            "Brakes": {"Brake Cables": 1, "Brake Pads": 2, "Brake_Lever": 1, "Hydraulic Fluid": 0.1},
            "Seat": {"Seat Padding": 1, "Aluminum Tubing": 1, "Steel Bolts": 4},
            "Handlebar": {"Handlebar Tubing": 1, "Rubber Grips": 2, "Steel Bolts": 4}
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
        
        # Create inventory entries for products that are used as components but don't exist in inventory
        missing_components = set()
        
        # First, collect all components that will be needed
        for product_name, components in bom_structure.items():
            for component_name in components.keys():
                if component_name not in inventory_ids_map and component_name in product_ids_map:
                    missing_components.add(component_name)
        
        # Create inventory entries for missing components
        supplier_id = session.execute(self.Suppliers.select().limit(1)).fetchone().SupplierID
        for component_name in missing_components:
            logger.info(f"Creating inventory entry for product component: {component_name}")
            
            # Get product info for consistent data
            product = session.execute(
                self.Products.select().where(
                    self.Products.c.Name == component_name
                )
            ).fetchone()
            
            if not product:
                continue
            
            # Create an inventory entry that matches this product
            inventory_record = {
                'Name': component_name,
                'Category': product.Category,
                'Quantity': random.randint(20, 100),  # Reasonable stock level
                'ReorderLevel': random.randint(10, 30),
                'SupplierID': supplier_id,
                'LeadTime': random.randint(5, 15),
                'Cost': product.Cost * random.uniform(0.7, 0.9),  # Component cost is less than product price
                'LotNumber': f"LOT-{fake.uuid4()[:8]}",
                'Location': random.choice(self.data_pools['storage_locations']),
                'LastReceivedDate': datetime.now() - timedelta(days=random.randint(1, 30))
            }
            
            result = session.execute(self.Inventory.insert().values(**inventory_record))
            inventory_id = result.inserted_primary_key[0]
            inventory_ids_map[component_name] = inventory_id
            
            logger.info(f"Created inventory entry for component {component_name} with ID {inventory_id}")
        
        # Process each product in the BOM structure
        for product_name, components in bom_structure.items():
            # Case-insensitive matching for product names
            matching_product_name = None
            matching_product_id = None
            
            for name, product_id in product_ids_map.items():
                if name.lower() == product_name.lower():
                    matching_product_name = name
                    matching_product_id = product_id
                    break
            
            if matching_product_id is None:
                logger.warning(f"Product '{product_name}' not found in product IDs map, skipping BOM creation")
                continue
                
            product_id = matching_product_id
            product_level = self.get_product_level(matching_product_name)
            
            # Check if this product already has a BOM
            has_bom = session.execute(
                self.BillOfMaterials.select().where(
                    self.BillOfMaterials.c.ProductID == product_id
                )
            ).fetchone() is not None
            
            if has_bom:
                logger.info(f"Product '{matching_product_name}' already has a BOM, skipping")
                continue  # Skip if already has BOM
            
            for component_name, component_qty in components.items():
                # Case-insensitive matching for component names
                matching_component_name = None
                matching_component_id = None
                
                for name, component_id in inventory_ids_map.items():
                    if name.lower() == component_name.lower():
                        matching_component_name = name
                        matching_component_id = component_id
                        break
                        
                if matching_component_id is None:
                    logger.warning(f"Component '{component_name}' not found in inventory for product '{matching_product_name}', skipping")
                    continue
                
                component_id = matching_component_id
                component_level = self.get_product_level(matching_component_name)
                
                # Use the specified quantity from the BOM structure
                quantity = component_qty
                
                # Higher scrap for raw materials, lower for components
                if component_level == "Raw Material":
                    scrap_factor = round(random.uniform(0.05, 0.15), 2)  # 5-15% scrap
                else:
                    scrap_factor = round(random.uniform(0.0, 0.05), 2)   # 0-5% scrap
                
                # Insert BOM record
                logger.info(f"Adding BOM entry: {matching_product_name} -> {matching_component_name} (Qty: {quantity})")
                session.execute(self.BillOfMaterials.insert().values(
                    ProductID=product_id,
                    ComponentID=component_id,
                    Quantity=quantity,
                    ScrapFactor=scrap_factor
                ))
        
        # For products not in the structure, add default components
        for product_name, product_id in product_ids_map.items():
            if any(product_name.lower() == name.lower() for name in bom_structure.keys()):
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
                
                logger.info(f"Adding default BOM entry: {product_name} -> {component_name} (Qty: {quantity})")
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
        """Insert work centers data with realistic capacity constraints."""
        logger.info("Inserting work centers")
        work_center_ids = {}
        cost_range = self.data_pools['cost_ranges']['work_centers']
        
        # Locations
        plant_areas = ["Building A", "Building B", "Main Factory", "North Wing", "South Wing"]
        
        # Select a work center to be the bottleneck
        # Typical bottlenecks are often in specialized processes
        bottleneck_candidates = ["Battery Production", "Motor Assembly", "Frame Fabrication"]
        bottleneck_work_center = random.choice(bottleneck_candidates)
        
        # Seasonal capacity factors - simulate increased/decreased capacity based on time of year
        current_month = datetime.now().month
        if current_month in [11, 12, 1]:  # Winter months
            seasonal_factor = 0.9  # Lower capacity in winter
        elif current_month in [6, 7, 8]:  # Summer months
            seasonal_factor = 1.1  # Higher capacity in summer
        else:
            seasonal_factor = 1.0  # Normal capacity in spring/fall
        
        for wc in self.data_pools['work_centers']:
            # Apply bottleneck factor if this is the bottleneck work center
            capacity_factor = 1.0
            if wc['name'] == bottleneck_work_center:
                # Bottleneck work center has 60-80% of normal capacity
                capacity_factor = random.uniform(0.6, 0.8)
                bottleneck_description = f"{wc['description']} (Current production bottleneck)"
            else:
                bottleneck_description = wc['description']
                
            # Apply seasonal capacity variation
            final_capacity = wc['capacity'] * capacity_factor * seasonal_factor
            
            # Some work centers are always active, others may be inactive
            is_active = True
            if wc['name'] in ["Final Assembly Line 2"]:  # Secondary lines might be inactive
                is_active = random.choices([True, False], weights=[80, 20], k=1)[0]
            
            result = session.execute(self.WorkCenters.insert().values(
                Name=wc['name'],
                Description=bottleneck_description,
                Capacity=round(final_capacity, 2),
                CapacityUOM=wc['capacity_uom'],
                CostPerHour=round(random.uniform(cost_range['min'], cost_range['max']), 2),
                Location=random.choice(plant_areas),
                IsActive=is_active
            ))
            work_center_id = result.inserted_primary_key[0]
            work_center_ids[wc['name']] = work_center_id
        
        session.commit()
        logger.info(f"Created work centers with {bottleneck_work_center} as production bottleneck")
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
        
        # Get finished product names for tracking
        finished_product_names = [name for name, _ in finished_products]
        logger.info(f"Finished products to manufacture: {finished_product_names}")
        
        # Track products that have been manufactured
        manufactured_products = set()
        
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
        
        # Key products with increased manufacturing probability
        key_products = ["eBike T101", "eBike T200", "eBike C150", "eBike M300"]
        
        # Increase overall batch count for a more populated database
        batch_count_multiplier = 1.5
        
        # For the first 30 days of the simulation, ensure all key products are manufactured
        early_period_end = start_date + timedelta(days=30)
        
        while current_date <= end_date:
            # Determine day of week (0=Monday, 6=Sunday)
            weekday = current_date.weekday()
            
            # Adjust batch count based on day of week to simulate realistic scheduling patterns
            if weekday < 2:  # Monday-Tuesday
                num_batches_weights = [5, 50, 35, 10]  # Higher production
            elif weekday < 4:  # Wednesday-Thursday
                num_batches_weights = [10, 60, 25, 5]  # Medium production
            elif weekday < 5:  # Friday
                num_batches_weights = [20, 60, 20, 0]  # Lower production
            else:  # Weekend
                num_batches_weights = [70, 25, 5, 0]   # Minimal production
            
            # Determine how many batches to start on this date
            num_batches = random.choices([0, 1, 2, 3], weights=num_batches_weights, k=1)[0]
            
            # Apply multiplier to increase overall batch count
            num_batches = min(5, int(num_batches * batch_count_multiplier) + 1)
            
            # Monthly production pattern - higher at month start (new orders) and month end (fulfillment)
            day_of_month = current_date.day
            days_in_month = 30  # Approximation
            
            if day_of_month <= 5:  # Month start - more new production
                num_batches = min(5, num_batches + random.randint(1, 2))
            elif day_of_month >= days_in_month - 5:  # Month end - fulfillment push
                num_batches = min(5, num_batches + random.randint(1, 2))
            
            # Early in simulation, ensure key products get manufactured
            if current_date <= early_period_end:
                # Find which key products haven't been manufactured yet
                unmade_key_products = [p for p in key_products if p not in manufactured_products]
                if unmade_key_products:
                    # Force at least one batch per day during this period
                    num_batches = max(1, num_batches)
            
            for batch_index in range(num_batches):
                # During early period, prioritize unmade key products
                if current_date <= early_period_end:
                    unmade_key_products = [p for p in key_products if p not in manufactured_products]
                    if unmade_key_products and random.random() < 0.7:  # 70% chance to pick unmade key product
                        product_name = random.choice(unmade_key_products)
                        product_id = product_ids_map.get(product_name)
                        if product_id:
                            logger.info(f"Creating early production batch for unmade key product: {product_name}")
                        else:
                            # Fallback to random selection if product not found
                            product_name, product_id = random.choice(finished_products)
                    else:
                        # Normal random selection
                        product_name, product_id = random.choice(finished_products)
                else:
                    # Product selection logic for normal period
                    if batch_index == 0 and random.random() < 0.4:  # 40% chance for first batch to be key product
                        product_name = random.choice(key_products)
                        product_id = product_ids_map.get(product_name)
                        if not product_id:
                            product_name, product_id = random.choice(finished_products)
                    else:
                        product_name, product_id = random.choice(finished_products)
                
                # Create a unique lot number for this batch
                lot_number = f"LOT-{fake.uuid4()[:8]}-{current_date.strftime('%m%d')}"
                
                # Determine batch size based on product type
                level = self.get_product_level(product_name)
                batch_size_range = self.typical_batch_sizes.get(level, {"min": 10, "max": 100})
                batch_size = random.randint(batch_size_range["min"], batch_size_range["max"])
                
                # Adjust batch size based on day of week (larger batches earlier in week)
                if weekday < 2:  # Monday-Tuesday - larger batches
                    batch_size = int(batch_size * random.uniform(1.0, 1.2))
                elif weekday >= 5:  # Weekend - smaller batches
                    batch_size = int(batch_size * random.uniform(0.6, 0.8))
                
                # Get the production routing for this product
                if "eBike" in product_name:
                    routing = self.production_routes.get("eBike_Model", [])
                else:
                    routing = self.production_routes.get(product_name, self.production_routes["default"])
                
                # Check if we have enough inventory for this batch
                inventory_check = self.check_material_availability(
                    session, product_id, batch_size, product_ids_map, inventory_ids_map
                )
                
                # If insufficient inventory but this is a key product, allow it to proceed with reduced quantity
                if not inventory_check["available"]:
                    if product_name in key_products:
                        batch_size = max(1, inventory_check["max_possible"])
                        logger.info(f"Adjusted batch size for key product {product_name} to {batch_size} due to inventory constraints")
                    else:
                        if inventory_check["max_possible"] <= 0:
                            continue  # Skip this batch
                        batch_size = inventory_check["max_possible"]
                
                # Calculate the start date for the batch - use the current date if it's in the past
                batch_start_date = max(current_date, datetime.now() - timedelta(days=random.randint(1, 10)))
                
                # For past dates, increase likelihood of completed status
                if current_date < datetime.now() - timedelta(days=7):
                    # Past orders should generally be completed
                    force_status = 'completed' if random.random() < 0.9 else None
                else:
                    force_status = None
                
                # Create orders for this batch based on routing
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
                    inventory_ids_map,
                    force_status=force_status
                )
                
                # Mark this product as manufactured
                manufactured_products.add(product_name)
                
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
                    inventory_ids_map,
                    force_status=force_status
                )
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # After all batches, log which products were manufactured
        logger.info(f"Products manufactured: {sorted(list(manufactured_products))}")
        unmade_products = set(finished_product_names) - manufactured_products
        if unmade_products:
            logger.warning(f"Products not manufactured: {sorted(list(unmade_products))}")
        else:
            logger.info("All products were manufactured successfully")
        
        session.commit()
    
    def check_material_availability(self, session, product_id, quantity, product_ids_map, inventory_ids_map):
        """
        Check if there are enough materials in inventory for a work order.
        Returns a dict with availability status and max possible quantity.
        """
        # Get the product name
        product_name = next((name for name, pid in product_ids_map.items() if pid == product_id), None)
        
        # For key products, be more lenient with availability
        key_products = ["eBike T101", "eBike T200", "eBike C150", "eBike M300"]
        
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
                
                # For key products, allow some production even with limited inventory
                if product_name in key_products:
                    # Ensure at least 20% of the requested quantity can be produced
                    possible_qty = max(possible_qty, int(quantity * 0.2))
                
                # Update max possible quantity based on this component's availability
                max_possible = min(max_possible, possible_qty)
        
        # For key products, ensure at least some production is possible
        if product_name in key_products:
            max_possible = max(1, max_possible)
        
        return {
            "available": max_possible >= quantity,
            "max_possible": max_possible
        }
    
    def create_batch_orders(self, session, product_id, product_name, batch_size, lot_number, 
                            start_date, routing, work_center_ids, machine_ids, employee_ids,
                            inventory_ids_map, force_status=None):
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
            
            # Add occasional production delays (5% chance)
            if random.random() < 0.05 and force_status is None:
                # Add a delay of 1-24 hours
                delay_hours = random.uniform(1, 24)
                planned_start = planned_start + timedelta(hours=delay_hours)
            
            planned_end = planned_start + timedelta(hours=step_hours)
            
            # Add occasional extended timeline (10% chance)
            if random.random() < 0.10 and force_status is None:
                # Extend end time by 10-50%
                extension = step_hours * random.uniform(0.1, 0.5)
                planned_end = planned_end + timedelta(hours=extension)
            
            # Lead time (in hours) - typically a bit longer than the process time
            lead_time = int(step_hours * 1.2)
            
            # Determine order status and actual times based on planned dates or forced status
            now = datetime.now()
            
            if force_status:
                # Use the forced status
                status = force_status
                
                if status == 'completed':
                    # For completed orders, create realistic actual times
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
                    
                elif status == 'in_progress':
                    # For in-progress orders, start time is in past, end time is in future
                    actual_start_variation = random.uniform(-0.1, 0.1)
                    actual_start = planned_start + timedelta(hours=step_hours * actual_start_variation)
                    
                    # End time is null for in-progress
                    actual_end = None
                    
                    # Partial production
                    progress = random.uniform(0.2, 0.8)  # 20-80% complete
                    actual_production = int(batch_size * progress)
                    scrap = int(actual_production * random.uniform(0.0, 0.05))
                    actual_production -= scrap
                    
                    # Setup time
                    setup_time_actual = int(setup_time * random.uniform(0.8, 1.2))
                    
                elif status == 'cancelled':
                    # Cancelled orders might have started but were terminated
                    if random.random() < 0.3:  # 30% of cancelled orders never started
                        actual_start = None
                        actual_end = None
                        actual_production = 0
                    else:
                        # Started but cancelled
                        actual_start_variation = random.uniform(-0.1, 0.1)
                        actual_start = planned_start + timedelta(hours=step_hours * actual_start_variation)
                        
                        # End time is when it was cancelled
                        progress = random.uniform(0.1, 0.5)  # 10-50% through when cancelled
                        actual_end = actual_start + timedelta(hours=step_hours * progress)
                        
                        # Partial production
                        actual_production = int(batch_size * progress * 0.8)  # Less efficient when cancelled
                    
                    scrap = int(batch_size * random.uniform(0.05, 0.15))  # Higher scrap for cancelled orders
                    setup_time_actual = int(setup_time * random.uniform(0.8, 1.2)) if actual_start else None
                    
                else:  # scheduled
                    actual_start = None
                    actual_end = None
                    actual_production = None
                    scrap = 0
                    setup_time_actual = None
                    
            elif planned_end < now:
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
                
                # 5% chance of cancellation for past orders, unless the product is eBike T101 or T200
                # (to ensure our main products always have completed orders)
                if (random.random() < 0.05 and 
                    "T101" not in product_name and 
                    "T200" not in product_name):
                    status = 'cancelled'
                    actual_production = int(batch_size * random.uniform(0, 0.3))  # 0-30% completed
                    scrap = int(batch_size * random.uniform(0.05, 0.15))  # Higher scrap for cancelled
                
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
                            machine_ids, employee_ids, product_ids_map, inventory_ids_map,
                            force_status=None):
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
            
            # Batch multiplier varies based on component type
            # Key components often made in larger batches
            if component_name in ["Frame", "Battery", "Motor"]:
                batch_multiplier = random.randint(2, 4)  # Larger batches for key components
            else:
                batch_multiplier = random.randint(1, 3)  # Normal batch size
                
            component_batch_size = max(required_qty, batch_multiplier * required_qty)
            
            # Add occasional "just-in-time" production with smaller batches
            if random.random() < 0.15:  # 15% chance of JIT production
                component_batch_size = max(1, int(required_qty * random.uniform(1.0, 1.3)))
            
            # Component production should happen before parent production
            # Lead time varies by component complexity and type
            if level == "Subassembly":
                # Complex subassemblies have longer lead times
                component_lead_days = random.randint(3, 10)
            else:
                # Simpler components have shorter lead times
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
                inventory_ids_map,
                force_status=force_status  # Pass through the force_status flag
            )
            
            # Recursively create orders for this component's components
            # Only go deeper for critical subassemblies
            if level == "Subassembly" and component_name in ["Frame", "Battery", "Motor"]:
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
                    inventory_ids_map,
                    force_status=force_status  # Pass through the force_status flag
                )
    
    def create_quality_control(self, session, order_id, status, product_name, 
                        work_center_name, employee_ids):
        """Create quality control records with realistic quality patterns."""
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
            
        # Get machine information for quality correlation
        machine = session.execute(
            self.Machines.select().where(
                self.Machines.c.MachineID == work_order.MachineID
            )
        ).fetchone()
        
        # Get employee information for quality correlation
        employee = session.execute(
            self.Employees.select().where(
                self.Employees.c.EmployeeID == work_order.EmployeeID
            )
        ).fetchone()
        
        # Product-specific quality factor - use realistic trend that newer products have more issues
        # while more mature products have better quality
        product_quality_factor = 1.0
        
        if "T101" in product_name:  # Newest model
            product_quality_factor = 1.3
        elif "T200" in product_name:  # Second generation
            product_quality_factor = 1.1
        elif "C150" in product_name:  # City model variant
            product_quality_factor = 0.9
        elif "M300" in product_name:  # Most mature model
            product_quality_factor = 0.7
        
        # Time-based quality improvements
        # Products gradually improve in quality over time as manufacturing processes mature
        if work_order.PlannedStartTime:
            days_ago = (datetime.now() - work_order.PlannedStartTime).days
            if days_ago > 60:  # Older orders had more quality issues
                time_quality_factor = 1.2
            elif days_ago > 30:  # Medium-age orders
                time_quality_factor = 1.1
            elif days_ago > 14:  # Recent orders
                time_quality_factor = 0.9
            else:  # Very recent orders have improved processes
                time_quality_factor = 0.8
        else:
            time_quality_factor = 1.0
            
        # Apply both product and time factors
        product_quality_factor *= time_quality_factor
        
        # Work center quality factor
        work_center_quality_factor = 1.0
        if "Battery Production" in work_center_name:
            work_center_quality_factor = 1.2  # More precision required, more issues
        elif "Motor Assembly" in work_center_name:
            work_center_quality_factor = 1.1  # Complex assembly
        elif "Frame Fabrication" in work_center_name:
            work_center_quality_factor = 1.05  # Varies with materials
        elif "Final Assembly" in work_center_name:
            work_center_quality_factor = 0.9  # Better supervised
        elif "Quality Control" in work_center_name:
            work_center_quality_factor = 0.8  # This is the QC station itself
        
        # Machine-specific quality factor
        machine_quality_factor = 1.0
        if machine:
            # Older machines have more quality issues
            if machine.InstallationDate:
                days_old = (datetime.now() - machine.InstallationDate).days
                if days_old > 1000:  # Older than ~3 years
                    machine_quality_factor = 1.2
                elif days_old > 500:  # 1.5-3 years
                    machine_quality_factor = 1.1
                else:  # Newer machine
                    machine_quality_factor = 0.9
                    
            # Machines that haven't had maintenance recently have more issues
            if machine.LastMaintenanceDate:
                days_since_maintenance = (datetime.now() - machine.LastMaintenanceDate).days
                if days_since_maintenance > 45:  # Overdue maintenance
                    machine_quality_factor *= 1.25
                elif days_since_maintenance > 30:  # Approaching maintenance
                    machine_quality_factor *= 1.1
        
        # Employee-specific quality factor
        employee_quality_factor = 1.0
        if employee:
            # New employees have more quality issues, experienced have fewer
            if employee.HireDate:
                days_employed = (datetime.now() - employee.HireDate).days
                if days_employed < 90:  # New employee (<3 months)
                    employee_quality_factor = 1.3
                elif days_employed < 180:  # 3-6 months
                    employee_quality_factor = 1.1
                elif days_employed > 730:  # Experienced (>2 years)
                    employee_quality_factor = 0.8
        
        # Add occasional quality "incidents" with spikes in defect rates
        quality_incident = False
        quality_incident_factor = 1.0
        
        if random.random() < 0.05:  # 5% chance of quality incident
            quality_incident = True
            quality_incident_factor = random.uniform(2.0, 5.0)
            incident_name = random.choice([
                "Component supplier quality issue", 
                "Calibration drift", 
                "Process change adaptation", 
                "New material batch variation"
            ])
        
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
        
        # Base defect rate - affected by product type, work center, machine, employee, and time
        base_defect_rate = 0.02 * product_quality_factor * work_center_quality_factor * machine_quality_factor * employee_quality_factor
        
        # Adjust for quality incident if present
        if quality_incident:
            defect_rate = base_defect_rate * quality_incident_factor
            rework_rate = round(random.uniform(0.05, 0.2), 4)  # Higher rework during incidents
        else:
            # Normal variation around base rate
            defect_rate = base_defect_rate * random.uniform(0.5, 1.5)
            rework_rate = round(random.uniform(0, 0.1), 4)  # 0-10% rework rate
        
        # Status affects quality - in progress has higher defect rate as issues not yet resolved
        if status == 'completed':
            defect_rate = defect_rate * 0.8  # Completed orders have issues resolved
        else:
            defect_rate = defect_rate * 1.2  # In-progress orders still have issues
        
        # Weekly pattern - quality typically worse on Monday (starting up) and Friday (rushing)
        qc_date = work_order.ActualEndTime if status == 'completed' else datetime.now()
        if qc_date:
            weekday = qc_date.weekday()
            if weekday == 0:  # Monday
                defect_rate *= 1.15  # 15% worse on Monday
            elif weekday == 4:  # Friday
                defect_rate *= 1.1   # 10% worse on Friday
            elif weekday >= 5:  # Weekend
                defect_rate *= 0.9   # 10% better on weekend (less rushed)
        
        # Round and ensure reasonable bounds
        defect_rate = round(min(0.5, max(0, defect_rate)), 4)  # Cap at 50% defects
        yield_rate = round(1 - defect_rate - rework_rate, 4)  # Remaining percentage
        
        # Weighted result based on actual rates
        if defect_rate + rework_rate < 0.05:
            result = 'pass'
        elif defect_rate + rework_rate < 0.15:
            result = 'rework'
        else:
            result = 'fail'
        
        # Get QC comments - more specific based on category and result
        if quality_incident:
            comments = f"{incident_name} detected. {random.choice(self.data_pools['qc_comments'].get(defect_category, ['Quality check performed']))}"
        elif defect_category in self.data_pools['qc_comments']:
            comments_pool = self.data_pools['qc_comments'][defect_category]
            if result == 'pass':
                comments = random.choice(comments_pool) + ". Passed quality inspection."
            elif result == 'rework':
                comments = random.choice(comments_pool) + ". Minor issues require rework."
            else:
                comments = random.choice(comments_pool) + ". Significant issues detected, failed QC."
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
            # Defect types for this category - more specific to work centers
            if defect_category == 'frame':
                defect_pool = [
                    "Weld Failure", "Misalignment", "Surface Defect", 
                    "Frame Bend", "Stress Crack", "Threaded Insert Issue"
                ]
            elif defect_category == 'paint':
                defect_pool = [
                    "Color Mismatch", "Uneven Coating", "Paint Run", 
                    "Orange Peel Texture", "Insufficient Coverage", "Clear Coat Issue"
                ]
            elif defect_category == 'wheels':
                defect_pool = [
                    "Out of True", "Spoke Tension", "Hub Bearing Issue", 
                    "Rim Damage", "Valve Hole Misalignment", "Uneven Tire Seating"
                ]
            elif defect_category == 'electronics':
                defect_pool = [
                    "Connection Issue", "Sensor Malfunction", "Battery Cell Variance", 
                    "Control Board Error", "Motor Coil Problem", "Waterproofing Failure"
                ]
            elif defect_category == 'final_assembly':
                defect_pool = [
                    "Missing Component", "Fastener Torque", "Cable Routing", 
                    "Interface Misalignment", "Improper Adjustment", "Incomplete Assembly"
                ]
            else:
                defect_pool = [
                    "Cosmetic Damage", "Noise", "Vibration", 
                    "Documentation Error", "Packaging Damage", "Specification Deviation"
                ]
            
            # If we have a quality incident, create a dominant defect type
            if quality_incident:
                # Select a dominant defect type
                dominant_defect = random.choice(defect_pool)
                
                # Higher percentage of this defect type
                defect_types = [dominant_defect]
                if random.random() < 0.7:  # 70% chance of additional defects
                    additional_defects = random.sample(
                        [d for d in defect_pool if d != dominant_defect],
                        min(2, len(defect_pool)-1)
                    )
                    defect_types.extend(additional_defects)
                    
                # Create more defects during incidents
                total_defect_qty = max(2, int(work_order.Quantity * defect_rate))
                
                # Most defects are the dominant type
                dominant_qty = int(total_defect_qty * random.uniform(0.6, 0.8))
                remaining_qty = total_defect_qty - dominant_qty
                
                if len(defect_types) > 1:
                    # Distribute remaining quantity among other defect types
                    other_quantities = self.distribute_value(remaining_qty, len(defect_types) - 1)
                    defect_quantities = [dominant_qty] + other_quantities
                else:
                    defect_quantities = [total_defect_qty]
                    
                # Higher severity for quality incidents
                severity_range = (3, 5)
            else:
                # Normal defect patterns
                # Number of defect types found - correlates with defect rate
                max_defect_types = min(len(defect_pool), int(defect_rate * 100) + 1)
                num_defect_types = random.randint(1, max_defect_types)
                
                # Select random defect types
                defect_types = random.sample(defect_pool, num_defect_types)
                
                # Total defect quantity should reflect the defect rate
                total_defect_qty = max(1, int(work_order.Quantity * defect_rate))
                defect_quantities = self.distribute_value(total_defect_qty, num_defect_types)
                
                # Severity range depends on defect rate
                if defect_rate > 0.2:
                    severity_range = (3, 5)  # More severe for high defect rates
                elif defect_rate > 0.1:
                    severity_range = (2, 4)  # Moderate severity
                else:
                    severity_range = (1, 3)  # Less severe for low defect rates
            
            for i, defect_type in enumerate(defect_types):
                # Defect severity - from the calculated range
                severity = random.randint(*severity_range)
                
                defect_quantity = defect_quantities[i]
                
                # Root causes vary by defect type and work center
                if quality_incident:
                    root_causes = ["Component Specification", "Supplier Quality", "Process Deviation", "Material Variation"]
                    root_cause = random.choice(root_causes)
                elif "Assembly" in work_center_name:
                    root_causes = ["Operator Error", "Process Variation", "Missing Step", "Incorrect Procedure"]
                    root_cause = random.choice(root_causes)
                elif "Fabrication" in work_center_name:
                    root_causes = ["Material Defect", "Tool Wear", "Machine Calibration", "Process Parameter Drift"]
                    root_cause = random.choice(root_causes)
                elif "Production" in work_center_name:
                    root_causes = ["Component Variation", "Design Issue", "Material Specification", "Supplier Quality"]
                    root_cause = random.choice(root_causes)
                else:
                    root_causes = ["Material Defect", "Operator Error", "Machine Calibration", "Design Issue", "Process Variation"]
                    root_cause = random.choice(root_causes)
                
                # Actions taken dependent on severity and defect type
                if severity >= 4:
                    actions = ["Scrapped", "Returned to Supplier", "Extensive Rework Required"]
                elif severity >= 3:
                    actions = ["Reworked", "Repaired", "Process Adjusted", "Special Inspection Implemented"]
                else:
                    actions = ["Accepted with Deviation", "Minor Repair", "Adjusted Process Parameters"]
                
                action_taken = random.choice(actions)
                
                defect_record = {
                    'CheckID': check_id,
                    'DefectType': defect_type,
                    'Severity': severity,
                    'Quantity': defect_quantity,
                    'Location': random.choice(["Front", "Rear", "Left", "Right", "Center", "Top", "Bottom"]),
                    'RootCause': root_cause,
                    'ActionTaken': action_taken
                }
                
                session.execute(self.Defects.insert().values(**defect_record))
 
    def distribute_value(self, total, num_parts):
        """Distribute a total value into num_parts with some randomness."""
        if num_parts <= 1:
            return [total]
        
        # Create random points to split the total
        splits = sorted([random.random() for _ in range(num_parts-1)])
        
        # Calculate the portions
        result = []
        prev = 0
        for split in splits:
            portion = max(1, int((split - prev) * total))
            result.append(portion)
            prev = split
        
        # Add the final portion
        final_portion = max(1, total - sum(result))
        result.append(final_portion)
        
        return result
    
    def create_material_consumption(self, session, order_id, product_id, batch_size, 
                       status, lot_number, consumption_date, inventory_ids_map):
        """Create material consumption records"""
        # Get the bill of materials for this product
        bom_items = session.execute(
            self.BillOfMaterials.select().where(
                self.BillOfMaterials.c.ProductID == product_id
            )
        ).fetchall()
        
        # Define critical items with special consumption patterns
        critical_items = ["Steel Bolts", "Rubber Grips", "Aluminum Tubing", "Lithium-ion Cells"]
        
        # Define commonly-used items that shouldn't be depleted too much
        common_items = ["Chain Links", "Wheel Spokes", "Tire Rubber", "Brake Cables", "Gear Shifters"]
        
        # Items that are more aggressively consumed (specialized components)
        specialized_items = ["Control Circuits", "Microcontrollers", "Battery Casings", "Electric Motors"]
        
        # Add cyclic patterns - some days have higher consumption
        day_of_week = consumption_date.weekday()
        weekend_factor = 0.7 if day_of_week >= 5 else 1.0  # Lower consumption on weekends
        
        # Monthly pattern - higher at month start and end
        day_of_month = consumption_date.day
        month_days = 30  # Approximation
        monthly_factor = 1.0
        if day_of_month < 5:
            monthly_factor = 1.2  # Higher at month start (planning new batches)
        elif day_of_month > month_days - 5:
            monthly_factor = 1.15  # Higher at month end (completing orders)
        
        # If no BOM items, create consumption from default items
        if not bom_items:
            default_items = ["Steel Bolts", "Aluminum Tubing", "Rubber Grips"]
            used_items = random.sample(default_items, random.randint(1, len(default_items)))
            
            for item_name in used_items:
                if item_name not in inventory_ids_map:
                    continue
                    
                item_id = inventory_ids_map[item_name]
                
                # Base planned quantity
                planned_qty = random.randint(1, 8) * batch_size / 100
                
                # Apply consumption patterns for critical items
                if item_name in critical_items:
                    # Batch consumption patterns (occasionally larger batches)
                    if random.random() < 0.10:
                        planned_qty *= random.uniform(1.3, 2.0)
                    
                    # Apply cyclic factors
                    planned_qty *= weekend_factor * monthly_factor
                    
                    # Reduced variability for critical items
                    variance = random.uniform(-0.05, 0.15)
                elif item_name in common_items:
                    # Common items have moderate consumption
                    variance = random.uniform(-0.05, 0.08)
                else:
                    variance = random.uniform(-0.03, 0.07)
                
                actual_qty = planned_qty * (1 + variance)
                
                # Only completed orders have full actual consumption
                if status == 'completed':
                    actual_value = actual_qty
                    variance_percent = variance * 100
                else:
                    # In-progress orders have partial consumption with more variance
                    progress = random.uniform(0.1, 0.9)
                    progress_variance = random.uniform(-0.08, 0.08)
                    actual_value = planned_qty * (progress + progress_variance)
                    actual_value = max(0, actual_value)  # Ensure non-negative
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
                        if item_name in critical_items:
                            # For critical items, ensure we never go below a minimum level
                            min_reserve = max(1, int(inventory_item.ReorderLevel * 0.15))
                            available_qty = max(0, inventory_item.Quantity - min_reserve)
                            consumption = min(int(actual_value), available_qty)
                            new_qty = inventory_item.Quantity - consumption
                        else:
                            min_reserve = max(0, int(inventory_item.ReorderLevel * 0.05))
                            available_qty = max(0, inventory_item.Quantity - min_reserve)
                            consumption = min(int(actual_value), available_qty)
                            new_qty = inventory_item.Quantity - consumption
                        
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
            
            # Get component info for pattern detection
            component = session.execute(
                self.Inventory.select().where(
                    self.Inventory.c.ItemID == component_id
                )
            ).fetchone()
            
            if not component:
                continue
                
            component_name = component.Name
            is_critical = component_name in critical_items
            is_common = component_name in common_items
            is_specialized = component_name in specialized_items
            
            # Calculate planned quantity
            planned_qty = bom_item.Quantity * batch_size
            
            # Add scrap factor to planned quantity, but reduce it slightly
            scrap_factor = bom_item.ScrapFactor * 0.9
            planned_qty = planned_qty * (1 + scrap_factor)
            
            # Apply consumption patterns based on item type
            if is_critical:
                # Batch consumption patterns - reduced frequency and magnitude
                if random.random() < 0.10:
                    planned_qty *= random.uniform(1.1, 1.5)
                
                # Apply cyclic factors
                planned_qty *= weekend_factor * monthly_factor
                
                variance = random.uniform(-0.05, 0.12)
            elif is_specialized:
                # Higher variability for specialized components that tend to deplete faster
                variance = random.uniform(-0.05, 0.15)
            elif is_common:
                # Common items have moderate and stable consumption
                variance = random.uniform(-0.03, 0.06)
            else:
                # Regular variability for non-critical, non-specialized items
                variance = random.uniform(-0.04, 0.08)
            
            actual_qty = planned_qty * (1 + variance)
            
            # Only completed orders have full actual consumption
            if status == 'completed':
                actual_value = actual_qty
                variance_percent = variance * 100
            else:
                # In-progress orders have partial consumption
                progress = random.uniform(0.1, 0.9)
                # Add more variance to in-progress consumption but keep it smaller
                progress_variance = random.uniform(-0.08, 0.08)
                actual_value = planned_qty * (progress + progress_variance)
                actual_value = max(0, actual_value)  # Ensure non-negative
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
            
            # Reduce inventory for completed consumptions - more conservative approach
            if status == 'completed':
                # Get current inventory
                inventory_item = session.execute(
                    self.Inventory.select().where(
                        self.Inventory.c.ItemID == component_id
                    )
                ).fetchone()
                
                if inventory_item:
                    if is_critical:
                        # For critical items, ensure we never go below a higher minimum level
                        min_reserve = max(2, int(inventory_item.ReorderLevel * 0.15))
                        available_qty = max(0, inventory_item.Quantity - min_reserve)
                        consumption = min(int(actual_value), available_qty)
                        new_qty = inventory_item.Quantity - consumption
                    elif is_common:
                        # For common items, maintain at least 10% of reorder level
                        min_reserve = max(1, int(inventory_item.ReorderLevel * 0.10))
                        available_qty = max(0, inventory_item.Quantity - min_reserve)
                        consumption = min(int(actual_value), available_qty)
                        new_qty = inventory_item.Quantity - consumption
                    else:
                        # For non-critical, non-common items, allow reduction to 5% of reorder level
                        min_reserve = max(0, int(inventory_item.ReorderLevel * 0.05))
                        available_qty = max(0, inventory_item.Quantity - min_reserve)
                        consumption = min(int(actual_value), available_qty)
                        new_qty = inventory_item.Quantity - consumption
                    
                    session.execute(
                        self.Inventory.update().where(
                            self.Inventory.c.ItemID == component_id
                        ).values(
                            Quantity=new_qty
                        )
                    )
    
    def create_downtime_record(self, session, machine_id, order_id, status, 
                        start_time, end_time, employee_ids):
        """Create a more realistic downtime record with patterns related to maintenance."""
        # Get machine info to check maintenance history
        machine = session.execute(
            self.Machines.select().where(
                self.Machines.c.MachineID == machine_id
            )
        ).fetchone()
        
        if not machine:
            return
        
        # Calculate days since last maintenance
        days_since_maintenance = (datetime.now() - machine.LastMaintenanceDate).days if machine.LastMaintenanceDate else 30
        
        # Machine type-specific breakdown probability adjustment
        breakdown_factor = 1.0
        if machine.Type == "Frame Welding":
            breakdown_factor = 1.2  # Old technology, more issues
        elif machine.Type == "Battery Assembly":
            breakdown_factor = 1.1  # Precision work, some issues
        elif machine.Type == "Quality Control":
            breakdown_factor = 0.7  # Newer technology, fewer issues
        elif machine.Type == "Motor Assembly":
            breakdown_factor = 1.05  # Complex assembly, some issues
        elif machine.Type == "Packaging":
            breakdown_factor = 0.8  # Simple operation, fewer issues
        
        # Machine age factor - older machines have more issues
        if machine.InstallationDate:
            days_old = (datetime.now() - machine.InstallationDate).days
            age_years = days_old / 365.0
            
            if age_years > 5:
                age_factor = 1.5  # Much higher breakdown rate for old machines
            elif age_years > 3:
                age_factor = 1.3  # Higher breakdown rate
            elif age_years > 1:
                age_factor = 1.0  # Baseline
            else:
                age_factor = 0.7  # New machines have fewer issues
        else:
            age_factor = 1.0
        
        # Base probability of unplanned downtime increases with days since maintenance
        # Early days (0-15): very low probability
        # Mid-term (16-30): moderate increase
        # Late (31+): higher probability
        if days_since_maintenance < 15:
            unplanned_probability = 0.05 * breakdown_factor * age_factor
        elif days_since_maintenance < 30:
            unplanned_probability = 0.15 * breakdown_factor * age_factor
        else:
            # Exponential increase in probability after maintenance is due
            overdue_days = days_since_maintenance - 30
            overdue_factor = 1.0 + (overdue_days * 0.02)  # 2% increase per overdue day
            unplanned_probability = min(0.5, 0.15 * breakdown_factor * age_factor * overdue_factor)
        
        # Determine if planned or unplanned based on this curve
        category = random.choices(
            ['planned', 'unplanned'], 
            weights=[max(0.1, 1 - unplanned_probability), unplanned_probability], 
            k=1
        )[0]
        
        # Get downtime reasons for this category
        reasons = self.data_pools['downtime_reasons'][category]
        
        # Weight reasons based on machine type, age, and maintenance status
        if category == 'unplanned':
            if days_since_maintenance > 30:
                # More serious breakdowns for machines needing maintenance
                weighted_reasons = {
                    "Equipment Failure": 50,
                    "Power Outage": 5,
                    "Material Shortage": 10,
                    "Operator Absence": 5,
                    "Quality Issue": 10,
                    "Tool Breakage": 15,
                    "Software Error": 5,
                    "Safety Incident": 5,
                    "Unexpected Maintenance": 30  # Increased for overdue maintenance
                }
            elif machine.InstallationDate and (datetime.now() - machine.InstallationDate).days > 1000:
                # Different pattern for old machines - more mechanical failures
                weighted_reasons = {
                    "Equipment Failure": 40,
                    "Power Outage": 5,
                    "Material Shortage": 10,
                    "Operator Absence": 5,
                    "Quality Issue": 10,
                    "Tool Breakage": 25,  # Higher for old machines
                    "Software Error": 5,
                    "Safety Incident": 5,
                    "Unexpected Maintenance": 15
                }
            else:
                # More balanced for well-maintained machines
                weighted_reasons = {
                    "Equipment Failure": 20,
                    "Power Outage": 10,
                    "Material Shortage": 20,
                    "Operator Absence": 15,
                    "Quality Issue": 15,
                    "Tool Breakage": 10,
                    "Software Error": 10,
                    "Safety Incident": 5,
                    "Unexpected Maintenance": 10
                }
            
            # Filter to only include valid reasons from the data pool
            valid_reasons = [r for r in reasons if r in weighted_reasons]
            valid_weights = [weighted_reasons.get(r, 10) for r in valid_reasons]
            
            if valid_reasons:
                reason = random.choices(valid_reasons, weights=valid_weights, k=1)[0]
            else:
                reason = random.choice(reasons)
        else:
            # Planned maintenance more common for older machines and as next maintenance approaches
            if machine.NextMaintenanceDate:
                days_to_maintenance = (machine.NextMaintenanceDate - datetime.now()).days
                if days_to_maintenance <= 7:  # Approaching scheduled maintenance
                    weighted_reasons = {
                        "Scheduled Maintenance": 60,
                        "Shift Change": 5,
                        "Setup/Changeover": 10,
                        "Cleaning": 10,
                        "Training": 5,
                        "Meeting": 5,
                        "Planned Downtime": 5,
                        "Software Update": 5,
                        "Certification": 5
                    }
                else:
                    weighted_reasons = {
                        "Scheduled Maintenance": 20,
                        "Shift Change": 10,
                        "Setup/Changeover": 30,
                        "Cleaning": 15,
                        "Training": 5,
                        "Meeting": 5,
                        "Planned Downtime": 5,
                        "Software Update": 5,
                        "Certification": 5
                    }
                    
                # Filter to only include valid reasons from the data pool
                valid_reasons = [r for r in reasons if r in weighted_reasons]
                valid_weights = [weighted_reasons.get(r, 10) for r in valid_reasons]
                
                if valid_reasons:
                    reason = random.choices(valid_reasons, weights=valid_weights, k=1)[0]
                else:
                    reason = random.choice(reasons)
            else:
                # Default selection when no next maintenance date
                reason = random.choice(reasons)
        
        # Duration depends on reason, machine type, and age
        if reason == "Scheduled Maintenance":
            # Maintenance takes longer for older machines
            if machine.InstallationDate and (datetime.now() - machine.InstallationDate).days > 1000:
                duration = random.randint(120, 360)  # 2-6 hours for old machines
            else:
                duration = random.randint(60, 240)  # 1-4 hours for newer machines
        elif reason == "Equipment Failure":
            # More serious failures on older machines and when maintenance is overdue
            if days_since_maintenance > 30 or (machine.InstallationDate and (datetime.now() - machine.InstallationDate).days > 1000):
                duration = random.randint(90, 480)  # 1.5-8 hours for serious failures
            else:
                duration = random.randint(30, 180)  # 0.5-3 hours for normal failures
        elif reason in ["Setup/Changeover", "Cleaning"]:
            duration = random.randint(15, 60)  # 15-60 minutes
        elif reason == "Safety Incident":
            # Safety incidents can cause longer downtimes
            duration = random.randint(60, 360)  # 1-6 hours
        elif reason == "Power Outage":
            # Power outages typically affect multiple machines
            duration = random.randint(30, 240)  # 0.5-4 hours
        else:
            duration = random.randint(10, 120)  # 10-120 minutes for other reasons
        
        # Don't allow downtime to exceed the work order duration
        if status == 'completed' and start_time and end_time:
            max_duration = (end_time - start_time).total_seconds() / 60 * 0.8
            duration = min(duration, int(max_duration))
        
        # Calculate start/end times
        if status == 'completed' and start_time and end_time:
            # For completed orders, place downtime within the order timeframe
            order_duration_minutes = (end_time - start_time).total_seconds() / 60
            
            # Downtime can occur at different points in the production process
            # Early: Setup issues
            # Middle: Operational issues
            # Late: Final adjustments or quality issues
            downtime_position = random.choices(
                ['early', 'middle', 'late'],
                weights=[30, 50, 20],
                k=1
            )[0]
            
            if downtime_position == 'early':
                start_offset = order_duration_minutes * random.uniform(0.05, 0.2)
            elif downtime_position == 'middle':
                start_offset = order_duration_minutes * random.uniform(0.3, 0.6)
            else:  # late
                start_offset = order_duration_minutes * random.uniform(0.7, 0.9)
                
            downtime_start = start_time + timedelta(minutes=start_offset)
            downtime_end = downtime_start + timedelta(minutes=duration)
            
            # Ensure downtime ends before order end
            if downtime_end > end_time:
                downtime_end = end_time
                duration = int((downtime_end - downtime_start).total_seconds() / 60)
        else:
            # For in-progress orders, place downtime recently
            now = datetime.now()
            # Most downtimes started in the last 24 hours for in-progress orders
            hours_ago = random.choices(
                [random.uniform(0.5, 4), random.uniform(4, 24)],
                weights=[70, 30],
                k=1
            )[0]
            downtime_start = now - timedelta(hours=hours_ago)
            downtime_end = downtime_start + timedelta(minutes=duration)
            
            # If downtime would end in the future, it's still ongoing
            if downtime_end > now:
                downtime_end = None
                duration = None
        
        # Get a reporter (technician or operator) based on the issue type
        if category == 'planned' or reason in ["Equipment Failure", "Tool Breakage", "Unexpected Maintenance"]:
            role = 'Technician'
        elif reason in ["Safety Incident"]:
            # Safety incidents might be reported by managers
            role = random.choices(['Operator', 'Technician', 'Manager'], weights=[30, 30, 40], k=1)[0]
        else:
            role = random.choices(['Operator', 'Technician'], weights=[70, 30], k=1)[0]
        
        reporters = [
            (name, eid) for (name, r, _), eid in employee_ids.items()
            if r == role
        ]
        
        if not reporters:
            reporters = list(employee_ids.items())
        
        _, reporter_id = random.choice(reporters)
        
        # Generate more specific descriptions based on reason and machine characteristics
        descriptions = {
            "Equipment Failure": [
                f"Machine {machine.Type} motor overheated and stopped functioning",
                f"Control system failure on {machine.Name}",
                f"Mechanical jam in {machine.Type} unit",
                f"Bearing failure in main drive",
                f"Pneumatic system pressure loss",
                f"Drive belt snapped during operation",
                f"Electrical short in control panel",
                f"Coolant pump failure",
                f"Gearbox misalignment detected",
                f"Servo motor malfunction"
            ],
            "Power Outage": [
                "Factory-wide power outage",
                "Electrical surge damaged circuit boards",
                "Backup generator failed to start",
                "Power fluctuation caused system reset",
                "Circuit breaker trip in work center",
                "Transformer failure affected production area",
                "Phase imbalance in electrical supply",
                "Power grid instability causing brownouts",
                "Lightning strike caused temporary outage",
                "Scheduled power system maintenance by utility company"
            ],
            "Scheduled Maintenance": [
                f"Routine maintenance check for {machine.Type}",
                "Annual certification and inspection",
                "Software update and calibration",
                "Preventative maintenance service",
                "Filter replacement and lubrication",
                f"Scheduled {machine.Type} component replacement",
                "90-day maintenance interval service",
                "Firmware update for control systems",
                "Safety system verification check",
                "Critical wear component replacement"
            ],
            "Setup/Changeover": [
                "Product changeover from previous batch",
                "Tool replacement and alignment",
                "Setup for new product specifications",
                "Jig reconfiguration for different model",
                "Program change for new product variant",
                "Die change for new production run",
                "Fixture adjustment for alternate components",
                "Material changeover procedure",
                "Batch start preparation",
                "First article inspection and setup"
            ],
            "Material Shortage": [
                "Awaiting delivery of critical components",
                "Inventory depletion of necessary parts",
                "Quality hold on incoming materials",
                "Incorrect materials delivered",
                "Supply chain delay impact",
                "Missing components for scheduled production",
                "Material quarantine pending testing",
                "Vendor delivery delay",
                "Expedited shipment awaiting arrival",
                "Inventory count discrepancy resolution"
            ],
            "Quality Issue": [
                "Investigating abnormal defect rate",
                "Material specification deviation detected",
                "Product dimensional check failure",
                "Customer complaint investigation",
                "Calibration drift affecting quality",
                "Unexplained process variation investigation",
                "Rework procedure implementation",
                "Special testing of suspicious components",
                "Production hold pending engineering review",
                "Process validation after parameter adjustment"
            ],
            "Safety Incident": [
                "Minor injury requiring first aid",
                "Near-miss investigation and corrective action",
                "Safety protocol review following incident",
                "Emergency stop activation investigation",
                "Safety barrier failure detected",
                "Operational safety check following reported concern",
                "Safety team inspection after incident report",
                "Mandatory safety briefing after procedural violation",
                "Equipment lockout following unsafe condition report",
                "Regulatory safety inspection"
            ]
        }
        
        if reason in descriptions:
            description = random.choice(descriptions[reason])
        else:
            description = f"{reason} on {machine.Name} in {machine.Type} operation"
        
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
        """Insert OEE metrics with realistic patterns related to maintenance cycles."""
        logger.info("Inserting OEE metrics with maintenance correlation")
        
        # Time period for metrics
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Machine type baseline metrics - different machines have different baseline performance
        machine_baselines = {
            "Frame Welding": {"availability": 0.85, "performance": 0.80, "quality": 0.95},
            "Wheel Assembly": {"availability": 0.88, "performance": 0.85, "quality": 0.97},
            "Paint Booth": {"availability": 0.82, "performance": 0.78, "quality": 0.94},
            "Battery Assembly": {"availability": 0.86, "performance": 0.82, "quality": 0.98},
            "Motor Assembly": {"availability": 0.87, "performance": 0.83, "quality": 0.96},
            "Final Assembly": {"availability": 0.90, "performance": 0.85, "quality": 0.98},
            "Quality Control": {"availability": 0.92, "performance": 0.88, "quality": 0.99},
            "Packaging": {"availability": 0.91, "performance": 0.86, "quality": 0.97}
        }
        
        # For each machine, create daily OEE metrics
        for (machine_name, machine_type, _), machine_id in machine_ids.items():
            machine = session.execute(self.Machines.select().where(
                self.Machines.c.MachineID == machine_id
            )).fetchone()
            
            if not machine:
                continue
            
            # Get the baseline metrics for this machine type
            baseline = machine_baselines.get(machine_type, {
                "availability": 0.88, "performance": 0.82, "quality": 0.96
            })
            
            # Get maintenance information
            maintenance_frequency_hours = machine.MaintenanceFrequency
            last_maintenance_date = machine.LastMaintenanceDate
            next_maintenance_date = machine.NextMaintenanceDate
            installation_date = machine.InstallationDate
            
            # Machine age factor - older machines have lower baseline
            days_since_installation = (datetime.now() - installation_date).days if installation_date else 365
            years_old = days_since_installation / 365
            age_factor = max(0.85, 1.0 - (years_old * 0.02))  # 2% degradation per year, minimum 85%
            
            # Different degradation rates for different metrics
            availability_age_impact = age_factor * 0.9 + 0.1  # Less impacted by age
            performance_age_impact = age_factor * 0.8 + 0.2  # More impacted by age
            quality_age_impact = age_factor * 0.95 + 0.05  # Least impacted by age
            
            current_date = start_date
            
            # Simulate a "mini-failure" at a random date within the period
            has_mini_failure = random.random() < 0.15  # 15% chance of a mini failure
            mini_failure_date = start_date + timedelta(days=random.randint(5, 25)) if has_mini_failure else None
            
            while current_date <= end_date:
                # Calculate days since last maintenance - ensure it's not negative
                days_since_maintenance = max(0, (current_date - last_maintenance_date).days if last_maintenance_date else 30)
                
                # Convert to hours for maintenance cycle calculation
                hours_since_maintenance = days_since_maintenance * 24
                
                # Calculate where we are in the maintenance cycle (0 to 1)
                maintenance_cycle_position = max(0.0, min(1.0, hours_since_maintenance / maintenance_frequency_hours))
                
                # Performance degradation curve - different curves for different metrics
                # Availability drops more quickly than other metrics as maintenance approaches
                availability_maintenance_factor = max(0.8, 1.0 - (0.2 * (maintenance_cycle_position ** 1.5)))
                performance_maintenance_factor = max(0.85, 1.0 - (0.15 * (maintenance_cycle_position ** 1.2)))
                quality_maintenance_factor = max(0.9, 1.0 - (0.1 * maintenance_cycle_position))
                
                # Day-specific variation
                weekday = current_date.weekday()
                is_weekend = weekday >= 5
                
                # Weekend factor - slightly lower efficiency on weekends
                weekend_factor = 0.95 if is_weekend else 1.0
                
                # Monthly pattern - slight drop at month start (adjusting to new production plans)
                day_of_month = current_date.day
                month_days = 30  # Approximation
                monthly_factor = 0.98 if day_of_month < 3 else 1.0
                
                # Random daily variation with small inertia (similar to previous days)
                daily_variation = random.uniform(0.97, 1.03)
                
                # Check if next maintenance date is approaching
                days_to_maintenance = (next_maintenance_date - current_date).days if next_maintenance_date else None
                if days_to_maintenance is not None and 0 < days_to_maintenance < 10:
                    # Progressive degradation as maintenance approaches
                    degradation_factor = 1.0 - (0.05 * (10 - days_to_maintenance) / 10)
                    availability_maintenance_factor *= degradation_factor
                    performance_maintenance_factor *= degradation_factor
                
                # Check for mini-failure event - temporary drop in performance
                mini_failure_factor = 1.0
                if mini_failure_date and current_date == mini_failure_date:
                    mini_failure_factor = random.uniform(0.5, 0.7)  # 30-50% drop
                elif mini_failure_date and current_date == mini_failure_date + timedelta(days=1):
                    mini_failure_factor = random.uniform(0.7, 0.9)  # 10-30% drop (recovery)
                
                # Calculate metrics with all factors applied
                base_availability = baseline["availability"]
                base_performance = baseline["performance"]
                base_quality = baseline["quality"]
                
                # Apply all factors to calculate final metrics
                availability = min(0.998, base_availability * 
                                availability_maintenance_factor * 
                                availability_age_impact * 
                                weekend_factor * 
                                monthly_factor * 
                                daily_variation * 
                                mini_failure_factor)
                
                performance = min(0.998, base_performance * 
                                performance_maintenance_factor * 
                                performance_age_impact * 
                                weekend_factor * 
                                monthly_factor * 
                                daily_variation * 
                                mini_failure_factor)
                
                quality = min(0.999, base_quality * 
                            quality_maintenance_factor * 
                            quality_age_impact * 
                            weekend_factor * 
                            (daily_variation * 0.3 + 0.7) * # Quality less affected by daily variation
                            (mini_failure_factor * 0.5 + 0.5)) # Quality less affected by failures
                
                # Calculate OEE
                oee = availability * performance * quality
                
                # Planned production time - different for weekends
                if is_weekend:
                    planned_time = 240  # 4 hours on weekends
                else:
                    planned_time = 480  # 8 hours on weekdays
                
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
    
    def create_downtime_record(self, session, machine_id, order_id, status, 
                          start_time, end_time, employee_ids):
        """Create a more realistic downtime record with patterns related to maintenance."""
        # Get machine info to check maintenance history
        machine = session.execute(
            self.Machines.select().where(
                self.Machines.c.MachineID == machine_id
            )
        ).fetchone()
        
        if not machine:
            return
        
        # Calculate days since last maintenance
        days_since_maintenance = (datetime.now() - machine.LastMaintenanceDate).days if machine.LastMaintenanceDate else 30
        
        # Machine type-specific breakdown probability adjustment
        breakdown_factor = 1.0
        if machine.Type == "Frame Welding":
            breakdown_factor = 1.2  # Old technology, more issues
        elif machine.Type == "Battery Assembly":
            breakdown_factor = 1.1  # Precision work, some issues
        elif machine.Type == "Quality Control":
            breakdown_factor = 0.7  # Newer technology, fewer issues
        elif machine.Type == "Motor Assembly":
            breakdown_factor = 1.05  # Complex assembly, some issues
        elif machine.Type == "Packaging":
            breakdown_factor = 0.8  # Simple operation, fewer issues
        
        # Base probability of unplanned downtime increases with days since maintenance
        # Early days (0-15): very low probability
        # Mid-term (16-30): moderate increase
        # Late (31+): higher probability
        if days_since_maintenance < 15:
            unplanned_probability = 0.05 * breakdown_factor
        elif days_since_maintenance < 30:
            unplanned_probability = 0.15 * breakdown_factor
        else:
            unplanned_probability = min(0.4, 0.15 + (days_since_maintenance - 30) * 0.01) * breakdown_factor
        
        # Determine if planned or unplanned based on this curve
        category = random.choices(
            ['planned', 'unplanned'], 
            weights=[max(0.1, 1 - unplanned_probability), unplanned_probability], 
            k=1
        )[0]
        
        # Get downtime reasons for this category
        reasons = self.data_pools['downtime_reasons'][category]
        
        # Weight reasons based on machine type and maintenance status
        if category == 'unplanned':
            if days_since_maintenance > 30:
                # More breakdowns for machines needing maintenance
                weighted_reasons = {
                    "Equipment Failure": 50,
                    "Power Outage": 5,
                    "Material Shortage": 10,
                    "Operator Absence": 5,
                    "Quality Issue": 10,
                    "Tool Breakage": 15,
                    "Software Error": 5,
                    "Safety Incident": 5,
                    "Unexpected Maintenance": 20
                }
            else:
                # More balanced for well-maintained machines
                weighted_reasons = {
                    "Equipment Failure": 20,
                    "Power Outage": 10,
                    "Material Shortage": 20,
                    "Operator Absence": 15,
                    "Quality Issue": 15,
                    "Tool Breakage": 10,
                    "Software Error": 10,
                    "Safety Incident": 5,
                    "Unexpected Maintenance": 10
                }
            
            # Filter to only include valid reasons from the data pool
            valid_reasons = [r for r in reasons if r in weighted_reasons]
            valid_weights = [weighted_reasons.get(r, 10) for r in valid_reasons]
            
            if valid_reasons:
                reason = random.choices(valid_reasons, weights=valid_weights, k=1)[0]
            else:
                reason = random.choice(reasons)
        else:
            # For planned downtime, use existing random selection
            reason = random.choice(reasons)
        
        # Duration depends on reason and machine type
        if reason == "Scheduled Maintenance":
            duration = random.randint(60, 240)
        elif reason == "Equipment Failure":
            # More serious failures on older machines
            if days_since_maintenance > 30:
                duration = random.randint(60, 240)  # older machines
            else:
                duration = random.randint(30, 120)  # newer machines
        elif reason in ["Setup/Changeover", "Cleaning"]:
            duration = random.randint(15, 60)
        else:
            duration = random.randint(10, 90)
        
        # Don't allow downtime to exceed the work order duration
        if status == 'completed' and start_time and end_time:
            max_duration = (end_time - start_time).total_seconds() / 60 * 0.8
            duration = min(duration, int(max_duration))
        
        # Calculate start/end times
        if status == 'completed' and start_time and end_time:
            # For completed orders, place downtime within the order timeframe
            order_duration_minutes = (end_time - start_time).total_seconds() / 60
            start_offset = random.uniform(0.1, 0.7) * order_duration_minutes
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
        
        # Get a reporter (technician for most issues, operator for some)
        if category == 'planned' or reason in ["Equipment Failure", "Tool Breakage", "Unexpected Maintenance"]:
            role = 'Technician'
        else:
            role = random.choices(['Operator', 'Technician'], weights=[70, 30], k=1)[0]
        
        reporters = [
            (name, eid) for (name, r, _), eid in employee_ids.items()
            if r == role
        ]
        
        if not reporters:
            reporters = list(employee_ids.items())
        
        _, reporter_id = random.choice(reporters)
        
        # Generate more specific descriptions based on reason
        descriptions = {
            "Equipment Failure": [
                f"Machine {machine.Type} motor overheated and stopped functioning",
                f"Control system failure on {machine.Name}",
                f"Mechanical jam in {machine.Type} unit",
                f"Bearing failure in main drive",
                f"Pneumatic system pressure loss"
            ],
            "Power Outage": [
                "Factory-wide power outage",
                "Electrical surge damaged circuit boards",
                "Backup generator failed to start",
                "Power fluctuation caused system reset",
                "Circuit breaker trip in work center"
            ],
            "Scheduled Maintenance": [
                f"Routine maintenance check for {machine.Type}",
                "Annual certification and inspection",
                "Software update and calibration",
                "Preventative maintenance service",
                "Filter replacement and lubrication"
            ],
            "Setup/Changeover": [
                "Product changeover from previous batch",
                "Tool replacement and alignment",
                "Setup for new product specifications",
                "Jig reconfiguration for different model",
                "Program change for new product variant"
            ],
            "Material Shortage": [
                "Awaiting delivery of critical components",
                "Inventory depletion of necessary parts",
                "Quality hold on incoming materials",
                "Incorrect materials delivered",
                "Supply chain delay impact"
            ],
            "Quality Issue": [
                "Investigating abnormal defect rate",
                "Material specification deviation detected",
                "Product dimensional check failure",
                "Customer complaint investigation",
                "Calibration drift affecting quality"
            ]
        }
        
        if reason in descriptions:
            description = random.choice(descriptions[reason])
        else:
            description = f"{reason} on {machine.Name} in {machine.Type} operation"
        
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
    

def main():
    """Main function to create / update the MES simulator"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate or refresh synthetic MES data')
    parser.add_argument('--config', default='app_factory/data_generator/data_pools.json', 
                        help='Path to configuration JSON file')
    parser.add_argument('--db', default='mes.db', 
                        help='Path to SQLite database file')
    parser.add_argument('--seed', type=int, 
                        help='Random seed for reproducibility. Omit for true randomness each run.')
    parser.add_argument('--lookback', type=int, default=90,
                        help='Number of days to look back for historical data')
    parser.add_argument('--lookahead', type=int, default=14,
                        help='Number of days to look ahead for future data')
    parser.add_argument('--mode', choices=['create', 'refresh', 'auto'], default='auto',
                        help='Operation mode: create=new database, refresh=update existing, auto=detect (default)')
    args = parser.parse_args()
    
    # Generate a timestamp-based seed if none provided
    if args.seed is None:
        # Use current timestamp for seed to ensure different data each run
        seed = int(datetime.now().timestamp())
        logger.info(f"No seed provided, using timestamp-based seed: {seed}")
    else:
        seed = args.seed
    
    try:
        # Check if database already exists
        db_exists = os.path.exists(args.db)
        
        # Determine mode based on arguments and database existence
        if args.mode == 'auto':
            # Auto-detect mode based on whether the database exists
            mode = 'refresh' if db_exists else 'create'
            logger.info(f"Auto-detected mode: {mode}")
        else:
            mode = args.mode
        
        # Handle create mode
        if mode == 'create':
            if db_exists:
                logger.info(f"Database {args.db} exists but create mode specified. Removing existing database.")
                os.remove(args.db)
            
            logger.info(f"Creating new database at {args.db}")
            simulator = MESSimulator(
                args.config, 
                args.db, 
                seed=seed,
                lookback_days=args.lookback,
                lookahead_days=args.lookahead
            )
            simulator.create_database()
            simulator.insert_data()
            logger.info(f"MES simulation database created successfully at {args.db}")
            
        # Handle refresh mode
        elif mode == 'refresh':
            if not db_exists:
                logger.error(f"Cannot refresh: Database {args.db} does not exist. Use 'create' mode instead.")
                sys.exit(1)
            
            logger.info(f"Refreshing data in existing database {args.db}")
            
            # Initialize the simulator without creating tables
            simulator = MESSimulator(
                args.config, 
                args.db, 
                seed=seed,
                lookback_days=args.lookback,
                lookahead_days=args.lookahead
            )
            
            # Truncate all tables while preserving schema
            truncate_all_tables(args.db)
            
            # Insert fresh data
            simulator.insert_data()
            logger.info(f"Data refreshed successfully in existing database {args.db}")
            logger.info(f"Generated {args.lookback} days of historical data and {args.lookahead} days of future data")
        
    except Exception as e:
        logger.error(f"Error in MES data generation: {e}")
        raise


def truncate_all_tables(db_path):
    """Delete all data from tables but preserve schema."""
    logger.info(f"Truncating all tables in {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Disable foreign key checks temporarily
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Start a transaction
        conn.execute("BEGIN TRANSACTION;")
        
        # Truncate each table
        for table in tables:
            table_name = table[0]
            if table_name != "sqlite_sequence":  # Skip internal SQLite tables
                logger.info(f"Truncating table: {table_name}")
                cursor.execute(f"DELETE FROM {table_name};")
        
        # Reset autoincrement counters if sqlite_sequence exists
        try:
            cursor.execute("DELETE FROM sqlite_sequence;")
        except sqlite3.OperationalError as e:
            if "no such table: sqlite_sequence" in str(e):
                logger.info("No sqlite_sequence table found (normal if no autoincrement columns)")
            else:
                raise
        
        # Commit transaction
        conn.commit()
        
        # Re-enable foreign key checks
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        conn.close()
        logger.info("All tables truncated successfully")
        return True
    except Exception as e:
        logger.error(f"Error truncating tables: {e}")
        return False


if __name__ == '__main__':
    main()