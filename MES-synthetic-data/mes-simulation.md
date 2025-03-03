# MES Simulation

## Creating the Simulated MES Database

This folder contains scripts to simulate a Manufacturing Execution System (MES) that manages and monitors the production process of an e-bike manufacturing facility. The simulated data provides a realistic foundation for testing and demonstrating SQL-based analytics and reporting capabilities.

## Database Structure

The MES database includes tables for:

- **Products**: E-bikes and their components
- **Bill of Materials**: Component relationships and quantities
- **Inventory**: Raw materials and components tracking
- **Suppliers**: External vendor information
- **Work Centers**: Manufacturing areas and their capabilities
- **Machines**: Equipment specifications and maintenance schedules
- **Employees**: Personnel records with roles and skills
- **Work Orders**: Production jobs with schedules and status
- **Quality Control**: Inspection results with defect details
- **Material Consumption**: Component usage tracking
- **Downtimes**: Machine downtime events and reasons
- **OEE Metrics**: Overall Equipment Effectiveness measurements

## 2 Creating the Database

To create the database tables and populate them with synthetic data, run:

```bash
# Create tables and simulation data
python3 MES-synthetic-data/sqlite-synthetic-mes-data.py
```

For additional configuration options:

```bash
# Get help on configuration options
python3 MES-synthetic-data/sqlite-synthetic-mes-data.py --help

# Specify custom configuration and database location
python3 MES-synthetic-data/sqlite-synthetic-mes-data.py --config custom_config.json --db custom_location.db

# Use a fixed random seed for reproducible data generation
python3 MES-synthetic-data/sqlite-synthetic-mes-data.py --seed 12345
```

## Example Queries

The repository includes example SQL queries that demonstrate how to analyze the MES data for various manufacturing metrics:

- Work order tracking with product and machine details
- Inventory management with reorder alerts
- Bill of materials with cost analysis
- Machine efficiency and maintenance schedules
- Quality control with defect analysis
- Production output and schedule adherence
- Downtime analysis by reason and duration
- Material consumption variance analysis
- OEE (Overall Equipment Effectiveness) trends
- Work center capacity utilization
- Employee productivity metrics
- Production scheduling

To run the example queries, you can use the SQLite command-line tool:

```bash
# Open the database with SQLite
sqlite3 mes.db

# Run queries from the example file
.read MES-synthetic-data/example-queries.sql
```

## Data Relationships

The simulated data maintains realistic relationships:

- Products are built from components listed in the bill of materials
- Work orders consume materials according to the bill of materials
- Quality issues and defects are linked to specific work orders
- Machine downtimes impact production schedules and OEE metrics
- Maintenance schedules affect machine availability

This interconnected data structure allows for complex analytical queries that reflect real manufacturing environments.
