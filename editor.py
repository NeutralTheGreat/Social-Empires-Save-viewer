import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QFileDialog,
    QMessageBox, QLineEdit, QComboBox
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
        self.setGeometry(100, 100, 1200, 600)

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
        top_layout.addWidget(self.town_selector)

        # Add Top Layout to Main Layout
        main_layout.addLayout(top_layout)

        # Middle Section: Table and Image
        middle_layout = QHBoxLayout()

        # Left Section: Table
        left_layout = QVBoxLayout()

        # Table for Data Display
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name/Details", "Position/Stats", "Image"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        left_layout.addWidget(self.table)

        middle_layout.addLayout(left_layout, 2)

        # Right Section: Image Display
        right_layout = QVBoxLayout()
        self.image_label = QLabel("No Image")
        self.image_label.setFixedSize(250, 250)
        self.image_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.image_label)
        middle_layout.addLayout(right_layout, 1)

        # Add Middle Layout to Main Layout
        main_layout.addLayout(middle_layout)

        # Finalize Layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        



         


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




    def toggle_mode(self):
        """Toggle between config and save file views."""
        if self.mode == "config":
            self.mode = "save"
            self.toggle_button.setText("Switch to Config View")
        else:
            self.mode = "config"
            self.toggle_button.setText("Switch to Save File View")
        self.populate_table()

    def load_file(self):
        """Open a file for editing/viewing."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json)", options=options
        )
        if file_path:
            self.current_file = file_path
            with open(file_path, "r") as file:
                self.save_data = json.load(file)  # Load the entire save file
            self.config_items = self.save_data.get("items", []) if self.mode == "config" else []
            self.save_items = self.save_data["maps"][0]["items"]  # Reference maps[0]["items"]
            self.populate_table()

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
        """Open a file for editing/viewing."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json)", options=options
        )
        if file_path:
            self.current_file = file_path
            with open(file_path, "r") as file:
                data = json.load(file)

        if self.mode == "config":
            if "items" in data:
                self.config_items = data["items"]
                self.save_items = []
                self.populate_table()
            else:
                QMessageBox.warning(self, "Error", "Invalid configuration file format.")
        else:
            if "maps" in data:
                self.save_data = data
                self.town_selector.clear()  # Clear existing items in the dropdown

                # Populate the dropdown with town indices or descriptions
                for i, town in enumerate(self.save_data["maps"]):
                    town_name = f"Town {i + 1} (Level {town.get('level', 'Unknown')})"
                    self.town_selector.addItem(town_name)

                # Default to the first town
                self.switch_town(0)
            else:
                QMessageBox.warning(self, "Error", "Invalid save file format.")

    def save_file(self):
        """Save the current data back to the file."""
        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file loaded.")
            return

        # Debug: Inspect the structure before saving
        print(f"Saving to {self.current_file}")
        print(json.dumps(self.save_data, indent=4))  # Print the full structure

        try:
            with open(self.current_file, "w") as file:
                json.dump(self.save_data, file, indent=4)
            QMessageBox.information(self, "Success", "File saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

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
        assets_path = "assets/buildingthumbs"

    )
    editor.show()
    sys.exit(app.exec_())
