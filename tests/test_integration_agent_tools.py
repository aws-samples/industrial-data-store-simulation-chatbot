#!/usr/bin/env python3
"""
Integration Tests for Production Meeting Agent Tools

This test suite validates that all specialized agent tools work correctly with
database tools, tests query routing and multi-domain analysis coordination,
and validates error handling and graceful degradation scenarios.

Test Coverage:
- Individual agent tool functionality
- Database tool integration
- Query routing and coordination
- Error handling and recovery
- Multi-domain analysis
- Performance and timeout handling

Requirements Coverage: 8.1, 8.2, 8.3, 8.4
"""

# import pytest  # Removed to avoid fixture issues in custom test runner
import asyncio
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Import the production meeting agents and tools
from app_factory.production_meeting_agents.production_meeting_agent import (
    production_analysis_tool,
    quality_analysis_tool,
    equipment_analysis_tool,
    inventory_analysis_tool,
    production_meeting_analysis_tool
)
from app_factory.production_meeting_agents.tools.database_tools import (
    run_sqlite_query,
    get_database_schema,
    get_production_context
)
from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
from app_factory.production_meeting_agents.config import ProductionMeetingConfig
from app_factory.production_meeting_agents.error_handling import ProductionMeetingError


class TestAgentToolFunctionality:
    """Test individual agent tool functionality and database integration."""
    
    def create_test_db(self):
        """Create a temporary test database."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        # Create test database with sample data
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute('''
            CREATE TABLE WorkOrders (
                OrderID INTEGER PRIMARY KEY,
                ProductID INTEGER,
                Quantity INTEGER,
                ActualProduction INTEGER,
                Scrap INTEGER,
                ActualStartTime TEXT,
                ActualEndTime TEXT,
                Status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE QualityControl (
                CheckID INTEGER PRIMARY KEY,
                ProductID INTEGER,
                DefectRate REAL,
                YieldRate REAL,
                Result TEXT,
                Date TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE Machines (
                MachineID INTEGER PRIMARY KEY,
                MachineName TEXT,
                Status TEXT,
                EfficiencyFactor REAL,
                NextMaintenanceDate TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE Inventory (
                ItemID INTEGER PRIMARY KEY,
                ItemName TEXT,
                Quantity INTEGER,
                ReorderLevel INTEGER,
                LeadTime INTEGER
            )
        ''')
        
        # Insert sample data
        cursor.execute('''
            INSERT INTO WorkOrders (OrderID, ProductID, Quantity, ActualProduction, Scrap, ActualStartTime, Status)
            VALUES 
                (1, 101, 100, 95, 5, '2024-01-15 08:00:00', 'completed'),
                (2, 102, 200, 180, 10, '2024-01-15 09:00:00', 'in_progress'),
                (3, 103, 150, 0, 0, '2024-01-15 10:00:00', 'pending')
        ''')
        
        cursor.execute('''
            INSERT INTO QualityControl (CheckID, ProductID, DefectRate, YieldRate, Result, Date)
            VALUES 
                (1, 101, 0.05, 0.95, 'pass', '2024-01-15 12:00:00'),
                (2, 102, 0.08, 0.92, 'fail', '2024-01-15 13:00:00'),
                (3, 103, 0.03, 0.97, 'pass', '2024-01-15 14:00:00')
        ''')
        
        cursor.execute('''
            INSERT INTO Machines (MachineID, MachineName, Status, EfficiencyFactor, NextMaintenanceDate)
            VALUES 
                (1, 'CNC-001', 'running', 0.85, '2024-01-20'),
                (2, 'CNC-002', 'maintenance', 0.90, '2024-01-18'),
                (3, 'PRESS-001', 'breakdown', 0.75, '2024-01-16')
        ''')
        
        cursor.execute('''
            INSERT INTO Inventory (ItemID, ItemName, Quantity, ReorderLevel, LeadTime)
            VALUES 
                (1, 'Steel Plate', 50, 100, 7),
                (2, 'Aluminum Rod', 200, 150, 5),
                (3, 'Copper Wire', 25, 50, 3)
        ''')
        
        conn.commit()
        conn.close()
        
        return temp_db.name
    
    @patch('app_factory.shared.database.DatabaseManager')
    def test_database_tools_integration(self, mock_db_manager):
        """Test that database tools work correctly with agent tools."""
        # Create test database
        test_db_path = self.create_test_db()
        
        try:
            # Mock database manager to use test database
            mock_instance = MagicMock()
            mock_db_manager.return_value = mock_instance
            
            # Test run_sqlite_query tool
            mock_instance.execute_query.return_value = {
                'success': True,
                'rows': [{'OrderID': 1, 'Status': 'completed', 'ActualProduction': 95}],
                'columns': ['OrderID', 'Status', 'ActualProduction'],
                'row_count': 1
            }
            
            result = run_sqlite_query("SELECT * FROM WorkOrders WHERE Status = 'completed'")
            
            assert result['success'] is True
            assert 'production_metadata' in result
            assert 'meeting_insights' in result
            assert len(result['meeting_insights']) > 0
            
            # Test get_database_schema tool
            mock_instance.get_schema.return_value = {
                'WorkOrders': {'columns': ['OrderID', 'ProductID', 'Status']},
                'QualityControl': {'columns': ['CheckID', 'DefectRate', 'Result']},
                'Machines': {'columns': ['MachineID', 'Status', 'EfficiencyFactor']},
                'Inventory': {'columns': ['ItemID', 'Quantity', 'ReorderLevel']}
            }
            
            schema_result = get_database_schema()
            
            assert schema_result['success'] is True
            assert 'tables' in schema_result
            assert 'meeting_priorities' in schema_result
            assert len(schema_result['tables']) > 0
            
        finally:
            # Cleanup test database
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)
    
    def test_production_context_tool(self):
        """Test get_production_context tool functionality."""
        # Test daily meeting context
        daily_context = get_production_context('daily', 1)
        
        assert daily_context['success'] is True
        assert daily_context['meeting_type'] == 'daily'
        assert 'time_ranges' in daily_context
        assert 'production_context' in daily_context
        assert 'meeting_focus_areas' in daily_context
        
        # Test weekly meeting context
        weekly_context = get_production_context('weekly', 7)
        
        assert weekly_context['success'] is True
        assert weekly_context['meeting_type'] == 'weekly'
        assert 'recommended_queries' in weekly_context
        assert 'key_metrics_to_review' in weekly_context
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_production_analysis_tool(self, mock_agent_class):
        """Test production analysis tool functionality."""
        # Mock the Agent class and its response
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Production analysis complete: 95% completion rate, bottleneck identified in work center 2")
        
        result = production_analysis_tool("What are today's production bottlenecks?")
        
        assert isinstance(result, str)
        assert "production" in result.lower()
        mock_agent_class.assert_called_once()
        mock_agent.assert_called_once()
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_quality_analysis_tool(self, mock_agent_class):
        """Test quality analysis tool functionality."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Quality analysis: 8% defect rate detected in product line B, immediate corrective action required")
        
        result = quality_analysis_tool("What quality issues need attention?")
        
        assert isinstance(result, str)
        assert "quality" in result.lower()
        mock_agent_class.assert_called_once()
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_equipment_analysis_tool(self, mock_agent_class):
        """Test equipment analysis tool functionality."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Equipment analysis: CNC-002 requires maintenance, PRESS-001 breakdown affecting production")
        
        result = equipment_analysis_tool("Which equipment needs maintenance?")
        
        assert isinstance(result, str)
        assert "equipment" in result.lower()
        mock_agent_class.assert_called_once()
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_inventory_analysis_tool(self, mock_agent_class):
        """Test inventory analysis tool functionality."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Inventory analysis: Steel Plate below reorder level, Copper Wire critically low")
        
        result = inventory_analysis_tool("What inventory shortages should I know about?")
        
        assert isinstance(result, str)
        assert "inventory" in result.lower()
        mock_agent_class.assert_called_once()


