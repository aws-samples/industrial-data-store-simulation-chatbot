# refresh-mes-data.py
import os
import sys
import argparse
import logging
import sqlite3
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MES-Data-Refresher')

# Import the MESSimulator class from the existing script
def import_simulator():
    """Dynamically import the MESSimulator class from the sqlite-synthetic-mes-data.py file."""
    try:
        # Get the full path to the module
        module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sqlite-synthetic-mes-data.py')
        
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("mes_simulator_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Return the MESSimulator class
        return module.MESSimulator
    except Exception as e:
        logger.error(f"Failed to import MESSimulator: {e}")
        raise

# Get the MESSimulator class
MESSimulator = import_simulator()

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

def refresh_mes_data(db_path, config_path, seed=None, lookback_days=30, lookahead_days=90):
    """Refresh the MES database with new synthetic data."""
    
    # 1. Check if database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}. Please create it first.")
        return False
    
    # 2. Truncate all tables
    if not truncate_all_tables(db_path):
        return False
    
    # 3. Create a simulator instance with improved parameters
    logger.info(f"Regenerating data with seed: {seed}")
    simulator = MESSimulator(
        config_path, 
        db_path, 
        seed=seed,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days
    )
    
    # 4. Insert fresh data
    try:
        simulator.insert_data()
        logger.info(f"Data regeneration completed successfully at {db_path}")
        logger.info(f"Generated {lookback_days} days of historical data and {lookahead_days} days of future data")
        return True
    except Exception as e:
        logger.error(f"Error regenerating data: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Refresh synthetic MES data in existing database')
    parser.add_argument('--config', default='data_pools.json', 
                        help='Path to configuration JSON file')
    parser.add_argument('--db', default='mes.db', 
                        help='Path to existing SQLite database file')
    parser.add_argument('--seed', type=int, 
                        help='Random seed for reproducibility. Omit for true randomness each run.')
    parser.add_argument('--lookback', type=int, default=30,
                        help='Number of days to look back for historical data')
    parser.add_argument('--lookahead', type=int, default=90,
                        help='Number of days to look ahead for future data')
    args = parser.parse_args()
    
    # Generate a timestamp-based seed if none provided
    if args.seed is None:
        # Use current timestamp for seed to ensure different data each run
        seed = int(datetime.now().timestamp())
        logger.info(f"No seed provided, using timestamp-based seed: {seed}")
    else:
        seed = args.seed
    
    result = refresh_mes_data(
        args.db, 
        args.config, 
        seed=seed,
        lookback_days=args.lookback,
        lookahead_days=args.lookahead
    )
    
    sys.exit(0 if result else 1)

if __name__ == '__main__':
    main()