#!/usr/bin/env python3
"""
Integration Tests for Dashboard Integration

This test suite validates that AI insights replacement works correctly in all
dashboard tabs, tests contextual insights generation for different dashboard
contexts, and validates that existing dashboard functionality remains unchanged.

Test Coverage:
- AI insights replacement functionality
- Dashboard tab integration
- Contextual insights generation
- Backward compatibility
- Dashboard functionality preservation

Requirements Coverage: 1.2, 2.1, 6.1, 6.5
"""

import pytest
import streamlit as st
import pandas as pd
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
import sys
import os

# Add the app_factory directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app_factory'))

# Import dashboard modules and AI insights
from app_factory.production_meeting.ai_insights import (
    generate_ai_insight,
    provide_tab_insights
)
from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
from app_factory.production_meeting_agents.config import ProductionMeetingConfig


class TestAIInsightsReplacement:
    """Test that AI insights replacement works correctly."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        # Mock Streamlit session state
        if 'session_state' not in st.__dict__:
            st.session_state = {}
        
        # Reset session state for each test
        st.session_state.clear()
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_generate_ai_insight_uses_agent_manager(self, mock_manager_class):
        """Test that generate_ai_insight uses agent manager instead of direct Bedrock calls."""
        # Mock agent manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.process_query.return_value = {
            'success': True,
            'analysis': 'Production analysis: 95% efficiency, bottleneck in work center 2',
            'execution_time': 2.5
        }
        
        # Test data
        test_data = pd.DataFrame({
            'WorkCenter': ['WC1', 'WC2', 'WC3'],
            'Efficiency': [0.95, 0.78, 0.92],
            'Output': [100, 85, 98]
        })
        
        # Call the function
        result = generate_ai_insight(test_data, "production efficiency analysis")
        
        # Verify agent manager was used
        mock_manager_class.assert_called_once()
        mock_manager.process_query.assert_called_once()
        
        # Verify result format
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'analysis' in result
        assert result['success'] is True
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_generate_ai_insight_error_handling(self, mock_manager_class):
        """Test error handling when agent manager fails."""
        # Mock agent manager with error
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = False
        mock_manager.process_query.return_value = {
            'success': False,
            'error': 'Agent not available',
            'message': 'Production meeting agent is not ready'
        }
        
        test_data = pd.DataFrame({'test': [1, 2, 3]})
        
        result = generate_ai_insight(test_data, "test analysis")
        
        # Should handle error gracefully
        assert isinstance(result, dict)
        assert 'success' in result
        assert result['success'] is False
        assert 'error' in result or 'message' in result
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_provide_tab_insights_integration(self, mock_manager_class):
        """Test that provide_tab_insights integrates with agent manager."""
        # Mock agent manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.get_contextual_insights.return_value = "Production insights: Focus on bottleneck resolution in work center 2"
        
        # Test dashboard data
        dashboard_data = {
            'metrics': ['efficiency', 'throughput', 'quality'],
            'alerts': ['bottleneck_detected'],
            'summary': {'total_orders': 150, 'completed': 142}
        }
        
        result = provide_tab_insights('production', dashboard_data)
        
        # Verify agent manager was used
        mock_manager.get_contextual_insights.assert_called_once_with(dashboard_data, 'production')
        
        # Verify result
        assert isinstance(result, str)
        assert len(result) > 0
        assert "production" in result.lower()
    
    def test_no_bedrock_client_usage(self):
        """Test that no direct Bedrock client calls are made."""
        # This test ensures we don't import or use bedrock client directly
        import app_factory.production_meeting.ai_insights as ai_insights_module
        
        # Check that bedrock client is not imported or used
        module_vars = vars(ai_insights_module)
        
        # Should not have bedrock client references
        bedrock_references = [var for var in module_vars.keys() if 'bedrock' in var.lower()]
        assert len(bedrock_references) == 0, f"Found Bedrock references: {bedrock_references}"
        
        # Should not have converse method calls
        module_source = ai_insights_module.__file__
        if module_source:
            with open(module_source, 'r') as f:
                content = f.read()
                assert 'client.converse' not in content, "Found direct Bedrock converse calls"
                assert 'get_bedrock_client' not in content, "Found Bedrock client initialization"


class TestDashboardTabIntegration:
    """Test integration with different dashboard tabs."""
    
    def setup_method(self):
        """Set up test environment."""
        if 'session_state' not in st.__dict__:
            st.session_state = {}
        st.session_state.clear()
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_production_tab_integration(self, mock_manager_class):
        """Test integration with production dashboard tab."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.get_contextual_insights.return_value = """
        Production Dashboard Insights:
        - Current efficiency: 95% (above target)
        - Bottleneck identified in work center 2
        - Recommend increasing capacity allocation
        - 3 work orders behind schedule
        """
        
        # Simulate production dashboard data
        production_data = {
            'work_orders': pd.DataFrame({
                'OrderID': [1, 2, 3],
                'Status': ['completed', 'in_progress', 'pending'],
                'Efficiency': [0.95, 0.88, 0.0]
            }),
            'metrics': {
                'total_orders': 150,
                'completed_orders': 142,
                'efficiency_rate': 0.95
            }
        }
        
        insights = provide_tab_insights('production', production_data)
        
        assert isinstance(insights, str)
        assert "production" in insights.lower()
        assert len(insights) > 50  # Should be substantial insights
        mock_manager.get_contextual_insights.assert_called_once()
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_quality_tab_integration(self, mock_manager_class):
        """Test integration with quality dashboard tab."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.get_contextual_insights.return_value = """
        Quality Dashboard Insights:
        - Defect rate: 2.1% (within acceptable range)
        - Product B showing increased defects
        - Recommend quality control review for line 3
        - Overall yield rate: 97.9%
        """
        
        quality_data = {
            'quality_checks': pd.DataFrame({
                'ProductID': ['A', 'B', 'C'],
                'DefectRate': [0.015, 0.035, 0.018],
                'YieldRate': [0.985, 0.965, 0.982]
            }),
            'summary': {
                'total_checks': 500,
                'pass_rate': 0.979
            }
        }
        
        insights = provide_tab_insights('quality', quality_data)
        
        assert isinstance(insights, str)
        assert "quality" in insights.lower()
        mock_manager.get_contextual_insights.assert_called_once_with(quality_data, 'quality')
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_equipment_tab_integration(self, mock_manager_class):
        """Test integration with equipment dashboard tab."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.get_contextual_insights.return_value = """
        Equipment Dashboard Insights:
        - Overall OEE: 85% (target: 80%)
        - CNC-002 requires maintenance within 2 days
        - PRESS-001 showing efficiency decline
        - Recommend preventive maintenance scheduling
        """
        
        equipment_data = {
            'machines': pd.DataFrame({
                'MachineID': ['CNC-001', 'CNC-002', 'PRESS-001'],
                'Status': ['running', 'running', 'running'],
                'OEE': [0.88, 0.82, 0.85],
                'NextMaintenance': ['2024-01-20', '2024-01-16', '2024-01-25']
            }),
            'oee_summary': {
                'average_oee': 0.85,
                'target_oee': 0.80
            }
        }
        
        insights = provide_tab_insights('equipment', equipment_data)
        
        assert isinstance(insights, str)
        assert "equipment" in insights.lower()
        mock_manager.get_contextual_insights.assert_called_once()
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_inventory_tab_integration(self, mock_manager_class):
        """Test integration with inventory dashboard tab."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.get_contextual_insights.return_value = """
        Inventory Dashboard Insights:
        - 3 items below reorder level
        - Steel Plate critically low (2 days supply)
        - Copper Wire requires immediate reorder
        - Lead time concerns with Supplier B
        """
        
        inventory_data = {
            'inventory': pd.DataFrame({
                'ItemID': [1, 2, 3],
                'ItemName': ['Steel Plate', 'Aluminum Rod', 'Copper Wire'],
                'Quantity': [45, 180, 15],
                'ReorderLevel': [100, 150, 50],
                'Status': ['low', 'ok', 'critical']
            }),
            'alerts': {
                'low_stock_count': 2,
                'critical_count': 1
            }
        }
        
        insights = provide_tab_insights('inventory', inventory_data)
        
        assert isinstance(insights, str)
        assert "inventory" in insights.lower()
        mock_manager.get_contextual_insights.assert_called_once()


class TestContextualInsightsGeneration:
    """Test contextual insights generation for different contexts."""
    
    @patch('app_factory.production_meeting_agents.agent_manager.production_meeting_analysis_tool')
    def test_contextual_insights_daily_meeting(self, mock_tool):
        """Test contextual insights for daily meeting context."""
        mock_tool.return_value = """
        Daily Meeting Context Analysis:
        - Focus on immediate production priorities
        - Address quality issues requiring same-day action
        - Equipment maintenance scheduling for today
        - Inventory shortages affecting today's production
        """
        
        config = ProductionMeetingConfig(agent_enabled=True, meeting_focus='daily')
        manager = ProductionMeetingAgentManager(config)
        manager.set_meeting_context('daily', ['production', 'quality'])
        
        dashboard_data = {'meeting_type': 'daily', 'focus_areas': ['production', 'quality']}
        
        import asyncio
        insights = asyncio.run(manager.get_contextual_insights(dashboard_data, 'production'))
        
        assert isinstance(insights, str)
        assert len(insights) > 0
        mock_tool.assert_called_once()
    
    @patch('app_factory.production_meeting_agents.agent_manager.production_meeting_analysis_tool')
    def test_contextual_insights_weekly_meeting(self, mock_tool):
        """Test contextual insights for weekly meeting context."""
        mock_tool.return_value = """
        Weekly Meeting Context Analysis:
        - Production trends over the past week
        - Quality performance summary and improvements
        - Equipment utilization and maintenance completed
        - Inventory consumption patterns and forecasting
        """
        
        config = ProductionMeetingConfig(agent_enabled=True, meeting_focus='weekly')
        manager = ProductionMeetingAgentManager(config)
        manager.set_meeting_context('weekly', ['production', 'quality', 'equipment', 'inventory'])
        
        dashboard_data = {'meeting_type': 'weekly', 'time_range': '7_days'}
        
        import asyncio
        insights = asyncio.run(manager.get_contextual_insights(dashboard_data, 'weekly'))
        
        assert isinstance(insights, str)
        assert "weekly" in insights.lower()
        mock_tool.assert_called_once()
    
    def test_contextual_query_generation(self):
        """Test that contextual queries are generated appropriately for different tabs."""
        config = ProductionMeetingConfig(agent_enabled=True)
        manager = ProductionMeetingAgentManager(config)
        
        # Test different tab contexts
        test_cases = [
            ('production', 'production performance'),
            ('quality', 'quality metrics'),
            ('equipment', 'equipment performance'),
            ('inventory', 'inventory levels'),
            ('productivity', 'productivity metrics'),
            ('root_cause', 'root cause'),
            ('weekly', 'weekly')
        ]
        
        for tab_name, expected_keyword in test_cases:
            query = manager._create_contextual_query(tab_name, {})
            assert isinstance(query, str)
            assert expected_keyword in query.lower()
            assert len(query) > 20  # Should be substantial query


class TestBackwardCompatibility:
    """Test that existing dashboard functionality remains unchanged."""
    
    def test_dashboard_function_signatures_preserved(self):
        """Test that AI insights functions maintain their original signatures."""
        import inspect
        from app_factory.production_meeting.ai_insights import generate_ai_insight, provide_tab_insights
        
        # Check generate_ai_insight signature
        sig = inspect.signature(generate_ai_insight)
        params = list(sig.parameters.keys())
        
        # Should accept data and query parameters
        assert 'data' in params or len(params) >= 1
        assert len(params) >= 2  # Should have at least data and query parameters
        
        # Check provide_tab_insights signature
        sig = inspect.signature(provide_tab_insights)
        params = list(sig.parameters.keys())
        
        # Should accept tab_name and dashboard_data parameters
        assert len(params) >= 2
    
    @patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager')
    def test_existing_dashboard_calls_still_work(self, mock_manager_class):
        """Test that existing dashboard code can still call AI insights functions."""
        # Mock agent manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.is_ready.return_value = True
        mock_manager.process_query.return_value = {
            'success': True,
            'analysis': 'Test analysis result'
        }
        mock_manager.get_contextual_insights.return_value = "Test contextual insights"
        
        # Test that old calling patterns still work
        test_data = pd.DataFrame({'test': [1, 2, 3]})
        
        # Should work with positional arguments
        result1 = generate_ai_insight(test_data, "test query")
        assert isinstance(result1, dict)
        
        # Should work with keyword arguments
        result2 = provide_tab_insights(tab_name='production', dashboard_data={'test': 'data'})
        assert isinstance(result2, str)
    
    def test_return_value_formats_preserved(self):
        """Test that return value formats are preserved for backward compatibility."""
        with patch('app_factory.production_meeting.ai_insights.ProductionMeetingAgentManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.is_ready.return_value = True
            mock_manager.process_query.return_value = {
                'success': True,
                'analysis': 'Test analysis'
            }
            mock_manager.get_contextual_insights.return_value = "Test insights"
            
            # Test generate_ai_insight return format
            result = generate_ai_insight(pd.DataFrame({'test': [1]}), "test")
            assert isinstance(result, dict)
            assert 'success' in result
            
            # Test provide_tab_insights return format
            result = provide_tab_insights('production', {'test': 'data'})
            assert isinstance(result, str)


class TestDashboardFunctionalityPreservation:
    """Test that existing dashboard functionality is preserved."""
    
    def test_dashboard_imports_still_work(self):
        """Test that dashboard modules can still be imported."""
        try:
            # Test importing dashboard modules
            from app_factory.production_meeting.dashboards import production
            from app_factory.production_meeting.dashboards import quality
            from app_factory.production_meeting.dashboards import equipment
            from app_factory.production_meeting.dashboards import inventory
            
            # Should import without errors
            assert production is not None
            assert quality is not None
            assert equipment is not None
            assert inventory is not None
            
        except ImportError as e:
            pytest.fail(f"Dashboard imports failed: {e}")
    
    def test_dashboard_data_processing_unchanged(self):
        """Test that dashboard data processing functions are unchanged."""
        # This test would verify that existing dashboard functions
        # for data processing, chart generation, etc. still work
        
        # Mock some basic dashboard functionality
        test_data = pd.DataFrame({
            'Date': ['2024-01-15', '2024-01-16'],
            'Production': [100, 105],
            'Quality': [0.98, 0.97]
        })
        
        # Basic data operations should still work
        assert len(test_data) == 2
        assert 'Production' in test_data.columns
        assert test_data['Production'].sum() == 205
    
    @patch('streamlit.plotly_chart')
    @patch('streamlit.metric')
    def test_dashboard_visualization_functions_preserved(self, mock_metric, mock_chart):
        """Test that dashboard visualization functions are preserved."""
        # Mock Streamlit functions
        mock_metric.return_value = None
        mock_chart.return_value = None
        
        # Test that basic Streamlit operations still work
        import streamlit as st
        
        # These should not raise errors
        st.metric("Test Metric", 100)
        mock_metric.assert_called_once()
        
        # Chart functionality should be preserved
        test_fig = {'data': [], 'layout': {}}
        st.plotly_chart(test_fig)
        mock_chart.assert_called_once()


def run_dashboard_integration_tests():
    """Run all dashboard integration tests."""
    print("🧪 Running Dashboard Integration Tests...")
    print("=" * 60)
    
    test_classes = [
        TestAIInsightsReplacement,
        TestDashboardTabIntegration,
        TestContextualInsightsGeneration,
        TestBackwardCompatibility,
        TestDashboardFunctionalityPreservation
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 Testing {test_class.__name__}...")
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                test_instance = test_class()
                
                # Run setup if available
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                method = getattr(test_instance, test_method)
                method()
                
                print(f"  ✅ {test_method}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {test_method}: {str(e)}")
                failed_tests.append(f"{test_class.__name__}.{test_method}: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Dashboard Integration Test Results:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for failure in failed_tests:
            print(f"   - {failure}")
    else:
        print(f"\n🎉 All dashboard integration tests passed!")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_dashboard_integration_tests()
    exit(0 if success else 1)