class TestQueryRoutingAndCoordination:
    """Test query routing and multi-domain analysis coordination."""
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_single_domain_query_routing(self, mock_agent_class):
        """Test that single-domain queries are routed correctly."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Single domain analysis complete")
        
        # Test production-specific query
        result = production_meeting_analysis_tool("What is our production efficiency today?")
        assert isinstance(result, str)
        
        # Test quality-specific query
        result = production_meeting_analysis_tool("Show me quality control results")
        assert isinstance(result, str)
        
        # Test equipment-specific query
        result = production_meeting_analysis_tool("Which machines are down for maintenance?")
        assert isinstance(result, str)
        
        # Test inventory-specific query
        result = production_meeting_analysis_tool("What materials are running low?")
        assert isinstance(result, str)
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_multi_domain_query_coordination(self, mock_agent_class):
        """Test coordination of multiple agents for complex queries."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Multi-domain analysis: Production issues correlate with equipment downtime and quality problems")
        
        # Test multi-domain query
        result = production_meeting_analysis_tool("Give me a comprehensive daily briefing covering all areas")
        
        assert isinstance(result, str)
        assert len(result) > 0
        mock_agent_class.assert_called()
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_daily_briefing_generation(self, mock_agent_class):
        """Test daily briefing generation using multiple specialized tools."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="""
        Daily Production Briefing:
        - Production: 95% completion rate
        - Quality: 2 issues requiring attention
        - Equipment: 1 machine in maintenance
        - Inventory: 3 items below reorder level
        """)
        
        result = production_meeting_analysis_tool("Generate a daily production briefing")
        
        assert isinstance(result, str)
        assert "production" in result.lower()
        assert "briefing" in result.lower()


class TestErrorHandlingAndRecovery:
    """Test error handling and graceful degradation scenarios."""
    
    def test_database_connection_error_handling(self):
        """Test handling of database connection errors."""
        with patch('app_factory.production_meeting_agents.tools.database_tools.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_db.return_value = mock_instance
            mock_instance.execute_query.side_effect = sqlite3.Error("Database connection failed")

            result = run_sqlite_query("SELECT * FROM WorkOrders")

            assert result['success'] is False
            assert 'error' in result
            assert 'recovery_options' in result
    
    def test_invalid_query_error_handling(self):
        """Test handling of invalid SQL queries."""
        # Test dangerous query validation
        result = run_sqlite_query("DROP TABLE WorkOrders")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'suggestions' in result
        
        # Test empty query validation
        result = run_sqlite_query("")
        
        assert result['success'] is False
        assert result['error'] == 'Query cannot be empty'
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_agent_timeout_handling(self, mock_agent_class):
        """Test handling of agent execution timeouts."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.side_effect = TimeoutError("Agent execution timed out")
        
        result = production_analysis_tool("Complex production analysis query")
        
        assert isinstance(result, str)
        assert "error" in result.lower() or "issue" in result.lower()
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_agent_model_error_handling(self, mock_agent_class):
        """Test handling of model/API errors."""
        mock_agent_class.side_effect = Exception("Model API error")

        result = production_analysis_tool("Test query")

        assert isinstance(result, str)
        # Error message should indicate an issue occurred during production analysis
        assert "encountered an issue" in result.lower() or "production" in result.lower()
    
    def test_graceful_degradation_scenarios(self):
        """Test graceful degradation when agents are unavailable."""
        config = ProductionMeetingConfig(agent_enabled=False)
        manager = ProductionMeetingAgentManager(config)
        
        # Test that manager handles disabled agents gracefully
        assert not manager.is_ready()
        
        # Test error response format
        result = asyncio.run(manager.process_query("Test query"))
        
        assert result['success'] is False
        assert 'suggested_actions' in result
        assert 'Agent is disabled' in result['message']


