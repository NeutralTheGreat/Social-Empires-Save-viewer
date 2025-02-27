# editor.py
# -*- coding: utf-8 -*-

import sys
import os
import json
import jsonpatch
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QTableView,
    QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QFileDialog,
    QMessageBox, QLineEdit, QComboBox, QSpinBox, QCheckBox, QSplitter, QDialogButtonBox,
    QFormLayout, QDialog
)

###############################################################################
# PATCH HELPER
###############################################################################
def apply_all_patches(base_config, patch_dir):
    """Apply all patches in the given directory to the base configuration."""
    if not os.path.exists(patch_dir):
        return base_config  # No patches to apply

    for patch_file in os.listdir(patch_dir):
        if patch_file.endswith(".json"):
            patch_path = os.path.join(patch_dir, patch_file)
            try:
                with open(patch_path, "r", encoding="utf-8") as file:
                    patch_data = json.load(file)
                patch = jsonpatch.JsonPatch(patch_data)
                base_config = patch.apply(base_config)
                print(f" * Patch applied successfully: {os.path.basename(patch_file)}")
            except Exception as e:
                print(f"Error applying patch {os.path.basename(patch_file)}: {e}")
    return base_config

###############################################################################
# WORKER THREAD FOR LOADING FILES
###############################################################################
class FileLoaderThread(QThread):
    """Loads a JSON file in a separate thread (optional patch application)."""
    file_loaded = pyqtSignal(dict)  # Signal to emit loaded data

    def __init__(self, file_path, patch_dir=None, apply_patches=False):
        super().__init__()
        self.file_path = file_path
        self.patch_dir = patch_dir
        self.apply_patches = apply_patches

    def run(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            # If it's a config file with "items" and user wants patches, apply them
            if self.apply_patches and "items" in data and self.patch_dir:
                data = apply_all_patches(data, self.patch_dir)

            self.file_loaded.emit(data)
        except Exception as e:
            print(f"Error loading file: {e}")
            self.file_loaded.emit({})  # Emit empty dict on failure

###############################################################################
# MAIN APPLICATION WINDOW
###############################################################################
class ConfigEditor(QMainWindow):
    def __init__(self, patch_dir=None, assets_paths=None):
        super().__init__()
        self.patch_dir = patch_dir or "config/patch"
        self.assets_paths = assets_paths if isinstance(assets_paths, list) else [assets_paths]

        # Data Structures
        self.config_items = []       # from config.json
        self.save_data = {}          # from save.json
        self.save_items = []         # items in the currently selected town
        self.current_file = None     # path to the currently opened file
        self.mode = "config"         # "config" or "save"

        # UI Elements
        self.table = None
        self.add_items_list = None
        self.toggle_button = None
        self.town_selector = None
        self.player_info_label = None
        self.apply_patches_checkbox = None
        self.search_bar = None
        self.stats_layout = None
        self.stats_widget = None
        self.quantity_box = None
        self.add_button = None

        # Initialize the UI
        self.init_ui()
        self.apply_dark_mode()
        self.set_table_selection_mode()
        self.setWindowTitle("Social Empires/Wars Save File Editor")

    ###########################################################################
    # UTILITY METHODS
    ###########################################################################
    def get_asset_path(self, asset_name):
        """
        Locate an asset in the specified assets paths. Returns the full path if found, otherwise None.
        """
        for path in self.assets_paths or []:
            if not path:
                continue
            full_path = os.path.join(path, asset_name)
            if os.path.exists(full_path):
                return full_path
        return None

    def edit_player_resources(self):
        """Open a dialog to edit player resource values."""
        # Ensure the necessary sections exist
        if ("playerInfo" not in self.save_data or
                "maps" not in self.save_data or
                not self.save_data["maps"] or
                "privateState" not in self.save_data):
            QMessageBox.warning(self, "Missing Data", "Required data not found in the loaded save file.")
            return

        # Get the data from their correct places
        player_info = self.save_data["playerInfo"]
        # Use the first map entry as the main map for resource editing
        map_data = self.save_data["maps"][0]
        private_state = self.save_data["privateState"]

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Player Resources")
        form_layout = QFormLayout(dialog)

        # Prepare spinboxes for each resource field from its corresponding section.
        spinboxes = {}
        resource_fields = {
            "cash": player_info.get("cash", 0),
            "coins": map_data.get("coins", 0),
            "xp": map_data.get("xp", 0),
            "level": map_data.get("level", 1),
            "stone": map_data.get("stone", 0),
            "wood": map_data.get("wood", 0),
            "food": map_data.get("food", 0),
            "mana": private_state.get("mana", 0)
        }

        for key, value in resource_fields.items():
            spin = QSpinBox(dialog)
            spin.setMaximum(1000000000)  # a large maximum
            spin.setValue(value)
            form_layout.addRow(QLabel(key.capitalize() + ":"), spin)
            spinboxes[key] = spin

        # Dropdown for race – assume only "h" (humans) and "t" (trolls)
        race_options = ["h", "t"]
        race_combo = QComboBox(dialog)
        race_combo.addItems(race_options)
        current_race = map_data.get("race", "h")
        if current_race in race_options:
            race_combo.setCurrentIndex(race_options.index(current_race))
        form_layout.addRow(QLabel("Race:"), race_combo)

        # Dropdown for skin options
        skin_options = [
            "Grassy Meadows",
            "Sunny Desert",
            "Snowy Plains",
            "Ocean",
            "Rocky Mountains",
            "Lush Jungle",
            "Cloudy Heaven"
        ]
        skin_combo = QComboBox(dialog)
        skin_combo.addItems(skin_options)
        current_skin = map_data.get("skin", 0)
        # If skin is stored as a string, convert it to int if possible
        try:
            current_skin = int(current_skin)
        except ValueError:
            current_skin = 0
        if 0 <= current_skin < len(skin_options):
            skin_combo.setCurrentIndex(current_skin)
        form_layout.addRow(QLabel("Skin:"), skin_combo)

        # OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        form_layout.addRow(button_box)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            # Update the correct sections with the new values
            player_info["cash"] = spinboxes["cash"].value()
            map_data["coins"] = spinboxes["coins"].value()
            map_data["xp"] = spinboxes["xp"].value()
            map_data["level"] = spinboxes["level"].value()
            map_data["stone"] = spinboxes["stone"].value()
            map_data["wood"] = spinboxes["wood"].value()
            map_data["food"] = spinboxes["food"].value()
            private_state["mana"] = spinboxes["mana"].value()
            map_data["race"] = race_options[race_combo.currentIndex()]
            map_data["skin"] = skin_combo.currentIndex()

            # Write the updates back into the save data
            self.save_data["playerInfo"] = player_info
            self.save_data["maps"][0] = map_data
            self.save_data["privateState"] = private_state

            QMessageBox.information(self, "Updated", "Player resources updated.")

    def apply_dark_mode(self):
        """Simple dark mode styling."""
        dark_style = """
            QWidget {
                background-color: #2b2b2b;  
                color: white;
                font-size: 12px;
            }
            QTableWidget {
                background-color: #3c3f41;
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
            QLabel { color: white; }
            QPushButton {
                background-color: #444444;
                color: white;
                border: 1px solid #666666;
                padding: 6px;
            }
            QPushButton:hover { background-color: #555555; }
            QLineEdit {
                background-color: #3c3f41;
                color: white;
                border: 1px solid #666666;
            }
            QSpinBox {
                background-color: #3c3f41;
                color: white;
                border: 1px solid #666666;
            }
        """
        self.setStyleSheet(dark_style)

    def set_table_selection_mode(self):
        """Set the table's selection mode based on the current mode."""
        if self.mode == "config":
            if self.table:
                self.table.setSelectionMode(QTableWidget.SingleSelection)
        else:  # "save"
            if self.table:
                self.table.setSelectionMode(QTableWidget.MultiSelection)

    #######################################################################
    # LAZY LOADING LOGIC
    #######################################################################
    def lazy_load_visible_images(self, target_table, data_list, is_config_table=False, image_col=3):
        if not target_table or target_table.rowCount() == 0:
            return

        viewport_rect = target_table.viewport().rect()

        for row in range(target_table.rowCount()):
            item = target_table.item(row, 0)
            if not item:
                continue

            row_rect = target_table.visualItemRect(item)
            if viewport_rect.intersects(row_rect):
                # Always remove any placeholder or existing widget first
                target_table.removeCellWidget(row, image_col)
                if target_table.item(row, image_col):
                    target_table.takeItem(row, image_col)

                # Retrieve the image name from the data
                if is_config_table:
                    img_name = data_list[row].get("img_name", None)
                else:
                    id_item = data_list[row][0]
                    img_name = self._get_img_name_from_config(id_item)

                if img_name:
                    img_path = self.get_asset_path(f"{img_name}.jpg")
                    if img_path and os.path.exists(img_path):
                        pixmap = QPixmap(img_path).scaled(90, 90, Qt.KeepAspectRatio)
                        label = QLabel()
                        label.setPixmap(pixmap)
                        label.setAlignment(Qt.AlignCenter)
                        target_table.setCellWidget(row, image_col, label)
                    else:
                        self._set_placeholder_image(target_table, row, image_col)
                else:
                    self._set_placeholder_image(target_table, row, image_col)

    def _set_placeholder_image(self, table, row, col):
        label = QLabel()
        placeholder = QPixmap(90, 90)
        placeholder.fill(Qt.gray)
        label.setPixmap(placeholder)
        label.setAlignment(Qt.AlignCenter)
        table.setCellWidget(row, col, label)

    def _get_img_name_from_config(self, item_id):
        for cfg_item in self.config_items:
            if int(cfg_item.get("id", -1)) == int(item_id):
                return cfg_item.get("img_name", None)
        return None

    ###########################################################################
    # UI INITIALIZATION
    ###########################################################################
    def init_ui(self):
        # Main Window Settings
        self.setMinimumSize(900, 600)



        # Main Layout
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()

        # Toggle Button (Switch Mode)
        self.toggle_button = QPushButton("Switch to Config/Save View")
        self.toggle_button.clicked.connect(self.toggle_mode)
        top_layout.addWidget(self.toggle_button)

        # Open File Button
        open_button = QPushButton("Open File")
        open_button.clicked.connect(self.load_file)
        top_layout.addWidget(open_button)

        # Save File Button
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_file)
        top_layout.addWidget(save_button)

        # Find Missing IDs Button
        debug_button = QPushButton("Find Missing IDs")
        debug_button.clicked.connect(self.find_missing_ids)
        top_layout.addWidget(debug_button)

        # Delete Button
        delete_button = QPushButton("Delete Selected Items")
        delete_button.clicked.connect(self.delete_selected_items)
        top_layout.addWidget(delete_button)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setFixedWidth(150)
        self.search_bar.setPlaceholderText("Enter ID to find...")
        top_layout.addWidget(self.search_bar)

        # Search Button
        search_button = QPushButton("Find")
        search_button.clicked.connect(self.find_items_by_id)
        top_layout.addWidget(search_button)

        # Town Selector
        town_label = QLabel("Select Town:")
        self.town_selector = QComboBox()
        self.town_selector.currentIndexChanged.connect(self.switch_town)
        top_layout.addWidget(town_label)
        top_layout.addWidget(self.town_selector)

        # Player Info Label
        self.player_info_label = QLabel("No Save File Loaded")
        self.player_info_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.player_info_label)

        # Patches Checkbox
        self.apply_patches_checkbox = QCheckBox("Apply Patches on Load")
        self.apply_patches_checkbox.setChecked(True)
        top_layout.addWidget(self.apply_patches_checkbox)

        main_layout.addLayout(top_layout)

        # Splitter for Middle Section
        splitter = QSplitter(Qt.Horizontal)

        # Left Widget (Main Table)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name/Details", "Position/Stats", "Image"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalScrollBar().valueChanged.connect(lambda: self.on_scroll_main_table())
        self.table.itemSelectionChanged.connect(self.update_stats_panel)

        left_layout.addWidget(self.table)
        splitter.addWidget(left_widget)

        # Right Widget (Stats + Add Items)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Add Button & SpinBox
        self.add_button = QPushButton("Add Selected Unit/Building")
        self.add_button.clicked.connect(self.add_item_to_save)
        right_layout.addWidget(self.add_button)

        self.quantity_box = QSpinBox()
        self.quantity_box.setMinimum(1)
        self.quantity_box.setValue(1)
        right_layout.addWidget(self.quantity_box)

        # Table of Config Items for Adding to Save
        self.add_items_list = QTableWidget()
        self.add_items_list.setColumnCount(3)
        self.add_items_list.setHorizontalHeaderLabels(["ID", "Name", "Image"])
        self.add_items_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.add_items_list.setSelectionMode(QTableWidget.SingleSelection)
        self.add_items_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.add_items_list.verticalScrollBar().valueChanged.connect(lambda: self.on_scroll_add_items_table())
        self.add_items_list.itemDoubleClicked.connect(self.handle_item_double_click)
        right_layout.addWidget(self.add_items_list)

        # Stats Widget
        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_widget)
        right_layout.addWidget(self.stats_widget)

        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        main_layout.addWidget(splitter)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Hide add items UI in config mode by default
        self.toggle_mode(force_config=True)

        # In your top_layout creation section in init_ui:
        edit_resources_button = QPushButton("Edit Resources")
        edit_resources_button.clicked.connect(self.edit_player_resources)
        top_layout.addWidget(edit_resources_button)

    ###########################################################################
    # MODE SWITCH
    ###########################################################################
    def toggle_mode(self, force_config=False):
        """
        Switch between Config and Save modes. 
        force_config=True ensures we start in config mode on app launch.
        """
        if force_config:
            self.mode = "config"
        else:
            self.mode = "save" if self.mode == "config" else "config"

        if self.mode == "config":
            self.setWindowTitle("Config Mode")
            self.add_button.hide()
            self.quantity_box.hide()
            self.add_items_list.hide()
            self.toggle_button.setText("Switch to Save File View")
        else:
            self.setWindowTitle("Save Mode")
            self.add_button.show()
            self.quantity_box.show()
            self.add_items_list.show()
            self.toggle_button.setText("Switch to Config View")

        self.set_table_selection_mode()
        self.populate_table()

        if self.mode == "save":
            # If we have config items, populate the add_items_list
            if self.config_items:
                self.populate_add_items_list()

    ###########################################################################
    # FILE LOAD / SAVE
    ###########################################################################
    def load_file(self):
        """Prompt user for a JSON file and load it."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        self.current_file = file_path
        apply_patches = self.apply_patches_checkbox.isChecked()
        self.loader_thread = FileLoaderThread(
            file_path, patch_dir=self.patch_dir, apply_patches=apply_patches
        )
        self.loader_thread.file_loaded.connect(self.on_file_loaded)
        self.loader_thread.start()

    def on_file_loaded(self, data):
        """Callback when file loading thread finishes."""
        if not data:
            QMessageBox.critical(self, "Error", "Failed to load file or file is empty.")
            return

        # If the file has "maps", assume it's a save file
        if "maps" in data:
            self.save_data = data
            self.populate_town_selector()
            self.switch_town(0)  # Default to first town
            self.player_info_label.setText(
                f"PID: {data.get('playerInfo', {}).get('pid', 'Unknown')} | "
                f"Name: {data.get('playerInfo', {}).get('name', 'Unknown')}"
            )
            self.toggle_button.setText("Switch to Config View")
            self.mode = "save"
            self.populate_table()
        # If the file has "items", assume it's a config
        elif "items" in data:
            self.config_items = data["items"]
            self.populate_table()
            self.toggle_button.setText("Switch to Save File View")
            self.mode = "config"
        else:
            QMessageBox.warning(self, "Warning", "Unrecognized file structure.")

    def save_file(self):
        """Save the current file if we're in save mode."""
        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file loaded.")
            return

        if self.mode == "config":
            QMessageBox.information(self, "Info", "Saving config is disabled in this example.")
            return

        if self.mode == "save":
            try:
                with open(self.current_file, "w", encoding="utf-8") as file:
                    json.dump(self.save_data, file, indent=4)
                QMessageBox.information(self, "Success", f"Saved file: {self.current_file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

    ###########################################################################
    # TABLE POPULATION (CONFIG / SAVE)
    ###########################################################################
    def populate_town_selector(self):
        """Populate the town dropdown based on the save data."""
        self.town_selector.clear()
        if not self.save_data or "maps" not in self.save_data:
            return
        towns = self.save_data.get("maps", [])
        for i, town in enumerate(towns):
            name = town.get("name", f"Town {i+1}")
            self.town_selector.addItem(name)

        # If there's only one town, disable the dropdown
        if len(towns) == 1:
            self.town_selector.setEnabled(False)
        else:
            self.town_selector.setEnabled(True)

    def switch_town(self, index):
        """Switch the current town in save_data."""
        if not self.save_data or "maps" not in self.save_data:
            return
        towns = self.save_data["maps"]
        if 0 <= index < len(towns):
            self.save_items = towns[index].get("items", [])
            if self.mode == "save":
                self.populate_table()

    def populate_table(self):
        """Populate the main table based on current mode."""
        self.table.setRowCount(0)
        if self.mode == "config":
            data = self.config_items
        else:
            data = self.save_items

        for row, item in enumerate(data):
            self.table.insertRow(row)
            self.table.setRowHeight(row, 90)

            if self.mode == "config":
                # item is a dict
                item_id = item.get("id", "N/A")
                name = item.get("name", "Unnamed")
                stats = str(item)
            else:
                # item is a list
                item_id = item[0]
                name = f"Position: ({item[1]}, {item[2]})"
                stats = str(item)

            self.table.setItem(row, 0, QTableWidgetItem(str(item_id)))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(stats))
            # Image column initially blank; lazy load on scroll
            placeholder = QTableWidgetItem("Loading...")
            self.table.setItem(row, 3, placeholder)

        # Trigger a manual lazy load after population
        self.on_scroll_main_table()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Trigger lazy loading on resize (for both tables if needed)
        self.on_scroll_main_table()
        self.on_scroll_add_items_table()

    def populate_add_items_list(self):
        """Populate the right-side config table (for adding items to the save)."""
        self.add_items_list.setRowCount(0)
        for row, item in enumerate(self.config_items):
            self.add_items_list.insertRow(row)
            self.add_items_list.setRowHeight(row, 90)

            item_id = item.get("id", "N/A")
            name = item.get("name", "Unnamed")

            self.add_items_list.setItem(row, 0, QTableWidgetItem(str(item_id)))
            self.add_items_list.setItem(row, 1, QTableWidgetItem(name))
            # Set placeholder in image column (column index 2)
            placeholder = QTableWidgetItem("Loading...")
            self.add_items_list.setItem(row, 2, placeholder)

        # Use a QTimer to ensure the UI has finished laying out before lazy loading
        QTimer.singleShot(0, lambda: self.on_scroll_add_items_table())

    ###########################################################################
    # SCROLL EVENTS FOR LAZY LOADING
    ###########################################################################
    def on_scroll_main_table(self):
        """Called when the main table is scrolled; triggers lazy loading."""
        if self.mode == "config":
            self.lazy_load_visible_images(
                target_table=self.table,
                data_list=self.config_items,
                is_config_table=True
            )
        else:
            self.lazy_load_visible_images(
                target_table=self.table,
                data_list=self.save_items,
                is_config_table=False
            )

    def on_scroll_add_items_table(self):
        """Called when the add-items table is scrolled; triggers lazy loading."""
        # For the add-items table, the image column is index 2.
        self.lazy_load_visible_images(
            target_table=self.add_items_list,
            data_list=self.config_items,
            is_config_table=True,
            image_col=2
        )

    ###########################################################################
    # ITEM SELECTION & STATS PANEL
    ###########################################################################
    def update_stats_panel(self):
        """
        If in config mode, show stats for the selected config item.
        If in save mode, clear or show minimal info.
        """
        if self.mode == "save":
            self.clear_stats_panel()
            return

        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            self.clear_stats_panel()
            return

        row = selected_indexes[-1].row()
        if row < 0 or row >= len(self.config_items):
            self.clear_stats_panel()
            return

        item_data = self.config_items[row]
        self.populate_stats_form(item_data)

    def clear_stats_panel(self):
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def populate_stats_form(self, item_data):
        """Populate the stats form with key/value pairs for the config item."""
        self.clear_stats_panel()
        for key, value in item_data.items():
            row_layout = QHBoxLayout()
            label = QLabel(f"{key}:")
            label.setFixedWidth(100)
            row_layout.addWidget(label)

            field = QLineEdit(str(value))
            row_layout.addWidget(field)
            self.stats_layout.addLayout(row_layout)

    ###########################################################################
    # ADD / DELETE / FIND / DEBUG
    ###########################################################################
    def handle_item_double_click(self, item):
        """Double-click on the add-items list to add an item to the save."""
        self.add_item_to_save()

    def add_item_to_save(self):
        """Add the selected config item to the save file."""
        if self.mode != "save":
            QMessageBox.warning(self, "Error", "Only available in Save Mode.")
            return
        row = self.add_items_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "No item selected to add.")
            return

        item_id = self.add_items_list.item(row, 0).text()
        item_name = self.add_items_list.item(row, 1).text()
        quantity = self.quantity_box.value()

        # Example: [ID, x, y, 0, 0, 0, [], {}]
        for _ in range(quantity):
            self.save_items.append([int(item_id), 54, 54, 0, 0, 0, [], {}])

        self.populate_table()
        QMessageBox.information(self, "Added", f"Added {quantity}x {item_name} (ID: {item_id})")

    def delete_selected_items(self):
        """Delete selected rows from the save items."""
        if self.mode != "save":
            QMessageBox.warning(self, "Error", "Only available in Save Mode.")
            return

        selected_rows = list({idx.row() for idx in self.table.selectedIndexes()})
        selected_rows.sort(reverse=True)
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select items to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete {len(selected_rows)} item(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        for row in selected_rows:
            if 0 <= row < len(self.save_items):
                del self.save_items[row]

        self.populate_table()
        QMessageBox.information(self, "Deleted", f"Deleted {len(selected_rows)} item(s).")

    def find_items_by_id(self):
        """Select rows matching the ID in the search bar."""
        search_id_str = self.search_bar.text().strip()
        if not search_id_str.isdigit():
            QMessageBox.warning(self, "Error", "Enter a valid numeric ID.")
            return

        search_id = int(search_id_str)
        self.table.clearSelection()
        matches = []

        for row in range(self.table.rowCount()):
            cell_value = self.table.item(row, 0).text()
            if cell_value.isdigit() and int(cell_value) == search_id:
                matches.append(row)

        for row in matches:
            self.table.selectRow(row)

        if matches:
            QMessageBox.information(self, "Found", f"Found {len(matches)} matching items.")
        else:
            QMessageBox.information(self, "Not Found", "No matching items found.")

    def find_missing_ids(self):
        """Find IDs in the save file not present in the config."""
        if self.mode != "save":
            QMessageBox.warning(self, "Error", "Switch to Save Mode to debug.")
            return
        config_ids = {int(item["id"]) for item in self.config_items}
        save_ids = {sitem[0] for sitem in self.save_items}
        missing = save_ids - config_ids
        if missing:
            QMessageBox.information(
                self,
                "Missing IDs",
                f"IDs not in config: {sorted(missing)}"
            )
        else:
            QMessageBox.information(self, "All Good", "No missing IDs.")

###############################################################################
# MAIN ENTRY POINT
###############################################################################
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Example usage: 
    #   - patch_dir = "config/patch"
    #   - assets_paths = ["assets/buildingthumbs", "assets/thumbs"]
    editor = ConfigEditor(
        patch_dir="config/patch",
        assets_paths=["assets/buildingthumbs", "assets/thumbs"]
    )
    editor.show()
    sys.exit(app.exec_())
