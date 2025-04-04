"""
Production utility functions for working with MES data and supporting the simulation
"""

import pandas as pd
import networkx as nx
from datetime import datetime, timedelta
import random
import logging
import sqlite3
import numpy as np
import json
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Production-Utils')

class ProductionGraph:
    """
    Utility class for working with production flow as directed graphs
    Used for visualizing and analyzing dependencies between orders
    """
    
    def __init__(self, session, lot_number=None):
        """
        Initialize with a database session and optional lot number filter
        
        Args:
            session: SQLAlchemy session
            lot_number (str, optional): Filter to a specific lot number
        """
        self.session = session
        self.lot_number = lot_number
        self.graph = nx.DiGraph()
        self.build_graph()
    
    def build_graph(self):
        """Build the production flow graph from work orders."""
        if not self.session:
            logger.error("No database session provided")
            return
        
        # Get work orders, filtering by lot number if specified
        query = """
        SELECT 
            wo.OrderID, 
            wo.LotNumber,
            p.Name as ProductName,
            p.Category as ProductCategory,
            wo.Quantity,
            wo.PlannedStartTime,
            wo.PlannedEndTime,
            wo.Status,
            wc.Name as WorkCenterName
        FROM 
            WorkOrders wo
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        JOIN 
            WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
        """
        
        if self.lot_number:
            query += f" WHERE wo.LotNumber = '{self.lot_number}'"
        
        # Execute query using raw SQL through session
        result = self.session.execute(query)
        work_orders = [dict(row) for row in result]
        
        # Add nodes to the graph (work orders)
        for order in work_orders:
            node_id = order['OrderID']
            self.graph.add_node(
                node_id, 
                lot=order['LotNumber'],
                product=order['ProductName'],
                category=order['ProductCategory'],
                quantity=order['Quantity'],
                start=order['PlannedStartTime'],
                end=order['PlannedEndTime'],
                status=order['Status'],
                work_center=order['WorkCenterName']
            )
        
        # Add edges based on timing and products
        # Orders in the same lot are connected if they have timing dependencies
        lot_groups = {}
        for order in work_orders:
            lot = order['LotNumber']
            if lot not in lot_groups:
                lot_groups[lot] = []
            lot_groups[lot].append(order)
        
        # Within each lot, connect orders based on timing and product flow
        for lot, orders in lot_groups.items():
            # Sort by planned start time
            orders.sort(key=lambda x: x['PlannedStartTime'] if x['PlannedStartTime'] else datetime.max)
            
            # Connect orders based on timing (earlier → later)
            for i in range(len(orders) - 1):
                for j in range(i + 1, len(orders)):
                    if orders[i]['PlannedEndTime'] and orders[j]['PlannedStartTime']:
                        # If order i ends before or when order j starts, connect them
                        if orders[i]['PlannedEndTime'] <= orders[j]['PlannedStartTime']:
                            self.graph.add_edge(
                                orders[i]['OrderID'],
                                orders[j]['OrderID'],
                                type='timing',
                                weight=1
                            )
            
            # Connect based on product hierarchy
            # Find finished products and components
            finished_products = [o for o in orders if o['ProductCategory'] == 'Electric Bikes']
            components = [o for o in orders if o['ProductCategory'] in ['Components', 'Subassemblies']]
            
            # Connect components to their finished products
            for component in components:
                for product in finished_products:
                    # Only connect if timing allows (component completes before product starts)
                    if (component['PlannedEndTime'] and product['PlannedStartTime'] and 
                        component['PlannedEndTime'] <= product['PlannedStartTime']):
                        self.graph.add_edge(
                            component['OrderID'],
                            product['OrderID'],
                            type='material',
                            weight=2
                        )
    
    def get_critical_path(self):
        """
        Find the critical path through the production flow graph
        Returns a list of nodes representing the longest path
        """
        if not self.graph:
            return []
        
        # Use topological sort to find longest path
        try:
            # Convert to directed acyclic graph if not already
            if not nx.is_directed_acyclic_graph(self.graph):
                # Remove cycles by removing edges from later to earlier nodes
                edges_to_remove = []
                for u, v in self.graph.edges():
                    if (self.graph.nodes[u].get('start') and 
                        self.graph.nodes[v].get('start') and
                        self.graph.nodes[u]['start'] > self.graph.nodes[v]['start']):
                        edges_to_remove.append((u, v))
                
                for edge in edges_to_remove:
                    self.graph.remove_edge(*edge)
            
            # Find longest path using topological sort
            dist = {}  # stores max distance from source
            pred = {}  # stores predecessor
            
            # Initialize distances
            for node in self.graph.nodes():
                dist[node] = float('-inf')
                pred[node] = None
            
            # Find sources (nodes with no incoming edges)
            sources = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
            
            for source in sources:
                dist[source] = 0
            
            # Process nodes in topological order
            for node in nx.topological_sort(self.graph):
                # If we haven't reached this node yet, skip
                if dist[node] == float('-inf'):
                    continue
                
                # Relax outgoing edges
                for successor in self.graph.successors(node):
                    weight = self.graph.edges[node, successor].get('weight', 1)
                    if dist[successor] < dist[node] + weight:
                        dist[successor] = dist[node] + weight
                        pred[successor] = node
            
            # Find sink with maximum distance
            max_dist = float('-inf')
            max_sink = None
            
            for node in self.graph.nodes():
                if self.graph.out_degree(node) == 0:  # it's a sink
                    if dist[node] > max_dist:
                        max_dist = dist[node]
                        max_sink = node
            
            # Reconstruct the path
            path = []
            if max_sink:
                curr = max_sink
                while curr:
                    path.append(curr)
                    curr = pred[curr]
                path.reverse()
            
            return path
            
        except Exception as e:
            logger.error(f"Error finding critical path: {e}")
            return []
    
    def get_node_attributes(self, node_id):
        """Get attributes for a specific node"""
        if node_id in self.graph.nodes:
            return self.graph.nodes[node_id]
        return None
    
    def get_bottleneck_metrics(self):
        """
        Calculate metrics to identify bottlenecks in the production flow
        Returns a dict with work centers and their bottleneck scores
        """
        if not self.graph:
            return {}
        
        # Collect work center data
        work_centers = {}
        
        # Identify critical path
        critical_path = self.get_critical_path()
        
        # Calculate metrics for each work center
        for node_id in self.graph.nodes():
            node = self.graph.nodes[node_id]
            work_center = node.get('work_center')
            
            if not work_center:
                continue
                
            if work_center not in work_centers:
                work_centers[work_center] = {
                    'order_count': 0,
                    'total_duration': 0,
                    'on_critical_path': 0,
                    'status_counts': {'scheduled': 0, 'in_progress': 0, 'completed': 0, 'cancelled': 0},
                    'bottleneck_score': 0
                }
            
            # Increment order count
            work_centers[work_center]['order_count'] += 1
            
            # Add to status count
            status = node.get('status', 'unknown')
            if status in work_centers[work_center]['status_counts']:
                work_centers[work_center]['status_counts'][status] += 1
            
            # Calculate duration if available
            if node.get('start') and node.get('end'):
                duration = (node['end'] - node['start']).total_seconds() / 3600  # hours
                work_centers[work_center]['total_duration'] += duration
            
            # Check if on critical path
            if node_id in critical_path:
                work_centers[work_center]['on_critical_path'] += 1
        
        # Calculate bottleneck scores
        for wc in work_centers:
            # Bottleneck score is a weighted sum of:
            # 1. Proportion of orders on critical path (weight 0.5)
            # 2. Average duration per order (weight 0.3)
            # 3. Proportion of in-progress orders (weight 0.2)
            
            # Normalize these factors
            critical_path_factor = 0
            if work_centers[wc]['order_count'] > 0:
                critical_path_factor = work_centers[wc]['on_critical_path'] / work_centers[wc]['order_count']
            
            duration_factor = 0
            if work_centers[wc]['order_count'] > 0:
                duration_factor = work_centers[wc]['total_duration'] / work_centers[wc]['order_count']
                # Normalize duration factor (assume max duration is 8 hours)
                duration_factor = min(duration_factor / 8, 1)
            
            in_progress_factor = 0
            if work_centers[wc]['order_count'] > 0:
                in_progress_factor = work_centers[wc]['status_counts']['in_progress'] / work_centers[wc]['order_count']
            
            # Calculate weighted score
            bottleneck_score = (
                0.5 * critical_path_factor +
                0.3 * duration_factor +
                0.2 * in_progress_factor
            )
            
            work_centers[wc]['bottleneck_score'] = round(bottleneck_score, 3)
        
        # Sort by bottleneck score
        return dict(sorted(work_centers.items(), key=lambda x: x[1]['bottleneck_score'], reverse=True))
    
    def visualize_graph(self, format='networkx'):
        """
        Visualize the production graph
        
        Args:
            format (str): Output format ('networkx', 'json', 'mermaid')
            
        Returns:
            Graph visualization in specified format
        """
        if not self.graph:
            return None
            
        if format == 'networkx':
            return self.graph
            
        elif format == 'json':
            # Convert to JSON-serializable format
            nodes = []
            for node_id in self.graph.nodes():
                attrs = self.graph.nodes[node_id]
                nodes.append({
                    'id': node_id,
                    'lot': attrs.get('lot', ''),
                    'product': attrs.get('product', ''),
                    'category': attrs.get('category', ''),
                    'status': attrs.get('status', ''),
                    'work_center': attrs.get('work_center', '')
                })
                
            edges = []
            for u, v in self.graph.edges():
                edges.append({
                    'source': u,
                    'target': v,
                    'type': self.graph.edges[u, v].get('type', 'default')
                })
                
            return {
                'nodes': nodes,
                'edges': edges
            }
            
        elif format == 'mermaid':
            # Generate Mermaid flowchart
            mermaid = ["graph TD;"]
            
            # Add nodes
            for node_id in self.graph.nodes():
                attrs = self.graph.nodes[node_id]
                label = f"{attrs.get('product', 'Order')} ({attrs.get('work_center', '')})"
                
                # Style based on status
                style = ""
                if attrs.get('status') == 'completed':
                    style = "style n{} fill:#8afa8a;".format(node_id)
                elif attrs.get('status') == 'in_progress':
                    style = "style n{} fill:#fafa8a;".format(node_id)
                elif attrs.get('status') == 'scheduled':
                    style = "style n{} fill:#8aabfa;".format(node_id)
                elif attrs.get('status') == 'cancelled':
                    style = "style n{} fill:#fa8a8a;".format(node_id)
                
                mermaid.append("    n{}[{}];".format(node_id, label))
                if style:
                    mermaid.append("    " + style)
            
            # Add edges
            for u, v in self.graph.edges():
                edge_type = self.graph.edges[u, v].get('type', 'default')
                if edge_type == 'material':
                    # Material dependency (thicker line)
                    mermaid.append("    n{} ==> n{};".format(u, v))
                else:
                    # Timing dependency (normal line)
                    mermaid.append("    n{} --> n{};".format(u, v))
            
            return "\n".join(mermaid)
            
        else:
            logger.error(f"Unsupported visualization format: {format}")
            return None
        
    def calculate_efficiency_metrics(self):
        """
        Calculate efficiency metrics for the production flow
        
        Returns:
            Dict with efficiency metrics
        """
        if not self.graph:
            return {}
            
        # Get critical path
        critical_path = self.get_critical_path()
        
        # Calculate total planned duration
        min_start = None
        max_end = None
        
        for node_id in self.graph.nodes():
            attrs = self.graph.nodes[node_id]
            start = attrs.get('start')
            end = attrs.get('end')
            
            if start and (min_start is None or start < min_start):
                min_start = start
                
            if end and (max_end is None or end > max_end):
                max_end = end
        
        # Calculate metrics
        metrics = {
            'node_count': len(self.graph.nodes()),
            'edge_count': len(self.graph.edges()),
            'critical_path_length': len(critical_path),
            'disconnected_components': nx.number_weakly_connected_components(self.graph)
        }
        
        # Calculate timing metrics if available
        if min_start and max_end:
            total_duration = (max_end - min_start).total_seconds() / 3600  # hours
            metrics['total_duration_hours'] = round(total_duration, 2)
            
            # Calculate critical path duration
            critical_duration = 0
            for node_id in critical_path:
                attrs = self.graph.nodes[node_id]
                if attrs.get('start') and attrs.get('end'):
                    duration = (attrs['end'] - attrs['start']).total_seconds() / 3600
                    critical_duration += duration
            
            metrics['critical_path_duration'] = round(critical_duration, 2)
            
            # Calculate efficiency ratio (critical path / total duration)
            if total_duration > 0:
                metrics['efficiency_ratio'] = round(critical_duration / total_duration, 2)
            else:
                metrics['efficiency_ratio'] = 0
        
        return metrics

