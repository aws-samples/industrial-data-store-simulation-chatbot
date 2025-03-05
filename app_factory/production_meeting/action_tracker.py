"""
Action Item Tracker for Production Meetings
Handles creating, updating, and managing action items from meetings
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import os
from pathlib import Path

class ActionTracker:
    """Manager for tracking action items from production meetings"""
    
    def __init__(self):
        """Initialize the action tracker"""
        # Create the data directory if it doesn't exist
        self.data_dir = Path("data/action_items")
        self.data_dir.mkdir(exist_ok=True, parents=True)
    
    def add_action_item(self, description, owner, priority, due_date, meeting_date, notes=""):
        """
        Add a new action item
        
        Args:
            description (str): Description of the action item
            owner (str): Person responsible for the action
            priority (str): Priority level (High, Medium, Low)
            due_date (str): Due date in YYYY-MM-DD format
            meeting_date (str): Meeting date in YYYY-MM-DD format
            notes (str, optional): Additional notes
            
        Returns:
            dict: The created action item
        """
        # Generate a unique ID
        action_id = f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create the action item
        action_item = {
            "id": action_id,
            "description": description,
            "owner": owner,
            "priority": priority,
            "due_date": due_date,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_date": meeting_date,
            "status": "Open",
            "notes": notes,
            "updates": []
        }
        
        # Save to file
        self._save_action_item(action_item)
        
        return action_item
    
    def update_action_status(self, action_id, new_status, update_note=""):
        """
        Update an action item's status
        
        Args:
            action_id (str): The ID of the action item
            new_status (str): New status (Open, In Progress, Completed, Closed)
            update_note (str, optional): Note about the update
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        action_item = self.get_action_item(action_id)
        
        if not action_item:
            return False
        
        # Update the status
        action_item["status"] = new_status
        
        # Add update record
        update = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": new_status,
            "note": update_note
        }
        
        action_item["updates"].append(update)
        
        # Save changes
        self._save_action_item(action_item)
        
        return True
    
    def get_action_item(self, action_id):
        """
        Get a specific action item by ID
        
        Args:
            action_id (str): The ID of the action item
            
        Returns:
            dict: The action item or None if not found
        """
        filepath = self.data_dir / f"{action_id}.json"
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading action item {action_id}: {e}")
            return None
    
    def get_all_action_items(self, filter_status=None):
        """
        Get all action items, optionally filtered by status
        
        Args:
            filter_status (str or list, optional): Status(es) to filter by
            
        Returns:
            list: List of action items
        """
        actions = []
        
        # Load all action item files
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    action = json.load(f)
                    
                    # Apply status filter if specified
                    if filter_status:
                        if isinstance(filter_status, list):
                            if action["status"] in filter_status:
                                actions.append(action)
                        else:
                            if action["status"] == filter_status:
                                actions.append(action)
                    else:
                        actions.append(action)
            except Exception as e:
                print(f"Error loading action item from {file}: {e}")
        
        # Sort by due date
        actions.sort(key=lambda x: x.get("due_date", "9999-99-99"))
        
        return actions
    
    def get_open_actions_by_owner(self):
        """
        Get open actions grouped by owner
        
        Returns:
            dict: Dictionary of owners with their open actions
        """
        open_actions = self.get_all_action_items(filter_status=["Open", "In Progress"])
        
        # Group by owner
        owners = {}
        for action in open_actions:
            owner = action["owner"]
            if owner not in owners:
                owners[owner] = []
            owners[owner].append(action)
        
        return owners
    
    def get_overdue_actions(self):
        """
        Get all overdue actions (due date in the past and not completed)
        
        Returns:
            list: List of overdue action items
        """
        open_actions = self.get_all_action_items(filter_status=["Open", "In Progress"])
        today = datetime.now().strftime("%Y-%m-%d")
        
        overdue = [
            action for action in open_actions
            if action["due_date"] < today
        ]
        
        # Sort by due date (oldest first)
        overdue.sort(key=lambda x: x["due_date"])
        
        return overdue
    
    def delete_action_item(self, action_id):
        """
        Delete an action item
        
        Args:
            action_id (str): The ID of the action item
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        filepath = self.data_dir / f"{action_id}.json"
        
        if not filepath.exists():
            return False
        
        try:
            filepath.unlink()
            return True
        except Exception as e:
            print(f"Error deleting action item {action_id}: {e}")
            return False
    
    def _save_action_item(self, action_item):
        """
        Save an action item to file
        
        Args:
            action_item (dict): The action item to save
        """
        action_id = action_item["id"]
        filepath = self.data_dir / f"{action_id}.json"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(action_item, f, indent=2)
        except Exception as e:
            print(f"Error saving action item {action_id}: {e}")
    
    def get_action_items_for_meeting(self, meeting_date):
        """
        Get action items created in a specific meeting
        
        Args:
            meeting_date (str): Meeting date in YYYY-MM-DD format
            
        Returns:
            list: List of action items from the meeting
        """
        all_actions = self.get_all_action_items()
        
        meeting_actions = [
            action for action in all_actions
            if action.get("meeting_date") == meeting_date
        ]
        
        return meeting_actions
    
    def export_actions_to_csv(self, filename=None):
        """
        Export all action items to CSV
        
        Args:
            filename (str, optional): Output filename
            
        Returns:
            str: Path to the exported CSV file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"action_items_export_{timestamp}.csv"
        
        # Get all action items
        actions = self.get_all_action_items()
        
        # Convert to DataFrame for export
        df = pd.DataFrame(actions)
        
        # Create exports directory if it doesn't exist
        exports_dir = Path("exports")
        exports_dir.mkdir(exist_ok=True)
        
        # Export to CSV
        export_path = exports_dir / filename
        df.to_csv(export_path, index=False)
        
        return str(export_path)

