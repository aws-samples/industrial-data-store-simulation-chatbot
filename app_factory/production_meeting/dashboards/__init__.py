from .production import production_summary_dashboard
from .equipment import equipment_status_dashboard
from .quality import quality_dashboard
from .inventory import inventory_dashboard
from .root_cause import add_root_cause_analysis

__all__ = [
    'production_summary_dashboard',
    'equipment_status_dashboard',
    'quality_dashboard',
    'inventory_dashboard',
    'add_root_cause_analysis',
]