class MaterialRequirementsPlanning:
    """
    Utility class for material requirements planning in the production simulation
    """
    
    def __init__(self, session):
        """
        Initialize with a database session
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def calculate_material_requirements(self, product_id, quantity, date):
        """
        Calculate material requirements for a product
        
        Args:
            product_id: Product ID to calculate requirements for
            quantity: Quantity to produce
            date: Planned production date
            
        Returns:
            List of dicts with required materials and quantities
        """
        if not self.session:
            logger.error("No database session provided")
            return []
        
        # Get the BOM for this product
        query = """
        SELECT 
            bom.ComponentID,
            i.Name as ComponentName,
            i.Category as ComponentCategory,
            bom.Quantity,
            bom.ScrapFactor,
            i.LeadTime as LeadTimeInDays,
            i.Quantity as CurrentInventory,
            i.ReorderLevel,
            s.Name as SupplierName
        FROM 
            BillOfMaterials bom
        JOIN 
            Inventory i ON bom.ComponentID = i.ItemID
        LEFT JOIN 
            Suppliers s ON i.SupplierID = s.SupplierID
        WHERE 
            bom.ProductID = :product_id
        """
        
        result = self.session.execute(query, {'product_id': product_id})
        bom_items = [dict(row) for row in result]
        
        requirements = []
        
        for item in bom_items:
            # Calculate gross requirement including scrap
            gross_qty = item['Quantity'] * quantity * (1 + item['ScrapFactor'])
            
            # Round up to nearest integer
            gross_qty = int(gross_qty + 0.5)
            
            # Check against current inventory
            current_inventory = item['CurrentInventory'] or 0
            net_qty = max(0, gross_qty - current_inventory)
            
            # Calculate need date (production date minus lead time)
            lead_time = item['LeadTimeInDays'] or 0
            need_date = date - timedelta(days=lead_time)
            
            requirements.append({
                'component_id': item['ComponentID'],
                'component_name': item['ComponentName'],
                'category': item['ComponentCategory'],
                'supplier': item['SupplierName'],
                'gross_quantity': gross_qty,
                'net_quantity': net_qty,
                'current_inventory': current_inventory,
                'reorder_level': item['ReorderLevel'],
                'lead_time': lead_time,
                'need_date': need_date
            })
        
        return requirements
    
    def generate_dependent_orders(self, product_id, quantity, date, lot_number=None):
        """
        Generate a list of dependent work orders for a product
        
        Args:
            product_id: Product ID to calculate requirements for
            quantity: Quantity to produce
            date: Planned production date
            lot_number: Optional lot number for traceability
            
        Returns:
            List of dicts representing work orders to create
        """
        if not self.session:
            logger.error("No database session provided")
            return []
        
        # Get product info
        product_query = """
        SELECT 
            p.Name as ProductName,
            p.Category as ProductCategory,
            p.StandardProcessTime
        FROM 
            Products p
        WHERE 
            p.ProductID = :product_id
        """
        
        product_result = self.session.execute(product_query, {'product_id': product_id})
        product = dict(product_result.fetchone() or {})
        
        if not product:
            logger.error(f"Product ID {product_id} not found")
            return []
        
        # Calculate requirements
        requirements = self.calculate_material_requirements(product_id, quantity, date)
        
        # Find components that need to be manufactured (vs. raw materials)
        manufactured_components = []
        
        for req in requirements:
            if req['category'] in ['Component', 'Subassembly']:
                # Find product ID for this component
                component_query = """
                SELECT 
                    p.ProductID,
                    p.Name,
                    p.StandardProcessTime
                FROM 
                    Products p
                WHERE 
                    p.Name = :component_name
                """
                
                comp_result = self.session.execute(component_query, {'component_name': req['component_name']})
                component = dict(comp_result.fetchone() or {})
                
                if component:
                    manufactured_components.append({
                        'product_id': component['ProductID'],
                        'product_name': component['Name'],
                        'quantity': req['gross_quantity'],
                        'need_date': req['need_date'],
                        'process_time': component['StandardProcessTime']
                    })
        
        # Create dependant work orders
        dependent_orders = []
        
        for component in manufactured_components:
            # Find appropriate work centers for this component
            work_center_query = """
            SELECT 
                wc.WorkCenterID,
                wc.Name as WorkCenterName,
                wc.Capacity,
                wc.CapacityUOM
            FROM 
                WorkCenters wc
            JOIN 
                Machines m ON wc.WorkCenterID = m.WorkCenterID
            WHERE 
                m.Type IN (
                    SELECT m2.Type
                    FROM WorkOrders wo
                    JOIN Machines m2 ON wo.MachineID = m2.MachineID
                    JOIN Products p ON wo.ProductID = p.ProductID
                    WHERE p.Name = :product_name
                    GROUP BY m2.Type
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )
            LIMIT 1
            """
            
            wc_result = self.session.execute(work_center_query, {'product_name': component['product_name']})
            work_center = dict(wc_result.fetchone() or {})
            
            if not work_center:
                # Fallback to any work center
                wc_result = self.session.execute("SELECT WorkCenterID, Name FROM WorkCenters LIMIT 1")
                work_center = dict(wc_result.fetchone() or {})
                
                if not work_center:
                    logger.error("No work centers found")
                    continue
            
            # Calculate process time based on quantity and standard time
            process_hours = component['process_time'] * (component['quantity'] / 100)
            
            # Create work order
            order = {
                'product_id': component['product_id'],
                'product_name': component['product_name'],
                'work_center_id': work_center['WorkCenterID'],
                'work_center_name': work_center.get('WorkCenterName', 'Unknown'),
                'quantity': component['quantity'],
                'planned_start': component['need_date'] - timedelta(hours=process_hours),
                'planned_end': component['need_date'],
                'lot_number': lot_number or f"LOT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            }
            
            dependent_orders.append(order)
        
        return dependent_orders
    
    def check_material_availability(self, product_id, quantity):
        """
        Check if there are enough materials in inventory for a work order
        
        Args:
            product_id: Product ID to check
            quantity: Desired quantity
            
        Returns:
            Dict with availability status
        """
        requirements = self.calculate_material_requirements(product_id, quantity, datetime.now())
        
        if not requirements:
            return {"available": True, "max_possible": quantity, "shortages": []}
            
        # Calculate the maximum possible quantity based on inventory
        max_possible = quantity
        shortages = []
        
        for req in requirements:
            # If net quantity > 0, we need more of this component
            if req['net_quantity'] > 0:
                possible = req['current_inventory'] / (req['gross_quantity'] / quantity)
                if possible < max_possible:
                    max_possible = int(possible)
                    
                shortages.append({
                    'component_name': req['component_name'],
                    'required': req['gross_quantity'],
                    'available': req['current_inventory'],
                    'shortage': req['net_quantity'],
                    'lead_time': req['lead_time'],
                    'supplier': req['supplier']
                })
        
        # If max_possible is 0, we can't make any
        if max_possible <= 0:
            max_possible = 0
            
        return {
            "available": max_possible >= quantity,
            "max_possible": max_possible,
            "shortages": shortages
        }
    
    def generate_purchase_requisitions(self, product_id, quantity, date):
        """
        Generate purchase requisitions for materials needed
        
        Args:
            product_id: Product ID to produce
            quantity: Planned quantity
            date: Production date
            
        Returns:
            List of purchase requisitions
        """
        # Calculate requirements
        requirements = self.calculate_material_requirements(product_id, quantity, date)
        
        # Filter to items with net requirements > 0
        needed_items = [req for req in requirements if req['net_quantity'] > 0]
        
        # Generate requisitions
        requisitions = []
        
        for item in needed_items:
            # Add some buffer to the quantity (10-20%)
            buffer_factor = random.uniform(1.1, 1.2)
            order_quantity = int(item['net_quantity'] * buffer_factor)
            
            # Need date is production date minus lead time
            need_date = date - timedelta(days=item['lead_time'])
            
            # Order date should be today or in the past
            order_date = min(datetime.now(), need_date - timedelta(days=1))
            
            requisitions.append({
                'component_id': item['component_id'],
                'component_name': item['component_name'],
                'supplier': item['supplier'],
                'quantity': order_quantity,
                'order_date': order_date,
                'need_date': need_date,
                'status': 'Pending'
            })
        
        return requisitions

def analyze_production_flow(db_connection):
    """
    Analyze the production flow and identify bottlenecks
    
    Args:
        db_connection: Database connection
        
    Returns:
        DataFrame with work center performance metrics
    """
    # Query work center throughput
    throughput_query = """
    SELECT 
        wc.Name as WorkCenter,
        COUNT(DISTINCT wo.OrderID) as OrderCount,
        AVG(wo.ActualProduction) as AvgProduction,
        SUM(
            CASE 
                WHEN wo.ActualStartTime IS NOT NULL AND wo.ActualEndTime IS NOT NULL
                THEN (julianday(wo.ActualEndTime) - julianday(wo.ActualStartTime)) * 24
                ELSE NULL
            END
        ) / NULLIF(COUNT(wo.ActualEndTime), 0) as AvgProcessHours,
        COUNT(
            CASE 
                WHEN wo.Status = 'in_progress' THEN 1 
                ELSE NULL
            END
        ) as InProgressOrders,
        SUM(wo.Quantity) as TotalScheduled,
        SUM(wo.ActualProduction) as TotalProduced
    FROM 
        WorkOrders wo
    JOIN 
        WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
    WHERE 
        wo.PlannedStartTime >= date('now', '-30 day')
    GROUP BY 
        wc.Name
    """
    
    throughput_df = pd.read_sql(throughput_query, db_connection)
    
    # Query downtime by work center
    downtime_query = """
    SELECT 
        wc.Name as WorkCenter,
        SUM(d.Duration) as TotalDowntimeMinutes,
        COUNT(d.DowntimeID) as DowntimeEvents,
        AVG(d.Duration) as AvgDowntimeDuration
    FROM 
        Downtimes d
    JOIN 
        Machines m ON d.MachineID = m.MachineID
    JOIN 
        WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
    WHERE 
        d.StartTime >= date('now', '-30 day')
    GROUP BY 
        wc.Name
    """
    
    downtime_df = pd.read_sql(downtime_query, db_connection)
    
    # Query quality by work center
    quality_query = """
    SELECT 
        wc.Name as WorkCenter,
        AVG(qc.DefectRate) * 100 as AvgDefectRate,
        AVG(qc.YieldRate) * 100 as AvgYieldRate
    FROM 
        QualityControl qc
    JOIN 
        WorkOrders wo ON qc.OrderID = wo.OrderID
    JOIN 
        WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
    WHERE 
        qc.Date >= date('now', '-30 day')
    GROUP BY 
        wc.Name
    """
    
    quality_df = pd.read_sql(quality_query, db_connection)
    
    # Merge all data
    merged_df = (throughput_df
                .merge(downtime_df, on='WorkCenter', how='left')
                .merge(quality_df, on='WorkCenter', how='left'))
    
    # Calculate completion rate
    merged_df['CompletionRate'] = merged_df['TotalProduced'] / merged_df['TotalScheduled'] * 100
    
    # Fill NAs
    merged_df = merged_df.fillna({
        'TotalDowntimeMinutes': 0,
        'DowntimeEvents': 0,
        'AvgDowntimeDuration': 0,
        'AvgDefectRate': 0,
        'AvgYieldRate': 100,
        'AvgProcessHours': 0
    })
    
    # Calculate bottleneck score
    # Higher score = more likely to be a bottleneck
    # Formula: (0.3 * normalized in-progress) + (0.3 * normalized process time) + 
    #          (0.2 * normalized downtime) + (0.2 * normalized defect rate)
    
    # Normalize metrics
    if merged_df['InProgressOrders'].max() > 0:
        merged_df['NormInProgress'] = merged_df['InProgressOrders'] / merged_df['InProgressOrders'].max()
    else:
        merged_df['NormInProgress'] = 0
        
    if merged_df['AvgProcessHours'].max() > 0:
        merged_df['NormProcessHours'] = merged_df['AvgProcessHours'] / merged_df['AvgProcessHours'].max()
    else:
        merged_df['NormProcessHours'] = 0
        
    if merged_df['TotalDowntimeMinutes'].max() > 0:
        merged_df['NormDowntime'] = merged_df['TotalDowntimeMinutes'] / merged_df['TotalDowntimeMinutes'].max()
    else:
        merged_df['NormDowntime'] = 0
        
    if merged_df['AvgDefectRate'].max() > 0:
        merged_df['NormDefectRate'] = merged_df['AvgDefectRate'] / merged_df['AvgDefectRate'].max()
    else:
        merged_df['NormDefectRate'] = 0
    
    # Calculate bottleneck score
    merged_df['BottleneckScore'] = (
        0.3 * merged_df['NormInProgress'] +
        0.3 * merged_df['NormProcessHours'] +
        0.2 * merged_df['NormDowntime'] +
        0.2 * merged_df['NormDefectRate']
    )
    
    # Sort by bottleneck score
    return merged_df.sort_values('BottleneckScore', ascending=False)

def get_active_work_orders(db_connection, work_center=None, status=None, lot_number=None):
    """
    Get active work orders with filtering options
    
    Args:
        db_connection: Database connection
        work_center (str, optional): Filter by work center name
        status (str, optional): Filter by status ('scheduled', 'in_progress', etc.)
        lot_number (str, optional): Filter by lot number
        
    Returns:
        DataFrame with work order details
    """
    # Build query with optional filters
    query = """
    SELECT 
        wo.OrderID,
        p.Name as ProductName,
        p.Category as ProductCategory,
        wc.Name as WorkCenterName,
        m.Name as MachineName,
        e.Name as EmployeeName,
        wo.Quantity,
        wo.PlannedStartTime,
        wo.PlannedEndTime,
        wo.ActualStartTime,
        wo.ActualEndTime,
        wo.Status,
        wo.Priority,
        wo.LotNumber,
        wo.ActualProduction,
        wo.Scrap
    FROM 
        WorkOrders wo
    JOIN 
        Products p ON wo.ProductID = p.ProductID
    JOIN 
        WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
    JOIN 
        Machines m ON wo.MachineID = m.MachineID
    JOIN 
        Employees e ON wo.EmployeeID = e.EmployeeID
    WHERE 
        1=1
    """
    
    if work_center:
        query += f" AND wc.Name = '{work_center}'"
    
    if status:
        query += f" AND wo.Status = '{status}'"
    
    if lot_number:
        query += f" AND wo.LotNumber = '{lot_number}'"
    
    # Add order by for consistent results
    query += " ORDER BY wo.PlannedStartTime DESC"
    
    # Execute query
    return pd.read_sql(query, db_connection)

def calculate_production_kpis(db_connection, start_date=None, end_date=None):
    """
    Calculate key production KPIs
    
    Args:
        db_connection: Database connection
        start_date: Optional start date for analysis
        end_date: Optional end date for analysis
        
    Returns:
        Dict with KPI values
    """
    # Default to last 30 days if not specified
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
        
    # Format dates for query
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Production volume KPIs
    volume_query = f"""
    SELECT
        COUNT(wo.OrderID) as TotalOrders,
        SUM(wo.Quantity) as TotalPlanned,
        SUM(wo.ActualProduction) as TotalProduced,
        SUM(wo.Scrap) as TotalScrap,
        ROUND(SUM(wo.ActualProduction) * 100.0 / NULLIF(SUM(wo.Quantity), 0), 2) as CompletionRate,
        COUNT(DISTINCT wo.LotNumber) as TotalLots
    FROM
        WorkOrders wo
    WHERE
        wo.Status = 'completed'
        AND wo.ActualEndTime BETWEEN '{start_str}' AND '{end_str}'
    """
    
    volume_df = pd.read_sql(volume_query, db_connection)
    volume_kpis = {}
    
    if not volume_df.empty:
        volume_kpis = volume_df.iloc[0].to_dict()
    
    # Quality KPIs
    quality_query = f"""
    SELECT
        ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
        ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
        ROUND(AVG(qc.ReworkRate) * 100, 2) as AvgReworkRate,
        SUM(CASE WHEN qc.Result = 'pass' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as FirstPassYield
    FROM
        QualityControl qc
    WHERE
        qc.Date BETWEEN '{start_str}' AND '{end_str}'
    """
    
    quality_df = pd.read_sql(quality_query, db_connection)
    quality_kpis = {}
    
    if not quality_df.empty:
        quality_kpis = quality_df.iloc[0].to_dict()
    
    # OEE KPIs
    oee_query = f"""
    SELECT
        ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
        ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
        ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality,
        ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE
    FROM
        OEEMetrics oee
    WHERE
        oee.Date BETWEEN '{start_str}' AND '{end_str}'
    """
    
    oee_df = pd.read_sql(oee_query, db_connection)
    oee_kpis = {}
    
    if not oee_df.empty:
        oee_kpis = oee_df.iloc[0].to_dict()
    
    # Lead time KPIs
    leadtime_query = f"""
    SELECT
        AVG(julianday(wo.ActualEndTime) - julianday(wo.ActualStartTime)) * 24 as AvgLeadTimeHours,
        AVG((julianday(wo.ActualEndTime) - julianday(wo.ActualStartTime)) / 
            (julianday(wo.PlannedEndTime) - julianday(wo.PlannedStartTime))) as LeadTimeRatio
    FROM
        WorkOrders wo
    WHERE
        wo.Status = 'completed'
        AND wo.ActualEndTime BETWEEN '{start_str}' AND '{end_str}'
    """
    
    leadtime_df = pd.read_sql(leadtime_query, db_connection)
    leadtime_kpis = {}
    
    if not leadtime_df.empty:
        leadtime_kpis = leadtime_df.iloc[0].to_dict()
    
    # Combine all KPIs
    kpis = {
        'volume': volume_kpis,
        'quality': quality_kpis,
        'oee': oee_kpis,
        'leadtime': leadtime_kpis,
        'date_range': {
            'start_date': start_date,
            'end_date': end_date,
            'days': (end_date - start_date).days
        }
    }
    
    return kpis

def identify_critical_materials(db_connection):
    """
    Identify critical materials based on consumption and inventory levels
    
    Args:
        db_connection: Database connection
        
    Returns:
        DataFrame with critical materials
    """
    # Query inventory levels and consumption
    query = """
    SELECT
        i.ItemID,
        i.Name,
        i.Category,
        i.Quantity as CurrentQuantity,
        i.ReorderLevel,
        i.LeadTime,
        s.Name as SupplierName,
        (SELECT SUM(mc.ActualQuantity) 
         FROM MaterialConsumption mc 
         WHERE mc.ItemID = i.ItemID 
           AND mc.ConsumptionDate >= date('now', '-30 day')
        ) as Consumption30Days
    FROM
        Inventory i
    LEFT JOIN
        Suppliers s ON i.SupplierID = s.SupplierID
    """
    
    materials_df = pd.read_sql(query, db_connection)
    
    # Calculate metrics
    materials_df['Consumption30Days'] = materials_df['Consumption30Days'].fillna(0)
    
    # Calculate days of supply
    materials_df['DailyConsumption'] = materials_df['Consumption30Days'] / 30
    materials_df['DaysOfSupply'] = np.where(
        materials_df['DailyConsumption'] > 0,
        materials_df['CurrentQuantity'] / materials_df['DailyConsumption'],
        float('inf')
    )
    
    # Calculate coverage ratio (current qty / reorder level)
    materials_df['CoverageRatio'] = materials_df['CurrentQuantity'] / materials_df['ReorderLevel']
    
    # Identify critical materials (low days of supply or below reorder)
    materials_df['IsCritical'] = (
        (materials_df['DaysOfSupply'] < materials_df['LeadTime']) | 
        (materials_df['CurrentQuantity'] < materials_df['ReorderLevel'])
    )
    
    # Sort by criticality
    critical_materials = materials_df[materials_df['IsCritical']].sort_values(
        by=['DaysOfSupply', 'CoverageRatio']
    )
    
    return critical_materials

def analyze_lot_based_production(db_connection, lookback_days=90):
    """
    Analyze production by lot number to identify flow issues
    
    Args:
        db_connection: Database connection
        lookback_days: Days to look back
        
    Returns:
        DataFrame with lot analysis
    """
    # Get date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    # Format dates for query
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Query lots and their work orders
    query = f"""
    WITH LotSummary AS (
        SELECT
            wo.LotNumber,
            COUNT(wo.OrderID) as OrderCount,
            MIN(wo.PlannedStartTime) as FirstPlannedStart,
            MAX(wo.PlannedEndTime) as LastPlannedEnd,
            MIN(wo.ActualStartTime) as FirstActualStart,
            MAX(wo.ActualEndTime) as LastActualEnd,
            MAX(p.Name) as MainProduct,
            MAX(CASE WHEN p.Category = 'Electric Bikes' THEN wo.Quantity ELSE 0 END) as PlannedQuantity,
            SUM(CASE WHEN p.Category = 'Electric Bikes' THEN wo.ActualProduction ELSE 0 END) as ActualProduction
        FROM
            WorkOrders wo
        JOIN
            Products p ON wo.ProductID = p.ProductID
        WHERE
            wo.LotNumber IS NOT NULL
            AND wo.PlannedStartTime BETWEEN '{start_str}' AND '{end_str}'
        GROUP BY
            wo.LotNumber
        HAVING
            OrderCount > 1  -- Only include lots with multiple orders
    )
    SELECT
        ls.*,
        julianday(ls.LastPlannedEnd) - julianday(ls.FirstPlannedStart) as PlannedLeadTimeDays,
        CASE
            WHEN ls.LastActualEnd IS NOT NULL AND ls.FirstActualStart IS NOT NULL
            THEN julianday(ls.LastActualEnd) - julianday(ls.FirstActualStart)
            ELSE NULL
        END as ActualLeadTimeDays,
        CASE
            WHEN ls.ActualProduction IS NOT NULL AND ls.PlannedQuantity > 0
            THEN ls.ActualProduction * 100.0 / ls.PlannedQuantity
            ELSE NULL
        END as CompletionRate
    FROM
        LotSummary ls
    """
    
    lots_df = pd.read_sql(query, db_connection)
    
    # Calculate additional metrics
    if not lots_df.empty:
        # Determine lot status
        def get_lot_status(row):
            if pd.notna(row['LastActualEnd']):
                return 'Completed'
            elif pd.notna(row['FirstActualStart']):
                return 'In Progress'
            else:
                return 'Scheduled'
        
        lots_df['Status'] = lots_df.apply(get_lot_status, axis=1)
        
        # Calculate lead time ratio (actual/planned)
        lots_df['LeadTimeRatio'] = np.where(
            lots_df['PlannedLeadTimeDays'] > 0,
            lots_df['ActualLeadTimeDays'] / lots_df['PlannedLeadTimeDays'],
            None
        )
    
    return lots_df

def find_production_constraints(db_connection):
    """
    Find production constraints using Theory of Constraints approach
    
    Args:
        db_connection: Database connection
        
    Returns:
        Dict with constraint analysis
    """
    # 1. Analyze bottlenecks
    bottlenecks = analyze_production_flow(db_connection)
    
    # 2. Analyze capacity utilization
    utilization_query = """
    SELECT
        wc.WorkCenterID,
        wc.Name as WorkCenterName,
        wc.Capacity as NominalCapacity,
        wc.CapacityUOM,
        COUNT(DISTINCT wo.OrderID) as ActiveOrders,
        SUM(wo.Quantity) as TotalScheduledQuantity,
        SUM(CASE WHEN wo.Status = 'completed' THEN wo.ActualProduction ELSE 0 END) as CompletedQuantity,
        SUM(CASE WHEN wo.Status = 'in_progress' THEN wo.Quantity ELSE 0 END) as InProgressQuantity
    FROM
        WorkCenters wc
    LEFT JOIN
        WorkOrders wo ON wc.WorkCenterID = wo.WorkCenterID
               AND wo.Status IN ('scheduled', 'in_progress')
               AND wo.PlannedEndTime > datetime('now', '-1 day')
    GROUP BY
        wc.WorkCenterID, wc.Name, wc.Capacity, wc.CapacityUOM
    """
    
    utilization_df = pd.read_sql(utilization_query, db_connection)
    
    # Calculate utilization percentage
    utilization_df['UtilizationRate'] = np.where(
        utilization_df['NominalCapacity'] > 0,
        utilization_df['ActiveOrders'] / utilization_df['NominalCapacity'],
        0
    )
    
    # 3. Analyze inventory constraints
    critical_materials = identify_critical_materials(db_connection)
    
    # 4. Find the overall constraint
    constraint_types = {
        'capacity': None,
        'material': None,
        'quality': None
    }
    
    # Check for capacity constraints
    if not bottlenecks.empty and bottlenecks['BottleneckScore'].max() > 0.5:
        primary_bottleneck = bottlenecks.iloc[0]['WorkCenter']
        constraint_types['capacity'] = {
            'work_center': primary_bottleneck,
            'bottleneck_score': bottlenecks.iloc[0]['BottleneckScore'],
            'in_progress_orders': bottlenecks.iloc[0]['InProgressOrders'],
            'avg_process_hours': bottlenecks.iloc[0]['AvgProcessHours']
        }
    
    # Check for material constraints
    if not critical_materials.empty:
        most_critical = critical_materials.iloc[0]
        constraint_types['material'] = {
            'item_name': most_critical['Name'],
            'days_of_supply': most_critical['DaysOfSupply'],
            'current_quantity': most_critical['CurrentQuantity'],
            'reorder_level': most_critical['ReorderLevel'],
            'lead_time': most_critical['LeadTime']
        }
    
    # Check for quality constraints
    quality_query = """
    SELECT
        p.Name as ProductName,
        wc.Name as WorkCenterName,
        AVG(qc.DefectRate) * 100 as AvgDefectRate,
        AVG(qc.ReworkRate) * 100 as AvgReworkRate
    FROM
        QualityControl qc
    JOIN
        WorkOrders wo ON qc.OrderID = wo.OrderID
    JOIN
        Products p ON wo.ProductID = p.ProductID
    JOIN
        WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
    WHERE
        qc.Date >= date('now', '-30 day')
    GROUP BY
        p.Name, wc.Name
    HAVING
        AVG(qc.DefectRate) > 0.1  -- More than 10% defects
    ORDER BY
        AVG(qc.DefectRate) DESC
    LIMIT 1
    """
    
    quality_df = pd.read_sql(quality_query, db_connection)
    
    if not quality_df.empty:
        constraint_types['quality'] = {
            'product_name': quality_df.iloc[0]['ProductName'],
            'work_center': quality_df.iloc[0]['WorkCenterName'],
            'defect_rate': quality_df.iloc[0]['AvgDefectRate'],
            'rework_rate': quality_df.iloc[0]['AvgReworkRate']
        }
    
    # Determine the primary constraint
    primary_constraint = None
    constraint_reason = None
    
    if constraint_types['capacity'] and (
        constraint_types['capacity']['bottleneck_score'] > 0.7 or
        constraint_types['capacity']['in_progress_orders'] > 5
    ):
        primary_constraint = 'capacity'
        constraint_reason = f"Work center {constraint_types['capacity']['work_center']} is the primary constraint with bottleneck score {constraint_types['capacity']['bottleneck_score']:.2f}"
    elif constraint_types['material'] and constraint_types['material']['days_of_supply'] < 3:
        primary_constraint = 'material'
        constraint_reason = f"Material {constraint_types['material']['item_name']} is critically low with only {constraint_types['material']['days_of_supply']:.1f} days of supply"
    elif constraint_types['quality'] and constraint_types['quality']['defect_rate'] > 15:
        primary_constraint = 'quality'
        constraint_reason = f"Quality issues with {constraint_types['quality']['product_name']} at {constraint_types['quality']['work_center']} with defect rate {constraint_types['quality']['defect_rate']:.1f}%"
    else:
        # Default to most likely constraint
        if constraint_types['capacity']:
            primary_constraint = 'capacity'
            constraint_reason = f"Work center {constraint_types['capacity']['work_center']} is the likely constraint"
    
    # Compile results
    results = {
        'primary_constraint': primary_constraint,
        'constraint_reason': constraint_reason,
        'constraint_types': constraint_types,
        'bottlenecks': bottlenecks.head(3).to_dict('records') if not bottlenecks.empty else [],
        'utilization': utilization_df.sort_values('UtilizationRate', ascending=False).head(3).to_dict('records') if not utilization_df.empty else [],
        'critical_materials': critical_materials.head(3).to_dict('records') if not critical_materials.empty else []
    }
    
    return results

def get_optimal_production_sequence(db_connection, work_center_id, date=None):
    """
    Calculate optimal production sequence for a work center to minimize changeover
    
    Args:
        db_connection: Database connection
        work_center_id: Work center ID
        date: Optional date to schedule (defaults to today)
        
    Returns:
        DataFrame with optimized sequence
    """
    if not date:
        date = datetime.now()
        
    date_str = date.strftime('%Y-%m-%d')
    
    # Get scheduled orders for the work center
    query = f"""
    SELECT
        wo.OrderID,
        p.ProductID,
        p.Name as ProductName,
        p.Category as ProductCategory,
        wo.Quantity,
        wo.PlannedStartTime,
        wo.PlannedEndTime,
        wo.Priority,
        wo.Status
    FROM
        WorkOrders wo
    JOIN
        Products p ON wo.ProductID = p.ProductID
    JOIN
        WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
    WHERE
        wc.WorkCenterID = {work_center_id}
        AND wo.Status = 'scheduled'
        AND date(wo.PlannedStartTime) = '{date_str}'
    ORDER BY
        wo.Priority, wo.PlannedStartTime
    """
    
    orders_df = pd.read_sql(query, db_connection)
    
    if orders_df.empty:
        return pd.DataFrame()
    
    # Get machine for the work center
    machine_query = f"""
    SELECT
        m.MachineID,
        m.Name as MachineName,
        m.ProductChangeoverTime
    FROM
        Machines m
    WHERE
        m.WorkCenterID = {work_center_id}
    LIMIT 1
    """
    
    machine_df = pd.read_sql(machine_query, db_connection)
    
    if machine_df.empty:
        machine_changeover_time = 30  # Default 30 minutes
    else:
        machine_changeover_time = machine_df.iloc[0]['ProductChangeoverTime']
    
    # Determine product families for more efficient sequencing
    def get_product_family(product_name):
        if 'eBike' in product_name:
            return 'eBikes'
        elif any(x in product_name for x in ['Frame', 'Fork']):
            return 'Frames'
        elif any(x in product_name for x in ['Wheel', 'Tire']):
            return 'Wheels'
        elif any(x in product_name for x in ['Battery', 'Motor', 'Control']):
            return 'Electronics'
        else:
            return 'Components'
    
    orders_df['ProductFamily'] = orders_df['ProductName'].apply(get_product_family)
    
    # Create a simple optimization - minimize changeovers while respecting priority
    # First sort by priority (most important)
    orders_df = orders_df.sort_values('Priority')
    
    # Within each priority level, group by product family to minimize changeovers
    optimized_orders = []
    
    for priority_level in orders_df['Priority'].unique():
        priority_orders = orders_df[orders_df['Priority'] == priority_level]
        
        # Group by product family
        for family in priority_orders['ProductFamily'].unique():
            family_orders = priority_orders[priority_orders['ProductFamily'] == family]
            optimized_orders.append(family_orders)
    
    # Combine the optimized sequence
    optimized_df = pd.concat(optimized_orders)
    
    # Calculate changeover times and updated schedule
    start_time = datetime.strptime(f"{date_str} 08:00:00", "%Y-%m-%d %H:%M:%S")  # Start at 8 AM
    
    schedule = []
    prev_family = None
    
    for _, order in optimized_df.iterrows():
        # Add changeover time if needed
        if prev_family and prev_family != order['ProductFamily']:
            start_time += timedelta(minutes=machine_changeover_time)
        
        # Calculate process time based on quantity and product
        # This is a simplification - in reality would use standard times from product
        process_minutes = order['Quantity'] * 0.5  # 30 seconds per unit as example
        end_time = start_time + timedelta(minutes=process_minutes)
        
        schedule.append({
            'OrderID': order['OrderID'],
            'ProductName': order['ProductName'],
            'ProductFamily': order['ProductFamily'],
            'Quantity': order['Quantity'],
            'Priority': order['Priority'],
            'ScheduledStart': start_time,
            'ScheduledEnd': end_time,
            'Duration': process_minutes
        })
        
        # Update for next order
        start_time = end_time
        prev_family = order['ProductFamily']
    
    return pd.DataFrame(schedule)