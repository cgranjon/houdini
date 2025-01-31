import os
import shutil
import hou
from PySide2 import QtWidgets, QtCore

#
#
# To copy file defined on a parameter (works on selected nodes)
# eg. copy all textures files from "map" parm into a defined folder
#
#

# Define a global variable to store the dialog object
file_copy_dialog = None

class FileCopyDialog(QtWidgets.QDialog):
    def __init__(self):
        super(FileCopyDialog, self).__init__()
        self.setWindowTitle("Copy File")
        self.setFixedSize(400, 250)  # Adjusted size to accommodate new checkbox
        self.layout = QtWidgets.QVBoxLayout()

        self.source_field = QtWidgets.QLineEdit()
        self.source_field.setPlaceholderText("Enter parameter name here")
        self.layout.addWidget(self.source_field)

        self.destination_field = QtWidgets.QLineEdit()
        self.destination_field.setPlaceholderText("Enter folder path here")
        self.layout.addWidget(self.destination_field)

        # Checkbox for updating parameter
        self.update_param_checkbox = QtWidgets.QCheckBox("Update parameter with new file path")
        self.layout.addWidget(self.update_param_checkbox)

        self.copy_button = QtWidgets.QPushButton("Copy")
        self.copy_button.clicked.connect(self.copy_files)
        self.layout.addWidget(self.copy_button)

        self.progress_bar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)

        # Change window flags to keep it open
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

    def copy_files(self):
        parameter_name = self.source_field.text()
        destination_folder = self.destination_field.text()

        if not os.path.isdir(destination_folder):
            hou.ui.displayMessage("Invalid destination folder path!")
            return

        nodes = hou.selectedNodes()

        total_files = len(nodes)
        copied_files = 0

        for node in nodes:
            try:
                source_file = node.evalParm(parameter_name)
                source_file_expr = node.parm(parameter_name).unexpandedString()
            except hou.OperationFailed:
                hou.ui.displayMessage(f"Invalid parameter name for node {node.name()}")
                continue

            filename_pattern = os.path.basename(source_file).split(".")[0]
            source_folder = os.path.dirname(source_file)
            matching_files = [os.path.join(source_folder, f) for f in os.listdir(source_folder) if filename_pattern in f]

            if not os.path.exists(source_folder) or not matching_files:
                hou.ui.displayMessage(f"Invalid source file path or filename pattern for node {node.name()}!")
                continue

            if not matching_files:
                hou.ui.displayMessage(f"No matching files found for node {node.name()}!")
                continue

            for file in matching_files:
                if not os.path.isfile(file):
                    hou.ui.displayMessage(f"Invalid source file path for node {node.name()}!")
                    continue

                # Copy file
                new_file_path = shutil.copy(file, destination_folder)
                
                # If checkbox is checked, update the parameter value
                if self.update_param_checkbox.isChecked():
                    orig_file_pattern = source_file_expr.split("/")[-1]
                    new_file_path = destination_folder + "/" + orig_file_pattern
                    
                    node.parm(parameter_name).set(new_file_path)

                copied_files += 1

                # Update progress bar value
                progress = int((copied_files / total_files) * 100)
                self.progress_bar.setValue(progress)

        hou.ui.displayMessage(f"File(s) copied successfully!")
        self.progress_bar.setValue(0)

# Create the dialog object and assign it to the global variable
file_copy_dialog = FileCopyDialog()
file_copy_dialog.show()