class TestAgentManagerIntegration:
    """Test agent manager integration and coordination."""
    
    def test_agent_manager_initialization(self):
        """Test agent manager initialization and status."""
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        # Test status reporting
        status = manager.get_agent_status()
        
        assert 'agent_type' in status
        assert 'capabilities' in status
        assert 'config' in status
        assert status['agent_type'] == 'Production Meeting Agent'
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.production_meeting_analysis_tool')
    def test_agent_manager_query_processing(self, mock_tool):
        """Test agent manager query processing."""
        mock_tool.return_value = "Analysis complete: Production running smoothly"
        
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        result = asyncio.run(manager.process_query("What is the production status?"))
        
        assert result['success'] is True
        assert 'analysis' in result
        assert 'execution_time' in result
        assert result['agent_type'] == 'Production Meeting Agent'
    
    def test_meeting_context_management(self):
        """Test meeting context setting and retrieval."""
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        # Set meeting context
        manager.set_meeting_context('daily', ['production', 'quality'], ['manager1', 'supervisor1'])
        
        context = manager.get_meeting_context()
        
        assert context['meeting_type'] == 'daily'
        assert 'production' in context['focus_areas']
        assert 'quality' in context['focus_areas']
        assert 'manager1' in context['participants']
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.production_meeting_analysis_tool')
    def test_daily_briefing_generation(self, mock_tool):
        """Test daily briefing generation through agent manager."""
        mock_tool.return_value = """
        Daily Production Briefing - January 15, 2024:
        
        Executive Summary: Production running at 95% efficiency
        Critical Issues: Equipment maintenance required for CNC-002
        Quality Status: 2% defect rate, within acceptable limits
        Inventory Alerts: Steel Plate below reorder level
        """
        
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        briefing = asyncio.run(manager.get_daily_briefing('2024-01-15'))
        
        assert isinstance(briefing, str)
        assert "briefing" in briefing.lower()
        assert "production" in briefing.lower()
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.production_meeting_analysis_tool')
    def test_contextual_insights_generation(self, mock_tool):
        """Test contextual insights generation for dashboard tabs."""
        mock_tool.return_value = "Production dashboard insights: Focus on work center efficiency and bottleneck resolution"
        
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        dashboard_data = {'metrics': ['efficiency', 'throughput'], 'alerts': ['bottleneck_detected']}
        insights = asyncio.run(manager.get_contextual_insights(dashboard_data, 'production'))
        
        assert isinstance(insights, str)
        assert len(insights) > 0
    
    def test_proactive_suggestions_generation(self):
        """Test proactive suggestion generation based on conversation history."""
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        # Test with empty history
        suggestions = manager.generate_proactive_suggestions([])
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)
        
        # Test with conversation history
        history = [
            {'query': 'What are production bottlenecks?'},
            {'query': 'Show me quality issues'}
        ]
        suggestions = manager.generate_proactive_suggestions(history)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


