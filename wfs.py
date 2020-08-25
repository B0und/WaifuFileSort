import convert_ui_and_qrc_files

from PyQt5.uic import pyuic
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QShortcut,
    QFileSystemModel,
    QAbstractItemView,
    QFileDialog,
    QDialog,
)
from PyQt5.QtGui import (
    QColor,
    QPalette,
    QStandardItemModel,
    QStandardItem,
    QKeySequence,
)
from PyQt5.QtCore import Qt, QDir, QItemSelectionModel
from main_ui import Ui_MainWindow
import sys
import pathlib
from pprint import pprint
import shutil
from send2trash import send2trash
from functools import partial
import json
import os


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Weeb File Sort")
        app_icon = QtGui.QIcon()
        app_icon.addFile("./icons/waifu_sort.png", QtCore.QSize(256, 256))
        self.setWindowIcon(app_icon)

        with open("orange.css") as f:
            style_text = f.read()
            self.setStyleSheet(style_text)

        self.path_hotkey_dict = {}
        self.hotkey_path_dict = {}
        self._shortcut_list = []
        self.undo_list = []
        self.delete_folder = str(pathlib.Path(find_data_file("delete")))
        self.current_file_folder = ""

        self.model = QFileSystemModel()
        # self.model.setFilter(QDir.Files)
        self.model.setNameFilters(["*.jpg", "*.png", "*.webp", ".JPEG", ".PNG"])
        self.model.setNameFilterDisables(False)
        self.ui.treeView.setModel(self.model)
        # self.ui.treeView.setRootIndex(self.model.index(p))
        self.ui.treeView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.tableWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )

        self.ui.treeView.selectionModel().selectionChanged.connect(
            self.updateImageLabel
        )

        self.ui.browseBtn.clicked.connect(self.browse_source_click)
        self.ui.addDest.clicked.connect(self.add_dest_to_table)

        self.delShortcut = QShortcut(QKeySequence("Delete"), self)
        self.delShortcut.activated.connect(
            partial(self.move_cb, None, self.delete_folder)
        )

        self.undoShortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undoShortcut.activated.connect(self.undo_cb)

        self.ui.removeDest.clicked.connect(self.remove_dest)
        self.ui.actionAbout.triggered.connect(self.showAboutDialog)
        self.ui.actionSave_Preset.triggered.connect(self.save_preset_cb)
        self.ui.actionLoad_Preset.triggered.connect(self.load_preset_cb)
        self.ui.actionClear_Delete_Folder.triggered.connect(self.clear_folder)
        self.ui.unmoveBtn.clicked.connect(self.undo_cb)
        self.ui.checkDeletedBtn.clicked.connect(self.checkDeletedBtn_cb)
        self.ui.actionWeeb.triggered.connect(self.setWeebStyle)
        self.ui.actionDefault.triggered.connect(self.setDefaultStyle)
        self.ui.comboMode.currentTextChanged.connect(self.changeFileType)
        self.ui.actionOrange.triggered.connect(self.setOrangeTheme)

    def setOrangeTheme(self):
        with open("orange.css") as f:
            style_text = f.read()
            self.setStyleSheet(style_text)

        self.ui.addDest.setText("Add")
        self.ui.removeDest.setText("Remove")
        self.ui.browseBtn.setText("Browse")
        self.ui.checkDeletedBtn.setText("Deleted")
        self.ui.unmoveBtn.setText("Undo")

    def setWeebStyle(self):
        with open("style_anime.css") as f:
            style_text = f.read()
            self.setStyleSheet(style_text)

        self.ui.addDest.setText("")
        self.ui.removeDest.setText("")
        self.ui.browseBtn.setText("")
        self.ui.checkDeletedBtn.setText("")
        self.ui.unmoveBtn.setText("")

    def setDefaultStyle(self):
        self.setStyleSheet(" ")
        self.ui.addDest.setText("Add")
        self.ui.removeDest.setText("Remove")
        self.ui.browseBtn.setText("Browse")
        self.ui.checkDeletedBtn.setText("Deleted")
        self.ui.unmoveBtn.setText("Undo")

    def changeFileType(self):
        mode = self.ui.comboMode.currentText()
        if mode == "Files":
            self.model.setNameFilters(["*.*"])

        elif mode == "Pictures":
            self.model.setNameFilters(["*.jpg", "*.png", "*.webp", ".JPEG", ".PNG"])

    def checkDeletedBtn_cb(self):
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
            self.ui.treeView.setRootIndex(self.model.index(self.current_file_folder))

    def clear_folder(self):
        p = pathlib.Path(self.delete_folder)
        for filename in p.glob("*"):
            send2trash(str(filename))
        QtWidgets.QMessageBox.about(
            self, "Delete folder cleared", "Delete folder cleared"
        )

    def undo_cb(self):
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
            QtWidgets.QMessageBox.warning(self, "Warning", "File already exists")
        except AttributeError:
            return
        except FileNotFoundError:
            return
        del self.undo_list[-1]

    def load_preset_cb(self):
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

    def showAboutDialog(self):
        text = (
            "<center>"
            "<h1>Waifu File Sort</h1>"
            "&#8291;"
            "</center>"
            "<p>Version 1.5.0<br/>"
        )
        QtWidgets.QMessageBox.about(self, "About Waifu File Sort", text)

    def restore_table_from_dict(self):
        self.clearTableWidget()
        row_counter = 0

        for shortcut in self._shortcut_list:
            shortcut.setEnabled(False)

        self._shortcut_list = []

        for path, hotkey in self.path_hotkey_dict.items():
            path = pathlib.Path(path)
            self.add_dest_to_table(dest_path=path.name, hotkey=hotkey)
            self.ui.tableWidget.item(row_counter, 0).setToolTip(str(path))
            shortcut = QShortcut(QKeySequence(hotkey), self)
            shortcut.activated.connect(lambda: self.move_cb(input_path=path))
            self._shortcut_list.append(shortcut)
            row_counter += 1

    def clearTableWidget(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

    def remove_dest(self):
        # get selected row or return
        # delete info from both dicts
        # reconstruct table widget from dict
        # items = self.ui.tableWidget.selectedItems()

        current_row = self.ui.tableWidget.currentRow()
        print(f"{current_row=}")
        try:
            dest_path = self.ui.tableWidget.item(current_row, 0).toolTip()
        except AttributeError:
            return
        hotkey = self.ui.tableWidget.cellWidget(current_row, 2).text()
        print("deleting hotkey: ", hotkey)
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
            print("k-name: ", key_name)
            if key_name == name.upper():
                print("DELETED hotkey: ", name)
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
        # pic_path = pathlib.Path(pic_path)
        dest_path = input_path or self.ui.tableWidget.item(row, 0).toolTip()
        dest_path = pathlib.Path(dest_path)

        if dest_path.is_dir() and str(dest_path) != ".":
            try:
                shutil.move(pic_path, str(dest_path))
            except shutil.Error:
                QtWidgets.QMessageBox.warning(self, "Warning", "File already exists")
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
        print(caller_row)
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

    def updateImageLabel(self):
        ind = self.ui.treeView.currentIndex()
        file_path = self.model.filePath(ind)

        # keep track of current folder for check button return location
        path_to_current_folder = pathlib.Path(file_path).parents[0]
        # print(f"{path_to_current_folder=}")
        print(path_to_current_folder.resolve())
        print(pathlib.Path(self.delete_folder).resolve())
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


def save_json(data, resultNameAndExt):
    with open(resultNameAndExt, "w") as fp:
        json.dump(data, fp)


def load_json(inputNameAndExt):
    with open(inputNameAndExt, "r") as fp:
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
    # Now use a palette to switch to dark colors:
    # palette = QPalette()
    # palette.setColor(QPalette.Window, QColor(53, 53, 53))
    # palette.setColor(QPalette.WindowText, Qt.white)
    # palette.setColor(QPalette.Base, QColor(25, 25, 25))
    # palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    # palette.setColor(QPalette.ToolTipBase, Qt.white)
    # palette.setColor(QPalette.ToolTipText, Qt.white)
    # palette.setColor(QPalette.Text, Qt.white)
    # palette.setColor(QPalette.Button, QColor(53, 53, 53))
    # palette.setColor(QPalette.ButtonText, Qt.white)
    # palette.setColor(QPalette.BrightText, Qt.red)
    # palette.setColor(QPalette.Link, QColor(42, 130, 218))
    # palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    # palette.setColor(QPalette.HighlightedText, Qt.black)
    # app.setPalette(palette)

    w = MainWindow()
    # w.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    w.show()
    sys.exit(app.exec_())
