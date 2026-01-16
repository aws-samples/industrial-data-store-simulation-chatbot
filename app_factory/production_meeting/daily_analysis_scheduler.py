"""
Daily Analysis Scheduler for Production Meeting Insights

This module runs comprehensive AI analysis daily and caches results for fast retrieval.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app_factory.shared.database import DatabaseManager
from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
from app_factory.production_meeting_agents.config import default_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyAnalysisScheduler:
    """Handles daily analysis generation and caching"""
    
    def __init__(self, cache_dir: str = "reports/daily_analysis", generate_data: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.generate_data = generate_data
        
        self.db_manager = DatabaseManager()
        self.agent_manager = ProductionMeetingAgentManager(default_config)
        
        # Get project root for data generation
        self.project_root = Path(__file__).parent.parent.parent
        
    async def initialize(self):
        """Initialize the agent manager"""
        try:
            await self.agent_manager.initialize()
            logger.info("Agent manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {e}")
            raise
    
    def generate_fresh_data(self) -> bool:
        """Generate fresh synthetic MES data before analysis"""
        if not self.generate_data:
            logger.info("Data generation disabled, skipping")
            return True
            
        logger.info("Generating fresh synthetic MES data...")
        
        try:
            # Path to data generator script
            data_generator_script = self.project_root / "app_factory" / "data_generator" / "sqlite-synthetic-mes-data.py"
            config_file = self.project_root / "app_factory" / "data_generator" / "data_pools.json"
            
            # Command to generate data with 90 days lookback and 14 days lookahead
            cmd = [
                "uv", "run", "python", str(data_generator_script),
                "--config", str(config_file),
                "--lookback", "90",
                "--lookahead", "14"
            ]
            
            logger.info(f"Running data generation: {' '.join(cmd)}")
            
            # Run the data generation
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Data generation completed successfully")
                if result.stdout:
                    logger.debug(f"Data generation output: {result.stdout}")
                return True
            else:
                logger.error(f"Data generation failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"Data generation error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Data generation timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Error during data generation: {e}")
            return False
    
    def get_cache_filename(self, date: datetime = None) -> Path:
        """Get cache filename for a specific date"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        return self.cache_dir / f"daily_analysis_{date_str}.json"
    
    async def generate_daily_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive daily analysis using parallel execution"""
        logger.info("Starting daily analysis generation (parallel mode)")
        start_time = datetime.now()

        analysis_results = {
            "generated_at": start_time.isoformat(),
            "analysis_date": start_time.strftime("%Y-%m-%d"),
            "analyses": {}
        }

        # Define analysis types - simplified queries for faster processing
        analysis_types = [
            {
                "name": "executive_summary",
                "context": "production",
                "query": """Executive summary for daily meeting. Format as 3-5 bullet points with emoji indicators (🔴 critical, 🟠 warning, 🟢 good). Include only the most critical issues across production, quality, equipment, and inventory. Under 200 words."""
            },
            {
                "name": "production_summary",
                "context": "production",
                "query": """Daily production status: completion rates, bottlenecks, and critical work orders. Be concise - key metrics and top 3 issues only."""
            },
            {
                "name": "quality_insights",
                "context": "quality",
                "query": """Today's quality metrics: defect rates, yield, and quality issues requiring attention. Focus on actionable items only."""
            },
            {
                "name": "equipment_status",
                "context": "equipment",
                "query": """Equipment status: OEE metrics, machines down or at risk, maintenance priorities. Key numbers and actions only."""
            },
            {
                "name": "inventory_analysis",
                "context": "inventory",
                "query": """Inventory status: items below reorder level, stock-outs, and materials at risk. Critical shortages only."""
            }
        ]

        # Run all analyses in PARALLEL for speed
        async def run_single_analysis(analysis_config):
            """Run a single analysis and return result"""
            try:
                logger.info(f"Starting {analysis_config['name']} analysis")
                analysis_start = datetime.now()

                agent_context = {
                    'context_type': analysis_config['context'],
                    'include_historical': False,  # Faster without historical
                    'dashboard_data': {},
                    'query_type': 'quick_daily'
                }

                response = await self.agent_manager.process_query(
                    analysis_config['query'],
                    agent_context
                )

                execution_time = (datetime.now() - analysis_start).total_seconds()

                if response.get('success', False):
                    logger.info(f"Completed {analysis_config['name']} in {execution_time:.1f}s")
                    return analysis_config['name'], {
                        "analysis": response.get('analysis', ''),
                        "execution_time": execution_time,
                        "capabilities_used": response.get('capabilities_used', []),
                        "follow_up_suggestions": response.get('follow_up_suggestions', []),
                        "generated_at": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"Failed {analysis_config['name']}: {response.get('error', 'Unknown')}")
                    return analysis_config['name'], {
                        "error": response.get('error', 'Analysis failed'),
                        "generated_at": datetime.now().isoformat()
                    }

            except Exception as e:
                logger.error(f"Error in {analysis_config['name']}: {e}")
                return analysis_config['name'], {
                    "error": str(e),
                    "generated_at": datetime.now().isoformat()
                }

        # Execute all analyses in parallel using asyncio.gather
        tasks = [run_single_analysis(config) for config in analysis_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel task failed: {result}")
            else:
                name, data = result
                analysis_results["analyses"][name] = data

        # Add execution summary
        total_time = (datetime.now() - start_time).total_seconds()
        analysis_results["total_execution_time"] = total_time
        analysis_results["completed_at"] = datetime.now().isoformat()

        logger.info(f"Daily analysis completed in {total_time:.2f} seconds (parallel)")
        return analysis_results
    
    def save_analysis_cache(self, analysis_results: Dict[str, Any], date: datetime = None):
        """Save analysis results to cache file"""
        cache_file = self.get_cache_filename(date)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Analysis results cached to {cache_file}")
            
            # Clean up old cache files (keep last 30 days)
            self.cleanup_old_cache_files()
            
        except Exception as e:
            logger.error(f"Failed to save analysis cache: {e}")
            raise
    
    def cleanup_old_cache_files(self, days_to_keep: int = 30):
        """Remove cache files older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for cache_file in self.cache_dir.glob("daily_analysis_*.json"):
            try:
                # Extract date from filename
                date_str = cache_file.stem.replace("daily_analysis_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    cache_file.unlink()
                    logger.info(f"Removed old cache file: {cache_file}")
                    
            except Exception as e:
                logger.warning(f"Error processing cache file {cache_file}: {e}")
    
    async def run_daily_analysis(self):
        """Main method to run daily analysis"""
        try:
            # Step 1: Generate fresh data (if enabled)
            if self.generate_data:
                logger.info("Step 1: Generating fresh synthetic data...")
                data_success = self.generate_fresh_data()
                if not data_success:
                    logger.warning("Data generation failed, proceeding with existing data")
                else:
                    logger.info("Fresh data generated successfully")
            
            # Step 2: Initialize agent manager
            logger.info("Step 2: Initializing agent manager...")
            await self.initialize()
            
            # Step 3: Check if analysis already exists for today
            today_cache = self.get_cache_filename()
            if today_cache.exists():
                logger.info(f"Daily analysis already exists for today: {today_cache}")
                
                # Check if it's recent (within last 6 hours)
                file_time = datetime.fromtimestamp(today_cache.stat().st_mtime)
                if datetime.now() - file_time < timedelta(hours=6):
                    logger.info("Recent analysis found, skipping generation")
                    return
                else:
                    logger.info("Analysis is older than 6 hours, regenerating")
            
            # Step 4: Generate new analysis
            logger.info("Step 3: Generating comprehensive analysis...")
            analysis_results = await self.generate_daily_analysis()
            
            # Step 5: Save to cache
            logger.info("Step 4: Saving analysis to cache...")
            self.save_analysis_cache(analysis_results)
            
            logger.info("Daily analysis workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Daily analysis workflow failed: {e}")
            raise


async def main():
    """Main entry point for daily analysis"""
    scheduler = DailyAnalysisScheduler()
    await scheduler.run_daily_analysis()


if __name__ == "__main__":
    asyncio.run(main())