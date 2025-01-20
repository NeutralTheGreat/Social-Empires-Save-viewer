import sys
import os
import json
import jsonpatch
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QFileDialog,
    QMessageBox, QLineEdit, QComboBox, QSizePolicy, QSpinBox, QCheckBox
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal


def apply_all_patches(base_config, patch_dir):
    """Apply all patches in the given directory to the base configuration."""
    for patch_file in os.listdir(patch_dir):
        if patch_file.endswith(".json"):
            patch_path = os.path.join(patch_dir, patch_file)
            try:
                with open(patch_path, "r") as file:
                    patch_data = json.load(file)
                patch = jsonpatch.JsonPatch(patch_data)
                base_config = patch.apply(base_config)
                print(f" * Patch applied successfully: {os.path.basename(patch_file)}")
            except Exception as e:
                print(f"Error applying patch {os.path.basename(patch_file)}: {e}")
    return base_config

class FileLoaderThread(QThread):
    file_loaded = pyqtSignal(dict)  # Signal to emit loaded data

    def __init__(self, file_path, assets_path, apply_patches=False):
        super().__init__()
        self.file_path = file_path
        self.assets_path = assets_path
        self.apply_patches = apply_patches  # Whether to apply patches

    def run(self):
        """Load the file in a separate thread and optionally apply patches."""
        try:
            with open(self.file_path, "r") as file:
                data = json.load(file)

            # Check if the file is a config file (contains "items")
            if self.apply_patches and "items" in data:
                print("Applying patches to config file...")
                data = apply_all_patches(data, "config/patch")  # Apply patches only to config files
            elif self.apply_patches:
                print("Patches will not be applied: File is not a config file.")

            # Emit the data once loaded
            self.file_loaded.emit(data)
        except Exception as e:
            print(f"Error loading file: {e}")





