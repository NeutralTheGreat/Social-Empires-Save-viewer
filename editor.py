import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QFileDialog,
    QMessageBox, QLineEdit, QComboBox, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class FileLoaderThread(QThread):
    file_loaded = pyqtSignal(dict)  # Signal to emit loaded data

    def __init__(self, config_path, assets_path):
        super().__init__()
        self.config_path = config_path
        self.assets_path = assets_path
        self.config_items = []
        self.save_items = []
        self.current_file = None
        self.mode = "config"
        self.init_ui()
        self.apply_dark_mode()  # Apply dark mode theme

    def run(self):
        """Load the file in a separate thread."""
        try:
            with open(self.file_path, "r") as file:
                data = json.load(file)
                # Emit the data once loaded
                self.file_loaded.emit(data)
        except Exception as e:
            print(f"Error loading file: {e}")


class ConfigEditor(QMainWindow):
    def __init__(self, config_path, assets_path):
        super().__init__()
        self.config_path = config_path
        self.assets_path = assets_path
        self.config_items = []
        self.save_items = []
        self.current_file = None
        self.mode = "config"
        self.init_ui()
        self.apply_dark_mode()  # Ensure this is here

    def init_ui(self):
        """Initialize the UI layout."""
        self.setWindowTitle("Social Empires Save File Debugger")

        # Set minimum size and optionally a default starting size
        self.setMinimumSize(800, 600)  # Minimum size for the window
        self.resize(1200, 600)  # Optional: Set a default size without forcing it

        # Set the window icon
        self.setWindowIcon(QIcon('templates/img/icon.gif'))

        # Main Layout
        main_layout = QVBoxLayout()  # Main vertical layout

        # Top Section: Buttons and Tools
        top_layout = QHBoxLayout()

        # Buttons in the Top Section
        self.toggle_button = QPushButton("Switch to Save File View")
        self.toggle_button.clicked.connect(self.toggle_mode)
        top_layout.addWidget(self.toggle_button)

        open_button = QPushButton("Open File")
        open_button.clicked.connect(self.load_file)
        top_layout.addWidget(open_button)

        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_file)
        top_layout.addWidget(save_button)

        debug_button = QPushButton("Find Missing IDs")
        debug_button.clicked.connect(self.find_missing_ids)
        top_layout.addWidget(debug_button)

        delete_button = QPushButton("Delete Selected Items")
        delete_button.clicked.connect(self.delete_selected_items)
        top_layout.addWidget(delete_button)

        # Search bar and button
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Enter ID to find...")
        self.search_bar.setFixedWidth(150)  # Set a fixed width (adjust as needed)
        top_layout.addWidget(self.search_bar)

        search_button = QPushButton("Find")
        search_button.clicked.connect(self.find_items_by_id)
        top_layout.addWidget(search_button)

        # Town Selector Dropdown
        self.town_selector = QComboBox()
        self.town_selector.currentIndexChanged.connect(self.switch_town)
        top_layout.addWidget(QLabel("Select Town:"))
        self.search_bar.setFixedWidth(150)  # Set a fixed width (adjust as needed)
        top_layout.addWidget(self.town_selector)

        # Add Player Info Label
        self.player_info_label = QLabel("No Save File Loaded")  # Default text
        self.player_info_label.setAlignment(Qt.AlignCenter)
        self.player_info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        top_layout.addWidget(self.player_info_label)

        # Add Top Layout to Main Layout
        main_layout.addLayout(top_layout)

        # Middle Section: Table and Stats Panel
        middle_layout = QHBoxLayout()

        # Left Section: Table
        left_layout = QVBoxLayout()

        # Table for Data Display
        self.table = QTableWidget()  # Initialize the table
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name/Details", "Position/Stats", "Image"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.set_table_selection_mode()  # Dynamically set the selection mode
        self.table.itemSelectionChanged.connect(self.update_stats_panel)
        left_layout.addWidget(self.table)  # Add the table to the layout

        # Add Left Layout to Middle Layout
        middle_layout.addLayout(left_layout, 2)

        # Right Section: Stats Panel
        right_layout = QVBoxLayout()

        self.add_button = QPushButton("Add Selected Unit/Building")
        self.add_button.clicked.connect(self.add_item_to_save)
        right_layout.addWidget(self.add_button)

        # List of Units/Buildings (from Config)
        self.add_items_list = QTableWidget()
        self.add_items_list.setColumnCount(2)
        self.add_items_list.setHorizontalHeaderLabels(["ID", "Name"])
        self.add_items_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.add_items_list.setSelectionMode(QTableWidget.SingleSelection)

        right_layout.addWidget(self.add_items_list)

        # Stats Display Area
        self.stats_widget = QWidget()  # Main widget for stats
        self.stats_layout = QVBoxLayout(self.stats_widget)  # Layout for stats
        self.stats_widget.setLayout(self.stats_layout)

        right_layout.addWidget(self.stats_widget)  # Add to the right layout

        # Add Right Layout to Middle Layout
        middle_layout.addLayout(right_layout, 1)

        # Add Middle Layout to Main Layout
        main_layout.addLayout(middle_layout)

        # Finalize Layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def set_table_selection_mode(self):
        """Set the table's selection mode based on the current mode."""
        if self.mode == "config":
            self.table.setSelectionMode(QTableWidget.SingleSelection)  # Single select for stats
        elif self.mode == "save":
            self.table.setSelectionMode(QTableWidget.MultiSelection)  # Multi-select for save mode

    def populate_add_items_list(self):
        """Populate the right panel with units/buildings from the config, including 90x90 images."""
        if not self.config_items:
            QMessageBox.warning(self, "No Config Data", "No config file loaded. Please load a config file first.")
            return

        self.add_items_list.setRowCount(0)  # Clear the table
        self.add_items_list.setColumnCount(3)  # Update column count to include images
        self.add_items_list.setHorizontalHeaderLabels(["ID", "Name", "Image"])
        self.add_items_list.setColumnWidth(0, 50)  # ID
        self.add_items_list.setColumnWidth(1, 150)  # Name
        self.add_items_list.setColumnWidth(2, 90)  # Image

        for item in self.config_items:
            row = self.add_items_list.rowCount()
            self.add_items_list.insertRow(row)
            self.add_items_list.setRowHeight(row, 90)  # Set row height for 90x90 images

            # Add ID
            self.add_items_list.setItem(row, 0, QTableWidgetItem(str(item.get("id", "N/A"))))

            # Add Name
            self.add_items_list.setItem(row, 1, QTableWidgetItem(item.get("name", "Unnamed")))

            # Add Image
            img_name = item.get("img_name", "placeholder")
            img_path = os.path.join(self.assets_path, f"{img_name}.jpg")
            image_label = QLabel()
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(90, 90, Qt.KeepAspectRatio)  # Scale to 90x90
                image_label.setPixmap(pixmap)
            else:
                pixmap = QPixmap(90, 90)  # Create a blank pixmap
                pixmap.fill(Qt.gray)  # Fill with gray as a placeholder
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignCenter)

            self.add_items_list.setCellWidget(row, 2, image_label)

    def toggle_mode(self):
        """Switch between config and save file views."""
        self.mode = "save" if self.mode == "config" else "config"
        self.set_table_selection_mode()
        self.populate_table()

        if self.mode == "save":
            self.populate_add_items_list()  # Populate the right panel

    def add_item_to_save(self):
        """Add the selected unit/building to the save file."""
        if not self.mode == "save":
            QMessageBox.warning(self, "Error", "This feature is only available in Save File mode.")
            return

        selected_row = self.add_items_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a unit or building to add.")
            return

        # Get the selected item's data
        item_id = int(self.add_items_list.item(selected_row, 0).text())
        item_name = self.add_items_list.item(selected_row, 1).text()

        # Example: Add the item with default attributes to the save file
        new_item = [item_id, 54, 54, 0, 0, 0, [], {}]
        self.save_items.append(new_item)

        # Refresh the table
        self.populate_table()
        QMessageBox.information(self, "Success", f"Added {item_name} (ID: {item_id}) to the save file.")

    def update_stats_panel(self):
        """Update the right panel with stats of the most recently selected item."""
        if self.mode == "save":
            self.clear_stats_panel()  # Clear the panel if in save file view
            return

        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            self.clear_stats_panel()  # Clear the panel if no row is selected
            return

        # Process the last selected row
        row = selected_indexes[-1].row()
        item_data = self.config_items[row]

        # Populate stats editor
        self.clear_stats_panel()  # Clear before populating
        self.populate_stats_form(item_data)

    def update_stats_panel(self):
        """Update the right panel with stats of the most recently selected item."""
        if self.mode == "save":
            self.clear_stats_panel()  # Clear the panel if in save file view
            return

        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            self.clear_stats_panel()  # Clear the panel if no row is selected
            return

        # Process the last selected row
        row = selected_indexes[-1].row()
        item_data = self.config_items[row]

        # Populate stats editor
        self.populate_stats_form(item_data)

    def clear_stats_panel(self):
        """Clear all widgets and layouts from the stats panel."""
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)  # Take the first item in the layout
            if item.widget():
                # If it's a widget, delete it
                print(f"Removing widget: {item.widget()}")  # Debug
                item.widget().deleteLater()
            elif item.layout():
                # If it's a layout, clear it recursively
                print("Removing nested layout")  # Debug
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                print(f"Removing nested widget: {item.widget()}")  # Debug
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())  # Recursively clear nested layouts

    def populate_stats_form(self, item_data):
        """Populate the stats form with editable fields."""
        self.clear_stats_panel()  # Clear previous fields

        # Add fields for each key-value pair
        for key, value in item_data.items():
            field_layout = QHBoxLayout()

            # Label
            label = QLabel(f"{key}:")
            label.setFixedWidth(100)
            field_layout.addWidget(label)

            # Editable Field
            field = QLineEdit(str(value))
            field.setObjectName(key)
            field_layout.addWidget(field)

            self.stats_layout.addLayout(field_layout)

        # Add Save Button
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(lambda: self.save_item_changes(item_data))
        self.stats_layout.addWidget(save_button)

    def save_item_changes(self, item_data):
        """Save changes made to the selected item's stats."""
        for i in range(self.stats_layout.count()):
            layout_item = self.stats_layout.itemAt(i)
            if isinstance(layout_item, QHBoxLayout):
                key_label = layout_item.itemAt(0).widget()
                value_field = layout_item.itemAt(1).widget()

                if key_label and value_field:
                    key = key_label.text().replace(":", "").strip()
                    if key in item_data:
                        item_data[key] = value_field.text()

        # Refresh table to reflect changes
        self.populate_table()

    def switch_town(self, index):
        """Switch to the selected town's data."""
        if self.mode != "save" or not self.save_data:
            return

        # Get the selected town's items
        try:
            self.save_items = self.save_data["maps"][index]["items"]
            self.populate_table()  # Refresh the table with the new town's data
        except IndexError:
            QMessageBox.warning(self, "Error", "Invalid town selection.")

    def apply_dark_mode(self):
        """Apply a dark mode theme to the app."""
        dark_style = """
            QWidget {
                background-color: #2b2b2b;  /* Dark gray background */
                color: white;              /* White text */
                font-size: 12px;           /* Adjust font size for readability */
            }
            QTableWidget {
                background-color: #3c3f41; /* Slightly lighter gray for tables */
                gridline-color: #555555;
                color: white;
                selection-background-color: #555555;
                selection-color: black;
            }
            QHeaderView::section {
                background-color: #444444;
                color: white;
                padding: 4px;
                border: 1px solid #222222;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #444444;
                color: white;
                border: 1px solid #666666;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QLineEdit {
                background-color: #3c3f41;
                color: white;
                border: 1px solid #666666;
            }
        """
        self.setStyleSheet(dark_style)  # Apply style to the main window

    def find_items_by_id(self):
        """Find and select all items with the entered ID."""
        search_id = self.search_bar.text().strip()
        if not search_id.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric ID.")
            return

        search_id = int(search_id)
        self.table.clearSelection()  # Clear any existing selections

        matching_rows = []
        for row in range(self.table.rowCount()):
            item_id = int(self.table.item(row, 0).text())  # Get the ID from the first column
            if item_id == search_id:
                matching_rows.append(row)

        search_id = int(search_id)
        self.table.clearSelection()  # Clear any existing selections

        matching_rows = []
        for row in range(self.table.rowCount()):
            item_id = int(self.table.item(row, 0).text())  # Get the ID from the first column
            if item_id == search_id:
                matching_rows.append(row)

        if matching_rows:
            for row in matching_rows:
                self.table.selectRow(row)
            QMessageBox.information(self, "Search Complete", f"Found {len(matching_rows)} matching item(s).")
        else:
            QMessageBox.information(self, "Search Complete", "No matching items found.")




    def delete_selected_items(self):
        """Delete the selected items from the save file."""
        if self.mode != "save":
            QMessageBox.warning(self, "Error", "You can only delete items in Save File View.")
            return

        # Get selected rows
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select one or more items to delete.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_rows)} item(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        # Remove selected rows from `maps[0]["items"]`
        for row in selected_rows:
            del self.save_items[row]
            self.table.removeRow(row)

        QMessageBox.information(self, "Success", "Selected items deleted.")

    def load_file(self):
        """Load a save or config file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json);;All Files (*)", options=options
        )

        if not file_path:  # User canceled the file dialog
            return  # Exit the method gracefully

        try:
            with open(file_path, "r") as file:
                data = json.load(file)

            self.current_file = file_path  # Store the file path for saving later

            # Check if it's a save file (contains "maps")
            if "maps" in data:
                self.save_data = data
                self.mode = "save"
                self.populate_town_selector()
                self.switch_town(0)
                self.toggle_button.setText("Switch to Config View")

                # Update player info label
                player_info = data.get("playerInfo", {})
                pid = player_info.get("pid", "Unknown PID")
                name = player_info.get("name", "Unknown Name")
                self.player_info_label.setText(f"PID: {pid} | Name: {name}")

            elif "items" in data:
                self.config_items = data["items"]
                self.mode = "config"
                self.populate_table()
                self.toggle_button.setText("Switch to Save File View")

                # Clear player info label (not relevant in config mode)
                self.player_info_label.setText("No Save File Loaded")

            else:
                QMessageBox.warning(self, "Invalid File", "The selected file is not valid.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while loading the file:\n{str(e)}")

    def populate_town_selector(self):
        """Populate the town selector with available towns from the save file."""
        self.town_selector.clear()  # Clear existing towns
        for i, town in enumerate(self.save_data.get("maps", [])):
            town_name = f"Town {i + 1} (Level {town.get('level', 'Unknown')})"
            self.town_selector.addItem(town_name)

    def save_file(self):
        """Save the current file based on the mode."""
        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file loaded. Please load a file first.")
            return

        if self.mode == "config":
            QMessageBox.information(self, "Save Disabled", "Saving is disabled in Config Viewer mode.")
            return

        try:
            if self.mode == "save":
                # Save the save file
                with open(self.current_file, "w") as file:
                    json.dump(self.save_data, file, indent=4)

                QMessageBox.information(self, "Success", "Save file saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Unknown mode. Cannot save the file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save the file:\n{str(e)}")

    def populate_table(self):
        """Populate the table with either config or save file data."""
        self.table.setRowCount(0)
        self.table.setColumnWidth(3, 90)  # Set the width of the image column to 90 pixels

        # Build a mapping of ID -> img_name from the config file
        id_to_img_name = {int(item["id"]): item.get("img_name", None) for item in self.config_items}

        data = self.config_items if self.mode == "config" else self.save_items

        for row, item in enumerate(data):
            self.table.insertRow(row)
            self.table.setRowHeight(row, 90)  # Set the height of each row to 90 pixels

            # ID for config or save items
            id_item = int(item["id"]) if isinstance(item, dict) else int(item[0])

            # Name or Details
            if self.mode == "config":
                name_item = item.get("name", "Unknown")
                stats_item = str(item)
            else:
                name_item = f"Position: ({item[1]}, {item[2]})"
                stats_item = str(item)

            # Add table entries
            self.table.setItem(row, 0, QTableWidgetItem(str(id_item)))
            self.table.setItem(row, 1, QTableWidgetItem(name_item))
            self.table.setItem(row, 2, QTableWidgetItem(stats_item))

            # Image Handling
            if self.mode == "config":
                img_name = item.get("img_name", None)
            else:
                img_name = id_to_img_name.get(id_item)

            img_path = os.path.join(self.assets_path, f"{img_name}.jpg") if img_name else None
            if img_name and os.path.exists(img_path):
                pixmap = QPixmap(img_path)  # Keep the original size of the image (90x90)
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row, 3, img_label)
            else:
                self.table.setItem(row, 3, QTableWidgetItem("No Image"))

    def find_missing_ids(self):
        """Identify and display missing IDs in the save file."""
        if self.mode != "save":
            QMessageBox.warning(self, "Error", "Switch to Save File View to debug.")
            return

        # Get IDs from config file
        config_ids = {int(item["id"]) for item in self.config_items}

        # Get IDs from save file
        save_ids = {item[0] for item in self.save_items}

        # Find missing IDs
        missing_ids = save_ids - config_ids

        if missing_ids:
            QMessageBox.information(
                self,
                "Missing IDs Found",
                f"The following IDs are missing in the config file: {sorted(missing_ids)}"
            )
        else:
            QMessageBox.information(self, "All Good!", "No missing IDs found.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ConfigEditor(
        config_path="config",
        assets_path="assets/buildingthumbs"

    )
    editor.show()
    sys.exit(app.exec_())
