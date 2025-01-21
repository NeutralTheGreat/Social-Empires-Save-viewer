
#  Social Empires & Social Wars Save File Editor

This is a Python-based GUI application for viewing, editing, and debugging save files for Social Empires and Social Wars. The app supports inspecting and modifying units/buildings, applying patches, and handling game-specific configurations.


## Features
  - Save File Viewer:

  - View all units/buildings in the save file.

  - Switch between towns (for Social Empires).
   
  - Edit or delete selected items.

## Config Viewer:

  - Inspect unit/building stats from the configuration file.

  - Check missing IDs between the config and save file.

  - View thumbnails for units/buildings.

## Dynamic UI:

  - Seamlessly switch between Save File mode and Config mode.
   
  - Add new units/buildings to the save file in Save mode.

  - Double-click functionality to quickly add items from the config.

## Patch Support:

  - Automatically apply patches to configuration files during loading.

## Multi-Game Support:

  - Automatically detects the game type (Social Empires or Social Wars).
  - Adjusts functionality based on the game type (e.g., town switching for Social Empires).

## Prerequisites

 - Python 3.9 or newer.
 - Required Python libraries:
 - PyQt5
 - json
 - os
 - jsonpatch (optional, for patching).

## Install dependencies using:

  - pip install PyQt5 jsonpatch

## drop editor.py in the directory it should look like this 

├── assets/

│   ├── buildingthumbs/      # For Social Empires

│   └── thumbs/              # For Social Wars

├── config/

│   ├── game_config.json     # Configuration file

│   └── patch/               # Patch files directory

├── editor.py                # Main Python script


## Run the editor:
 
  - editor.py

## Usage


#Loading Files
1. Click Open File to load a save file or configuration file.
2. The app will automatically detect:
   - Save File:
      - Social Empires: Multi-town save with a town selector.
      - Social Wars: Single-town save with no selector.
   - Config File: Displays the unit/building stats.

##S ave File Mode
  - View all items in the selected town.
  - Delete selected items.
  - Add new items from the configuration file.
  - Save changes back to the save file.

# Config Mode
 - View unit/building stats, including images.
 - Check for missing IDs between the config and save file.
 - Switching Modes
 - Use the Switch to Save File/Config View button to toggle between modes.

## Known Issues

  - Performance may degrade with very large save or config files due to image loading.
  - Dynamic image loading is partially implemented; optimization may be required.(Currently disabled)
  - Some features (e.g., adding items) require the config file to be loaded.


## Troubleshooting
   1. No Images Displayed:

      - Ensure the assets/buildingthumbs or assets/thumbs directories contain the correct image files.

   2. Patches Not Applied:

      - Ensure patch files are located in the config/patch directory.

   3. Errors When Loading Save Files:

      - Check the file structure to ensure "maps" and "items" are correctly formatted.