class ConfigEditor(QMainWindow):
    def __init__(self, config_path, assets_path, patch_dir=None):
        super().__init__()
        self.config_path = config_path
        self.assets_path = assets_path
        self.patch_dir = patch_dir  # Store the patch directory path

        self.config_items = []
        self.save_items = []
        self.current_file = None
        self.mode = "config"

        self.image_cache = {}  # Initialize the image cache

        self.init_ui()
        self.apply_dark_mode()  # Apply dark mode theme

    def load_cached_image(self, img_path):
        """Load an image from cache or disk."""
        if img_path not in self.image_cache:
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(90, 90, Qt.KeepAspectRatio)
                self.image_cache[img_path] = pixmap
            else:
                pixmap = QPixmap(90, 90)
                pixmap.fill(Qt.gray)
                self.image_cache[img_path] = pixmap
        return self.image_cache[img_path]



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
        self.toggle_button = QPushButton("Switch to Config/Save ")
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
        self.search_bar.setFixedWidth(150)  # Set a fixed width (adjust as needed)
        self.search_bar.setPlaceholderText("Enter ID to find...")
        top_layout.addWidget(self.search_bar)

        search_button = QPushButton("Find")
        search_button.clicked.connect(self.find_items_by_id)
        self.search_bar.setFixedWidth(150)
        top_layout.addWidget(search_button)

        # Town Selector Dropdown
        self.town_selector = QComboBox()
        self.town_selector.currentIndexChanged.connect(self.switch_town)
        top_layout.addWidget(QLabel("Select Town:"))
        self.search_bar.setFixedWidth(110)  # Set a fixed width (adjust as needed)
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

        # Right Section: Stats Panel (Save Mode Add Feature)
        right_layout = QVBoxLayout()

        # Add Button
        self.add_button = QPushButton("Add Selected Unit/Building")
        self.add_button.clicked.connect(self.add_item_to_save)
        right_layout.addWidget(self.add_button)

        # Quantity Selector
        self.quantity_box = QSpinBox()
        self.quantity_box.setMinimum(1)  # Minimum value
        self.quantity_box.setValue(1)  # Default value
        self.quantity_box.setToolTip("Enter the number of items to add.")
        right_layout.addWidget(self.quantity_box)

        # List of Units/Buildings (from Config)
        self.add_items_list = QTableWidget()
        self.add_items_list.setColumnCount(2)
        self.add_items_list.setHorizontalHeaderLabels(["ID", "Name"])
        self.add_items_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.add_items_list.setSelectionMode(QTableWidget.SingleSelection)
        self.add_items_list.setColumnWidth(0, 50)  # Adjust column width for ID
        self.add_items_list.setColumnWidth(1, 150)  # Adjust column width for Name

        # Add the table to the layout
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

        # In init_ui()
        self.apply_patches_checkbox = QCheckBox("Apply Patches on Load")
        self.apply_patches_checkbox.setChecked(True)  # Default to apply patches
        top_layout.addWidget(self.apply_patches_checkbox)

    def update_table(mode):
        """Refresh the table only if the mode or data has changed."""
        if mode == "save":
            self.populate_save_view()
        elif mode == "config":
            self.populate_table()

    class ImageLoaderThread(QThread):
        image_loaded = pyqtSignal(int, QPixmap)  # Signal to update UI

        def __init__(self, row, img_path):
            super().__init__()
            self.row = row
            self.img_path = img_path

        def run(self):
            if os.path.exists(self.img_path):
                pixmap = QPixmap(self.img_path).scaled(90, 90, Qt.KeepAspectRatio)
            else:
                pixmap = QPixmap(90, 90)
                pixmap.fill(Qt.gray)
            self.image_loaded.emit(self.row, pixmap)

    def load_image_in_thread(self, row, img_path):
        """Load an image in a separate thread."""
        thread = ImageLoaderThread(row, img_path)
        thread.image_loaded.connect(lambda r, pix: self.update_image_in_table(r, pix))
        thread.start()

    def update_image_in_table(self, row, pixmap):
        """Update the table with the loaded image."""
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        self.table.setCellWidget(row, 3, image_label)  # Example column index for image

    def load_image_lazy(row, img_path):
        """Load an image lazily when a row becomes visible."""
        image_label = QLabel()
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(90, 90, Qt.KeepAspectRatio)
            image_label.setPixmap(pixmap)
        else:
            pixmap = QPixmap(90, 90)
            pixmap.fill(Qt.gray)  # Placeholder for missing images
            image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        self.table.setCellWidget(row, 3, image_label)  # Example column index for image

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
            #print(f"Image Path: {img_path}, Exists: {os.path.exists(img_path)}")  # Debug print for paths
            image_label = QLabel()

            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():  # Check if pixmap is valid before scaling
                    pixmap = pixmap.scaled(90, 90, Qt.KeepAspectRatio)  # Scale to 90x90
                    image_label.setPixmap(pixmap)
            else:
                # Use a placeholder pixmap for missing images
                pixmap = QPixmap(90, 90)
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

        # Get the desired quantity from the spinbox
        quantity = self.quantity_box.value()  # Get value from spinbox (defaults to 1)

        # Add the item multiple times
        for _ in range(quantity):
            new_item = [item_id, 54, 54, 0, 0, 0, [], {}]  # Default attributes
            self.save_items.append(new_item)

        # Refresh the table
        self.populate_table()
        QMessageBox.information(self, "Success", f"Added {quantity} x {item_name} (ID: {item_id}) to the save file.")

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
                #print(f"Removing widget: {item.widget()}")  # Debug
                item.widget().deleteLater()
            elif item.layout():
                # If it's a layout, clear it recursively
                #print("Removing nested layout")  # Debug
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                #print(f"Removing nested widget: {item.widget()}")  # Debug
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
            return

        self.current_file = file_path  # Set the current file path here

        # Load file with patch option
        apply_patches = self.apply_patches_checkbox.isChecked()
        self.loader_thread = FileLoaderThread(file_path, self.assets_path, apply_patches=apply_patches)
        self.loader_thread.setParent(self)  # Set parent
        self.loader_thread.file_loaded.connect(self.on_file_loaded)
        self.loader_thread.start()

    def save_file(self):
        """Save the current file based on the mode."""
        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file loaded. Please load a file first.")
            return

        # Prevent saving in Config Viewer mode
        if self.mode == "config":
            QMessageBox.information(self, "Save Disabled", "Saving is disabled in Config Viewer mode.")
            return

        try:
            if self.mode == "save":
                # Save the save file
                with open(self.current_file, "w") as file:
                    json.dump(self.save_data, file, indent=4)

                QMessageBox.information(self, "Success", f"Save file saved successfully:\n{self.current_file}")
            else:
                QMessageBox.warning(self, "Error", "Unknown mode. Cannot save the file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save the file:\n{str(e)}")

    def closeEvent(self, event):
        """Ensure threads are stopped when closing the application."""
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait()
        super().closeEvent(event)

    def populate_town_selector(self):
        """Populate the town selector with available towns from the save file."""
        self.town_selector.clear()  # Clear existing towns
        for i, town in enumerate(self.save_data.get("maps", [])):
            town_name = f"Town {i + 1} (Level {town.get('level', 'Unknown')})"
            self.town_selector.addItem(town_name)


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



    def on_file_loaded(self, data):
        """Handle the loaded file data."""
        print("Loading Config/Save file and assets might take a while...")
        if "maps" in data:
            self.save_data = data
            self.populate_town_selector()
            self.switch_town(0)
            self.toggle_button.setText("Switch to Config/Save View") #Switch to Config View

            # Update player info label
            player_info = data.get("playerInfo", {})
            pid = player_info.get("pid", "Unknown PID")
            name = player_info.get("name", "Unknown Name")
            self.player_info_label.setText(f"PID: {pid} | Name: {name}")

        elif "items" in data:
            self.config_items = data["items"]
            self.populate_table()
            self.toggle_button.setText("Switch to Save File View") #Switch to Save File View

            # Clear player info label
            self.player_info_label.setText("Switch to Config/Save View")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ConfigEditor(
        config_path="config",
        assets_path="assets/buildingthumbs",
        patch_dir="config/patch"  # Properly forward the patch directory
    )
    editor.show()
    sys.exit(app.exec_())

