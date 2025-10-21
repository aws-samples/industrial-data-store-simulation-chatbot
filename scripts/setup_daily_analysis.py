#!/usr/bin/env python3
"""
Setup script for daily analysis automation

This script helps set up automated daily analysis generation using cron or system scheduler.
"""

import os
import sys
import subprocess
from pathlib import Path

def get_project_root():
    """Get the project root directory"""
    current_dir = Path(__file__).parent.parent
    return current_dir.absolute()



def create_systemd_service():
    """Create systemd service and timer for daily analysis"""
    
    project_root = get_project_root()
    script_path = project_root / "scripts" / "run_daily_analysis.py"
    
    service_content = f"""[Unit]
Description=Daily MES Production Analysis with Data Generation
After=network.target
Documentation=file://{project_root}/docs/DAILY_ANALYSIS_SETUP.md

[Service]
Type=oneshot
User={os.getenv('USER', 'root')}
WorkingDirectory={project_root}
ExecStart=/usr/bin/env uv run python {script_path}
StandardOutput=journal
StandardError=journal

# Resource limits
TimeoutStartSec=600
MemoryMax=2G

# Environment
Environment=PYTHONPATH={project_root}
Environment=UV_CACHE_DIR={project_root}/.uv-cache

[Install]
WantedBy=multi-user.target
"""

    timer_content = """[Unit]
Description=Run Daily MES Production Analysis
Requires=daily-mes-analysis.service
Documentation=https://www.freedesktop.org/software/systemd/man/systemd.timer.html

[Timer]
# Run daily at 6:00 AM
OnCalendar=*-*-* 06:00:00
# Run immediately if the system was powered off during the scheduled time
Persistent=true
# Add some randomization to avoid system load spikes
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
"""

    print("Systemd Service Setup")
    print("=" * 25)
    print("✅ Benefits of systemd:")
    print("  • Better logging with journalctl")
    print("  • Automatic restart on failure")
    print("  • Resource management and limits")
    print("  • Dependency management")
    print("  • Status monitoring")
    print()
    print("Service file content:")
    print(service_content)
    print("\nTimer file content:")
    print(timer_content)
    print()
    
    response = input("Would you like to create systemd service files? (y/n): ").lower().strip()
    
    if response == 'y':
        try:
            # Write service file
            service_path = Path("/tmp/daily-mes-analysis.service")
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            # Write timer file
            timer_path = Path("/tmp/daily-mes-analysis.timer")
            with open(timer_path, 'w') as f:
                f.write(timer_content)
            
            print(f"✅ Service files created in /tmp/")
            print("\n📋 Installation commands:")
            print(f"sudo cp {service_path} /etc/systemd/system/")
            print(f"sudo cp {timer_path} /etc/systemd/system/")
            print("sudo systemctl daemon-reload")
            print("sudo systemctl enable daily-mes-analysis.timer")
            print("sudo systemctl start daily-mes-analysis.timer")
            print()
            print("📊 Management commands:")
            print("# Check status:")
            print("sudo systemctl status daily-mes-analysis.timer")
            print("sudo systemctl status daily-mes-analysis.service")
            print()
            print("# View logs:")
            print("sudo journalctl -u daily-mes-analysis.service -f")
            print()
            print("# Manual run:")
            print("sudo systemctl start daily-mes-analysis.service")
            
        except Exception as e:
            print(f"❌ Error creating service files: {e}")

def test_daily_analysis():
    """Test the daily analysis script"""
    project_root = get_project_root()
    script_path = project_root / "scripts" / "run_daily_analysis.py"
    
    print("Testing Daily Analysis Script")
    print("=" * 35)
    print(f"Running: {script_path}")
    print()
    
    try:
        result = subprocess.run(['uv', 'run', 'python', str(script_path)], 
                              capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print("✅ Daily analysis completed successfully!")
            print("\nOutput:")
            print(result.stdout)
        else:
            print("❌ Daily analysis failed!")
            print("\nError:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error running daily analysis: {e}")

def check_systemd():
    """Check if systemd is available"""
    try:
        result = subprocess.run(['systemctl', '--version'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def main():
    """Main setup function"""
    print("MES Daily Analysis Setup")
    print("=" * 30)
    print("This script sets up automated daily analysis generation using systemd.")
    print("The analysis includes fresh data generation + comprehensive AI insights.")
    print()
    
    # Check if systemd is available
    if not check_systemd():
        print("❌ Error: systemd is not available on this system.")
        print("This setup script requires systemd (available on modern Linux distributions).")
        print("Please ensure you're running on a systemd-based Linux system.")
        return
    
    print("✅ Systemd detected - proceeding with setup")
    print()
    print("🎯 Benefits of systemd automation:")
    print("  • Reliable scheduling with automatic restart on failure")
    print("  • Comprehensive logging with journalctl")
    print("  • Resource management and limits")
    print("  • Easy status monitoring and management")
    print()
    
    while True:
        print("Options:")
        print("1. Test daily analysis script")
        print("2. Setup systemd service and timer")
        print("3. Exit")
        print()
        
        choice = input("Select an option (1-3): ").strip()
        
        if choice == '1':
            test_daily_analysis()
        elif choice == '2':
            create_systemd_service()
        elif choice == '3':
            print("Setup complete!")
            break
        else:
            print("Invalid choice. Please select 1-3.")
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()