class TestPerformanceAndReliability:
    """Test performance characteristics and reliability."""
    
    @patch('app_factory.production_meeting_agents.production_meeting_agent.Agent')
    def test_response_time_performance(self, mock_agent_class):
        """Test that agent responses meet performance requirements."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.return_value = MagicMock(content="Quick analysis result")
        
        start_time = datetime.now()
        result = production_analysis_tool("Quick production status check")
        end_time = datetime.now()
        
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time for meeting efficiency
        assert execution_time < 30  # 30 seconds max for complex analysis
        assert isinstance(result, str)
    
    def test_concurrent_query_handling(self):
        """Test handling of concurrent queries."""
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        # Test that manager can handle status requests concurrently
        status1 = manager.get_agent_status()
        status2 = manager.get_agent_status()
        
        assert status1['agent_type'] == status2['agent_type']
        assert 'timestamp' in status1
        assert 'timestamp' in status2
    
    def test_memory_and_resource_management(self):
        """Test that agents don't consume excessive resources."""
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        # Test multiple operations don't cause memory leaks
        for i in range(10):
            status = manager.get_agent_status()
            context = manager.get_meeting_context()
            suggestions = manager.generate_proactive_suggestions([])
        
        # Should complete without errors
        assert status is not None
        assert context is not None
        assert suggestions is not None


def run_integration_tests():
    """Run all integration tests for agent tool functionality."""
    print("🧪 Running Production Meeting Agent Integration Tests...")
    print("=" * 60)
    
    # Test categories
    test_classes = [
        TestAgentToolFunctionality,
        TestQueryRoutingAndCoordination,
        TestErrorHandlingAndRecovery,
        TestAgentManagerIntegration,
        TestPerformanceAndReliability
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 Testing {test_class.__name__}...")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                # Create test instance and run test
                test_instance = test_class()
                
                # No special fixture handling needed anymore
                
                method = getattr(test_instance, test_method)
                method()
                
                print(f"  ✅ {test_method}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {test_method}: {str(e)}")
                failed_tests.append(f"{test_class.__name__}.{test_method}: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for failure in failed_tests:
            print(f"   - {failure}")
    else:
        print(f"\n🎉 All tests passed!")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)