# Create a Streamlit component for displaying and managing action items
def display_action_tracker(meeting_date=None):
    """
    Streamlit component for displaying and managing action items
    
    Args:
        meeting_date (str, optional): Current meeting date (for filtering)
    """
    # Initialize tracker
    tracker = ActionTracker()
    
    # Layout
    st.subheader("📋 Action Item Tracker")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Current Actions", "Add New Action", "Action History"])
    
    # Tab 1: Current Actions
    with tab1:
        # Filter controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                options=["Open", "In Progress", "Completed", "Closed"],
                default=["Open", "In Progress"]
            )
        
        with col2:
            priority_filter = st.multiselect(
                "Priority",
                options=["High", "Medium", "Low"],
                default=["High", "Medium", "Low"]
            )
        
        with col3:
            owner_filter = st.text_input("Owner Filter", "")
        
        # Get action items
        actions = tracker.get_all_action_items()
        
        # Apply filters
        filtered_actions = []
        for action in actions:
            if status_filter and action["status"] not in status_filter:
                continue
            
            if priority_filter and action["priority"] not in priority_filter:
                continue
            
            if owner_filter and owner_filter.lower() not in action["owner"].lower():
                continue
            
            filtered_actions.append(action)
        
        # Show results
        if filtered_actions:
            st.write(f"Showing {len(filtered_actions)} action items")
            
            for action in filtered_actions:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    # Set priority color
                    priority_color = "🟢"  # Default green
                    if action["priority"] == "High":
                        priority_color = "🔴"
                    elif action["priority"] == "Medium":
                        priority_color = "🟠"
                    
                    col1.markdown(f"**{action['id']}: {action['description']}**")
                    col2.markdown(f"**Owner:** {action['owner']}")
                    col3.markdown(f"**Priority:** {priority_color} {action['priority']}")
                    
                    col4, col5, col6 = st.columns([1, 1, 3])
                    col4.markdown(f"**Due:** {action['due_date']}")
                    col5.markdown(f"**Status:** {action['status']}")
                    
                    if action.get("notes"):
                        col6.markdown(f"**Notes:** {action['notes']}")
                    
                    # Action management
                    action_col1, action_col2 = st.columns([3, 1])
                    
                    with action_col1:
                        new_status = st.selectbox(
                            "Update Status",
                            options=["Open", "In Progress", "Completed", "Closed"],
                            index=["Open", "In Progress", "Completed", "Closed"].index(action["status"]),
                            key=f"status_{action['id']}"
                        )
                        
                        status_note = st.text_input(
                            "Update Note",
                            key=f"note_{action['id']}",
                            placeholder="Add optional note about the update"
                        )
                    
                    with action_col2:
                        if st.button("Update", key=f"update_{action['id']}"):
                            if new_status != action["status"]:
                                tracker.update_action_status(action["id"], new_status, status_note)
                                st.success(f"Updated status to {new_status}")
                                st.rerun()
                        
                        if st.button("Delete", key=f"delete_{action['id']}"):
                            tracker.delete_action_item(action["id"])
                            st.success("Action item deleted")
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No action items match your filters")
    
    # Tab 2: Add New Action
    with tab2:
        with st.form("new_action_form"):
            st.write("Create New Action Item")
            
            description = st.text_input("Description", placeholder="What needs to be done?")
            
            col1, col2 = st.columns(2)
            with col1:
                owner = st.text_input("Owner", placeholder="Who is responsible?")
            with col2:
                priority = st.selectbox("Priority", options=["High", "Medium", "Low"])
            
            col3, col4 = st.columns(2)
            with col3:
                due_date = st.date_input("Due Date", datetime.now() + timedelta(days=1))
            with col4:
                if meeting_date:
                    meeting_date_val = datetime.strptime(meeting_date, "%Y-%m-%d").date()
                else:
                    meeting_date_val = datetime.now().date()
                
                meeting_date_input = st.date_input("Meeting Date", meeting_date_val)
            
            notes = st.text_area("Notes", placeholder="Additional details or context")
            
            submitted = st.form_submit_button("Create Action Item")
            
            if submitted:
                if description and owner:
                    # Create new action
                    tracker.add_action_item(
                        description=description,
                        owner=owner,
                        priority=priority,
                        due_date=due_date.strftime("%Y-%m-%d"),
                        meeting_date=meeting_date_input.strftime("%Y-%m-%d"),
                        notes=notes
                    )
                    
                    st.success("Action item created!")
                    st.rerun()
                else:
                    st.error("Description and Owner are required")
    
    # Tab 3: Action History
    with tab3:
        st.write("Action Item History")
        
        # Get completed/closed actions
        closed_actions = tracker.get_all_action_items(filter_status=["Completed", "Closed"])
        
        if closed_actions:
            st.write(f"{len(closed_actions)} completed or closed actions")
            
            # Group by month
            months = {}
            for action in closed_actions:
                update_dates = [u["timestamp"][:7] for u in action.get("updates", [])]
                if update_dates:
                    # Use the date of the status change to Completed/Closed
                    month = max(update_dates)
                else:
                    # Fallback to creation date
                    month = action["created_date"][:7]
                
                if month not in months:
                    months[month] = []
                
                months[month].append(action)
            
            # Display by month
            for month in sorted(months.keys(), reverse=True):
                with st.expander(f"{month} ({len(months[month])} actions)"):
                    for action in months[month]:
                        st.markdown(f"""
                        **{action['id']}:** {action['description']}  
                        **Owner:** {action['owner']} | **Status:** {action['status']} | **Priority:** {action['priority']}  
                        **Due:** {action['due_date']} | **Created:** {action['created_date']}
                        """)
                        
                        if action.get("updates"):
                            st.markdown("**Updates:**")
                            for update in action["updates"]:
                                st.markdown(f"- {update['timestamp']}: Changed to **{update['status']}**" + 
                                          (f" - *{update['note']}*" if update['note'] else ""))
                        
                        st.markdown("---")
            
            # Export option
            if st.button("Export All Actions to CSV"):
                csv_path = tracker.export_actions_to_csv()
                st.success(f"Exported to {csv_path}")
        else:
            st.info("No completed or closed action items found")

# For testing the module directly
if __name__ == "__main__":
    st.set_page_config(page_title="Action Tracker", layout="wide")
    st.title("Action Item Tracker Test")
    display_action_tracker()