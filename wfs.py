import convert_ui_and_qrc_files
import json
import os
import pathlib
import shutil
import sys
from functools import partial
from pprint import pprint

import imagehash
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QKeySequence, QPalette
from PyQt5.QtWidgets import (QAbstractItemView, QDialog, QFileDialog,
                             QFileSystemModel, QShortcut)
from send2trash import send2trash


from main_ui import Ui_MainWindow
from vers import get_version

if not os.path.exists('delete'):
    os.makedirs('delete')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # style window 
        self.setWindowTitle("Waifu File Sort")
        app_icon = QtGui.QIcon()
        app_icon.addFile("./icons/waifu_sort.png", QtCore.QSize(256, 256))
        self.setWindowIcon(app_icon)

        # store important data
        self.path_hotkey_dict = {}
        self.hotkey_path_dict = {}
        self._shortcut_list = []
        self.undo_list = []
        self.delete_folder = str(pathlib.Path(find_data_file("delete")))
        self.current_file_folder = ""
        self.pic_ext_list = [".jpg", ".png", ".webp", ".JPEG", ".PNG"]
        self.default_palette = QtGui.QGuiApplication.palette()

        # initialize source directory
        self.model = QFileSystemModel()
        self.model.setNameFilters(
            ["*.jpg", "*.png", "*.webp", "*.JPEG", "*.PNG"])
        self.model.setNameFilterDisables(False)
        self.ui.treeView.setModel(self.model)
        self.ui.treeView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.tableWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.ui.treeView.selectionModel().selectionChanged.connect(
            self.update_image_label
        )

        # hotkeys
        self.delShortcut = QShortcut(QKeySequence("Delete"), self)
        self.delShortcut.activated.connect(
            partial(self.move_cb, None, self.delete_folder)
        )

        self.undoShortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undoShortcut.activated.connect(self.undo_cb)


        # callbacks init
        self.ui.browseBtn.clicked.connect(self.browse_source_click)
        self.ui.addDest.clicked.connect(self.add_dest_to_table)
        self.ui.removeDest.clicked.connect(self.remove_destination)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)
        self.ui.actionSave_Preset.triggered.connect(self.save_preset_cb)
        self.ui.actionLoad_Preset.triggered.connect(self.load_preset_cb)
        self.ui.actionClear_Delete_Folder.triggered.connect(self.clear_deleted_folder)
        self.ui.unmoveBtn.clicked.connect(self.undo_cb)
        self.ui.checkDeletedBtn.clicked.connect(self.check_deleted_btn_cb)
        self.ui.actionFancy.triggered.connect(self.set_fancy_style)
        self.ui.actionLight.triggered.connect(self.set_light_style)
        self.ui.actionDark.triggered.connect(self.set_dark_style)
        self.ui.comboMode.currentTextChanged.connect(self.change_file_type)
        self.ui.actionOrange.triggered.connect(self.set_orange_style)
        self.ui.actionRemove_Duplicates.triggered.connect(
            self.remove_duplicate_pictures)
        self.ui.actionRemove_Duplicates_Recursively.triggered.connect(
            partial(self.remove_duplicate_pictures, recursive_delete=True))

        self.set_dark_style()

    def remove_duplicate_pictures(self, recursive_delete=False):
        root_path = self.model.rootPath()
        if root_path == ".":
            return  # if source destination wasnt chosen

        # check for missclick
        msg = "Are you sure you want to delete (trash bin) duplicate pictures from source folder?"
        reply = QtWidgets.QMessageBox.question(self, 'Message',
                                               msg, QtWidgets.QMessageBox.Yes,
                                               QtWidgets.QMessageBox.No)

        if reply != QtWidgets.QMessageBox.Yes:
            return

        # gather pictures from root path
        all_pictures = []
        if recursive_delete:  # recursive search
            for path in pathlib.Path(root_path).glob(r'**/*'):
                if path.suffix in self.pic_ext_list:
                    all_pictures.append(path)

        else:  # non recursive
            for path in pathlib.Path(root_path).glob(r'*'):
                if path.suffix in self.pic_ext_list:
                    all_pictures.append(path)

        # add phash of picture to dictionary, replace with shorter filename if same hash found
        result_pics = {}
        for path in all_pictures:
            with Image.open(path) as img:
                img_hash = str(imagehash.phash(img))
                if img_hash in result_pics:
                    dict_fname = result_pics[img_hash].stem
                    if len(path.stem) < len(dict_fname):
                        result_pics[img_hash] = path
                else:
                    result_pics[img_hash] = path

        result_pics = {value: key for key, value in result_pics.items()}
        # delete all pictures that are not in a result_pics dict
        for path in all_pictures:
            if path not in result_pics:
                try:
                    shutil.move(str(path), self.delete_folder)
                except shutil.Error:
                    send2trash(str(path))

        QtWidgets.QMessageBox.about(self, "Info", "Done")

    def add_text_to_buttons(self):
        self.ui.addDest.setText("Add")
        self.ui.removeDest.setText("Remove")
        self.ui.browseBtn.setText("Browse")
        self.ui.checkDeletedBtn.setText("Deleted")
        self.ui.unmoveBtn.setText("Undo")

    def remove_text_from_buttons(self):
        self.ui.addDest.setText("")
        self.ui.removeDest.setText("")
        self.ui.browseBtn.setText("")
        self.ui.checkDeletedBtn.setText("")
        self.ui.unmoveBtn.setText("")

    def set_orange_style(self):
        QtGui.QGuiApplication.setPalette(self.default_palette)
        with open("./styles/orange.css") as f:
            style_text = f.read()
            self.setStyleSheet(style_text)

        self.add_text_to_buttons()

    def set_fancy_style(self):
        QtGui.QGuiApplication.setPalette(self.default_palette)
        with open("./styles/fancy.css") as f:
            style_text = f.read()
            self.setStyleSheet(style_text)

        self.remove_text_from_buttons()

    def set_light_style(self):
        QtGui.QGuiApplication.setPalette(self.default_palette)
        self.setStyleSheet(" ")
        self.add_text_to_buttons()

    def set_dark_style(self):
        self.setStyleSheet(" ")
        self.add_text_to_buttons()

        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QtGui.QGuiApplication.setPalette(dark_palette)

    def change_file_type(self):
        """
        Change source directory display between pictures and files
        """
        mode = self.ui.comboMode.currentText()
        if mode == "Files":
            self.model.setNameFilters(["*.*"])

        elif mode == "Pictures":
            self.model.setNameFilters(
                ["*.jpg", "*.png", "*.webp", ".JPEG", ".PNG"])

    def check_deleted_btn_cb(self):
        """
        This is supposed to change model view to the deleted folder,
        and second press is supposed to bring you back to the previous 
        folder, but it doesnt work if you dont select an image in deleted folder.
        """
        ind = self.ui.treeView.currentIndex()
        file_path = self.model.filePath(ind)
        try:
            file_path = pathlib.Path(file_path).parents[0].resolve()
        except IndexError:
            return

        if file_path != pathlib.Path(self.delete_folder).resolve():
            self.model.setRootPath(self.delete_folder)
            self.ui.treeView.setRootIndex(self.model.index(self.delete_folder))
        else:
            self.model.setRootPath(self.current_file_folder)
            self.ui.treeView.setRootIndex(
                self.model.index(self.current_file_folder))

    def clear_deleted_folder(self):
        msg = "Are you sure you want to clear folder with deleted files?"
        reply = QtWidgets.QMessageBox.question(self, 'Message',
                                               msg, QtWidgets.QMessageBox.Yes,
                                               QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            p = pathlib.Path(self.delete_folder)
            for filename in p.glob("*"):
                send2trash(str(filename))
            QtWidgets.QMessageBox.about(
                self, "Delete folder cleared", "Delete folder cleared"
            )

    def undo_cb(self):
        """
        Store actions in a list, revert them 1 by 1
        """
        try:
            last_operation = self.undo_list[-1]
        except IndexError:
            return
        pic_path, dest_path = last_operation
        pic_path = pathlib.Path(pic_path)
        dest_path = pathlib.Path(dest_path, pic_path.name)
        pic_path, dest_path = dest_path, pic_path

        # print(pic_path.parents[0], dest_path)
        try:
            shutil.move(pic_path, str(dest_path))
        except shutil.Error:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "File already exists")
        except AttributeError:
            return
        except FileNotFoundError:
            return
        del self.undo_list[-1]

    def load_preset_cb(self):
        """
        Load user settings from file
        """
        dialog = QFileDialog()
        dialog.setFilter(dialog.filter() | QtCore.QDir.Hidden)
        dialog.setDefaultSuffix("json")
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setNameFilters(["JSON (*.json)"])
        if dialog.exec_() == QDialog.Accepted:
            preset_path = dialog.selectedFiles()[0]
            self.path_hotkey_dict = load_json(preset_path)
            self.path_hotkey_dict = {
                k: v for k, v in self.path_hotkey_dict.items() if v is not None
            }
            print("loaded dict: ", self.path_hotkey_dict)
            self.hotkey_path_dict = {
                value: key for key, value in self.path_hotkey_dict.items()
            }
            self.restore_table_from_dict()
        else:
            print("Cancelled")

    def save_preset_cb(self):
        """
        Save user settings to file
        """
        dialog = QFileDialog()
        dialog.setFilter(dialog.filter() | QtCore.QDir.Hidden)
        dialog.setDefaultSuffix("json")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(["JSON (*.json)"])
        if dialog.exec_() == QDialog.Accepted:
            preset_path = dialog.selectedFiles()[0]
            save_json(self.path_hotkey_dict, preset_path)
            QtWidgets.QMessageBox.information(
                self, "Saved", f"Saved hotkey preset: {preset_path}"
            )
        else:
            print("Cancelled")

    def show_about_dialog(self):
        text = (
            "<center>"
            "<h1>Waifu File Sort</h1>"
            "&#8291;"
            "</center>"
            f"<p>Version {get_version()}<br/>"
        )
        QtWidgets.QMessageBox.about(self, "About Waifu File Sort", text)

    def restore_table_from_dict(self):
        self.clear_table_widget()
        row_counter = 0

        for shortcut in self._shortcut_list:
            shortcut.setEnabled(False)

        self._shortcut_list = []

        for path, hotkey in self.path_hotkey_dict.items():
            path = pathlib.Path(path)
            self.add_dest_to_table(dest_path=path.name, hotkey=hotkey)
            self.ui.tableWidget.item(row_counter, 0).setToolTip(str(path))
            shortcut = QShortcut(QKeySequence(hotkey), self)
            shortcut.activated.connect(
                lambda mypath=path: self.move_cb(input_path=mypath))
            self._shortcut_list.append(shortcut)
            row_counter += 1

    def clear_table_widget(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

    def remove_destination(self):
        # get selected row or return
        # delete info from both dicts
        # reconstruct table widget from dict

        current_row = self.ui.tableWidget.currentRow()
        # print(f"{current_row=}")
        try:
            dest_path = self.ui.tableWidget.item(current_row, 0).toolTip()
        except AttributeError:
            return
        hotkey = self.ui.tableWidget.cellWidget(current_row, 2).text()
        # print("deleting hotkey: ", hotkey)
        self.delete_hotkey(hotkey)
        try:
            del self.path_hotkey_dict[dest_path]
        except KeyError:
            pass
        try:
            del self.hotkey_path_dict[hotkey]
        except KeyError:
            pass

        self.restore_table_from_dict()

    def delete_hotkey(self, name):
        for shortcut in self._shortcut_list:
            key_name = shortcut.key().toString()
            # print("k-name: ", key_name)
            if key_name == name.upper():
                # print("DELETED hotkey: ", name)
                shortcut.setEnabled(False)

    def add_dest_to_table(self, dest_path=None, hotkey=None):
        self.ui.tableWidget.setEditTriggers(
            self.ui.tableWidget.NoEditTriggers
        )  # disable editing and sorting
        self.ui.tableWidget.setSortingEnabled(False)

        row_counter = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(row_counter)
        ########################################################
        # add path label
        dest_path = QtWidgets.QTableWidgetItem(
            dest_path or "Press browse to specify destination directory"
        )
        self.ui.tableWidget.setItem(row_counter, 0, dest_path)
        ########################################################
        # add browse button
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(
            lambda *args, row_ind=row_counter: self.browse_dest_click(row_ind)
        )
        self.ui.tableWidget.setCellWidget(row_counter, 1, browse_btn)
        ########################################################
        # add hotkey line edit
        hotkey_line = QtWidgets.QLineEdit()
        hotkey_line.setPlaceholderText("Add hotkey")
        hotkey_line.setText(hotkey)
        hotkey_line.setMaxLength(1)

        hotkey_line.textChanged.connect(
            lambda *args, row_ind=row_counter: self.hotkey_line_text_changed_cb(
                hotkey_line, row_ind
            )
        )
        self.ui.tableWidget.setCellWidget(row_counter, 2, hotkey_line)
        ########################################################
        # add send button
        send_btn = QtWidgets.QPushButton("Send")
        send_btn.clicked.connect(
            lambda *args, row_ind=row_counter: self.move_cb(row=row_ind)
        )
        self.ui.tableWidget.setCellWidget(row_counter, 3, send_btn)

    def move_cb(self, row=None, input_path=None):
        ind = self.ui.treeView.currentIndex()
        pic_path = self.model.filePath(ind)
        dest_path = input_path or self.ui.tableWidget.item(row, 0).toolTip()
        dest_path = pathlib.Path(dest_path)

        if dest_path.is_dir() and str(dest_path) != ".":
            try:
                shutil.move(pic_path, str(dest_path))
            except shutil.Error:
                QtWidgets.QMessageBox.warning(
                    self, "Warning", "File already exists")
                return
            self.undo_list.append((pic_path, str(dest_path)))
        else:
            # notify user
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Destination path doesnt exist"
            )

    def hotkey_line_text_changed_cb(self, hotkey_line, row_ind):
        hotkey = hotkey_line.text()
        path = self.ui.tableWidget.item(row_ind, 0).toolTip()
        if not path and len(hotkey) > 0:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Destination path doesnt exist"
            )
            hotkey_line.clear()
            hotkey_line.clearFocus()
            return

        # check if hotkey line edit is empty and delete hotkey
        if len(hotkey) == 0 and path != "":
            hotkey_to_del = self.path_hotkey_dict[path]
            self.delete_hotkey(hotkey_to_del)

        self.path_hotkey_dict[path] = hotkey
        self.hotkey_path_dict = {
            value: key for key, value in self.path_hotkey_dict.items()
        }
        shortcut = QShortcut(QKeySequence(hotkey), self)
        # self._shortcut_list.append(shortcut.key().toString())
        self._shortcut_list.append(shortcut)
        dest_path = self.hotkey_path_dict[hotkey]
        shortcut.activated.connect(lambda: self.move_cb(input_path=dest_path))
        if len(hotkey) > 0:
            hotkey_line.clearFocus()

    def browse_dest_click(self, caller_row):
        # print(caller_row)
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None, "Select Folder")
        p = pathlib.Path(folder_path)

        if folder_path:
            self.ui.tableWidget.item(caller_row, 0).setText(p.name)
            self.ui.tableWidget.item(caller_row, 0).setToolTip(str(p))
            self.path_hotkey_dict[str(p)] = self.ui.tableWidget.cellWidget(
                caller_row, 2
            ).text()

    def browse_source_click(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None, "Select Folder")
        if folder_path:
            self.model.setRootPath(folder_path)
            self.ui.treeView.setRootIndex(self.model.index(folder_path))

    def update_image_label(self):
        ind = self.ui.treeView.currentIndex()
        file_path = self.model.filePath(ind)

        # keep track of current folder for check button return location
        path_to_current_folder = pathlib.Path(file_path).parents[0]
        if str(path_to_current_folder.resolve()) != str(
            pathlib.Path(self.delete_folder).resolve()
        ):
            self.current_file_folder = str(path_to_current_folder)

        pixmap = QtGui.QPixmap(file_path)
        pixmap = pixmap.scaled(
            self.ui.imageLabel.width(),
            self.ui.imageLabel.height(),
            QtCore.Qt.KeepAspectRatio,
        )
        self.ui.imageLabel.setPixmap(pixmap)
        self.ui.imageLabel.setAlignment(QtCore.Qt.AlignCenter)


def save_json(data, result_name_with_ext):
    with open(result_name_with_ext, "w") as fp:
        json.dump(data, fp)


def load_json(input_name_and_ext):
    with open(input_name_and_ext, "r") as fp:
        data = json.load(fp)
    return data


def find_data_file(folder, filename=None):
    if getattr(sys, "frozen", False):
        # The application is frozen
        datadir = os.path.dirname(sys.executable)
    else:
        # The application is not frozen
        datadir = os.path.dirname(__file__)
    # The following line has been changed to match where you store your data files:
    if filename:
        return os.path.join(datadir, folder, filename)
    else:
        return os.path.join(datadir, folder)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
