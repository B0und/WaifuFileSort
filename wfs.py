from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QShortcut, QFileSystemModel, QAbstractItemView, QFileDialog
from PyQt5.QtGui import (
    QColor,
    QPalette,
    QStandardItemModel,
    QStandardItem,
    QKeySequence,
)
from PyQt5.QtCore import Qt, QDir
from main_ui import Ui_MainWindow
import sys
import pathlib
from pprint import pprint
import shutil
from send2trash import send2trash


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Weeb File Sort")
        # app_icon = QtGui.QIcon()
        # app_icon.addFile("ui_compile/icons/icon.png", QtCore.QSize(256, 256))
        # self.setWindowIcon(app_icon)

        self.path_hotkey_dict = {}
        self.hotkey_path_dict = {}

        self.model = QFileSystemModel()
        self.model.setFilter(QDir.Files)
        self.model.setNameFilters(["*.jpg", "*.png", "*.webp", ".JPEG", ".PNG"])
        self.model.setNameFilterDisables(False)
        self.ui.listView.setModel(self.model)
        # self.ui.listView.setRootIndex(self.model.index(p))
        self.ui.listView.setSelectionMode(QAbstractItemView.SingleSelection)

        self.ui.listView.selectionModel().selectionChanged.connect(
            self.updateImageLabel
        )

        self.ui.browseBtn.clicked.connect(self.browse_source_click)
        self.ui.addDest.clicked.connect(self.add_dest_to_table)

        self.delShortcut = QShortcut(QKeySequence("Delete"), self)
        self.delShortcut.activated.connect(self.delete_cb)
        self.ui.removeDest.clicked.connect(self.remove_dest)

    def clearTableWidget(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

    def remove_dest(self):
        # get selected row or return
        # delete info from both dicts
        # reconstruct table widget from dict
        current_row = self.ui.tableWidget.currentRow()
        print(current_row)
        if current_row == -1:
            return

        dest_path = self.ui.tableWidget.item(current_row, 0).toolTip()
        hotkey = self.ui.tableWidget.cellWidget(current_row, 2).text()
        del self.path_hotkey_dict[dest_path]
        del self.hotkey_path_dict[hotkey]

    def delete_cb(self):
        ind = self.ui.listView.currentIndex()
        file_path = self.model.filePath(ind)
        p = pathlib.Path(file_path)
        send2trash(str(p))

    def add_dest_to_table(self):
        self.ui.tableWidget.setEditTriggers(
            self.ui.tableWidget.NoEditTriggers
        )  # disable editing and sorting
        self.ui.tableWidget.setSortingEnabled(False)

        row_counter = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(row_counter)

        ########################################################
        # add path label
        dest_path = QtWidgets.QTableWidgetItem(
            "Press browse to specify destination directory"
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
            lambda *args, row_ind=row_counter: self.send_cb(row_ind)
        )
        self.ui.tableWidget.setCellWidget(row_counter, 3, send_btn)

    def send_cb(self, row):
        ind = self.ui.listView.currentIndex()
        pic_path = self.model.filePath(ind)
        # pic_path = pathlib.Path(pic_path)
        dest_path = self.ui.tableWidget.item(row, 0).toolTip()
        dest_path = pathlib.Path(dest_path)

        if dest_path.is_dir() and str(dest_path) != ".":
            shutil.move(pic_path, str(dest_path))
        else:
            # notify user
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Destination path doesnt exist"
            )

    def send_from_hotkey(self, dest_path):
        ind = self.ui.listView.currentIndex()
        pic_path = self.model.filePath(ind)
        dest_path = pathlib.Path(dest_path)
        # print(dest_path)
        if dest_path.is_dir() and str(dest_path) != ".":
            shutil.move(pic_path, str(dest_path))
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

        self.path_hotkey_dict[path] = hotkey
        self.hotkey_path_dict = {
            value: key for key, value in self.path_hotkey_dict.items()
        }
        shortcut = QShortcut(QKeySequence(hotkey), self)
        dest_path = self.hotkey_path_dict[hotkey]
        shortcut.activated.connect(lambda: self.send_from_hotkey(dest_path))
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
            self.ui.listView.setRootIndex(self.model.index(folder_path))

    def updateImageLabel(self):
        ind = self.ui.listView.currentIndex()
        file_path = self.model.filePath(ind)
        pixmap = QtGui.QPixmap(file_path)
        pixmap = pixmap.scaled(
            self.ui.imageLabel.width(),
            self.ui.imageLabel.height(),
            QtCore.Qt.KeepAspectRatio,
        )
        self.ui.imageLabel.setPixmap(pixmap)
        self.ui.imageLabel.setAlignment(QtCore.Qt.AlignCenter)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    app.setStyle("Fusion")
    # Now use a palette to switch to dark colors:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
