import sys
import numpy as np
import csv
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel, QRadioButton, QHBoxLayout, QScrollArea, QTextEdit
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QRect, QPoint

class ImageDisplayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.click_history = []

    def initUI(self):
        self.loadButton = QPushButton('CSV', self)
        self.loadButton.clicked.connect(self.openFileNameDialog)

        self.iButton = QRadioButton("Phase")
        self.jButton = QRadioButton("Magnitude")
        self.iButton.setChecked(True)

        self.imageLabel = QLabel(self)
        self.imageLabel.mousePressEvent = self.mousePressEvent
        self.imageLabel.mouseMoveEvent = self.mouseMoveEvent 
        self.imageLabel.mouseReleaseEvent = self.mouseReleaseEvent

        self.selectionLabel = QLabel(self)
        self.selectionLabel.mousePressEvent = self.selectionMousePressEvent

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.imageLabel)

        self.selectionArea = QScrollArea()
        self.selectionArea.setWidget(self.selectionLabel)

        self.dataLabel = QTextEdit(self)
        self.dataLabel.setReadOnly(True)
        self.dataArea = QScrollArea()
        self.dataArea.setWidget(self.dataLabel)

        self.coordLabel = QLabel(self)
        self.coordLabel.setText("Coordinates: (x, y), Value: value")

        self.label = QLabel('choose file', self)
        self.vbox = QVBoxLayout(self)
        self.hbox = QHBoxLayout()
        self.imageLayout = QHBoxLayout()

        self.hbox.addWidget(self.iButton)
        self.hbox.addWidget(self.jButton)
        self.vbox.addWidget(self.loadButton)
        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.label)
        self.vbox.addWidget(self.scrollArea)
        self.vbox.addWidget(self.coordLabel) 
        self.imageLayout.addWidget(self.selectionArea)
        self.imageLayout.addWidget(self.dataArea)
        self.vbox.addLayout(self.imageLayout)

        self.setLayout(self.vbox)
        self.setWindowTitle('obrasek')
        self.setGeometry(300, 300, 1500, 600)

        self.originQPoint = None
        self.currentQRect = QRect()
        self.pixmap = None
        self.selected_data_origin = None
        self.norm_image_data = None
        self.file_name = None

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if fileName:
            self.file_name = fileName
            self.displayImage(fileName)

    def displayImage(self, fileName):
        with open(fileName, 'r') as file:
            raw_data = file.read().strip().replace('(', '').replace(')', '').replace('"', '').split('\n')

        data = []
        for line in raw_data:
            row = line.split(',')
            row_pairs = [(float(row[i]), float(row[i+1])) for i in range(0, len(row), 2)]
            data.append(row_pairs)

        rows = len(data)
        cols = len(data[0])

        if self.iButton.isChecked():
            image_data = np.array([[item[0] for item in row] for row in data])
        else:
            image_data = np.array([[item[1] for item in row] for row in data])

        norm_image_data = (image_data - np.min(image_data)) / (np.max(image_data) - np.min(image_data)) * 255
        norm_image_data = norm_image_data.astype(np.uint8)

        self.image_data = image_data  # Store original data for later use
        self.norm_image_data = norm_image_data  # Store normalized data for later use

        height, width = norm_image_data.shape
        qimage = QImage(norm_image_data.data, width, height, width, QImage.Format_Grayscale8)
        scaled_qimage = qimage.scaled(width * 10, height * 10, Qt.IgnoreAspectRatio)

        self.pixmap = QPixmap.fromImage(scaled_qimage)
        self.imageLabel.setPixmap(self.pixmap)
        self.imageLabel.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.originQPoint = event.pos()
            self.currentQRect = QRect(self.originQPoint, self.originQPoint)

    def mouseMoveEvent(self, event):
        self.updateCoordinates(event)
        if event.buttons() & Qt.LeftButton and self.originQPoint:
            self.currentQRect = QRect(self.originQPoint, event.pos())
            self.updateSelection()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.originQPoint:
            self.currentQRect = QRect(self.originQPoint, event.pos())
            self.updateSelection()
            self.showSelectedArea()
            self.originQPoint = None
            self.currentQRect = QRect()

    def updateCoordinates(self, event):  # New method to show coordinates on mouse move
        x = event.pos().x() // 10
        y = event.pos().y() // 10
        if x >= 0 and y >= 0 and x < self.norm_image_data.shape[1] and y < self.norm_image_data.shape[0]:
            value = self.image_data[y, x]
            self.coordLabel.setText(f"Coordinates: ({x}, {y}), Value: {value}")

    def updateSelection(self):
        if self.pixmap:
            original_pixmap = self.pixmap.copy()
            painter = QPainter(original_pixmap)
            pen = QPen(Qt.red, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.currentQRect)
            painter.end()
            self.imageLabel.setPixmap(original_pixmap)

    def showSelectedArea(self):
        if self.currentQRect.isNull():
            return

        x1 = min(self.currentQRect.left(), self.currentQRect.right()) // 10
        y1 = min(self.currentQRect.top(), self.currentQRect.bottom()) // 10
        x2 = max(self.currentQRect.left(), self.currentQRect.right()) // 10
        y2 = max(self.currentQRect.top(), self.currentQRect.bottom()) // 10

        if x1 == x2 or y1 == y2:
            return

        self.selected_data_origin = (x1, y1)

        selected_data = self.norm_image_data[y1:y2+1, x1:x2+1]

        # Normalize selected data to range 0-1
        if selected_data.size > 0:
            min_val = np.min(selected_data)
            max_val = np.max(selected_data)
            if max_val - min_val != 0:
                selected_data = (selected_data - min_val) / (max_val - min_val)
            else:
                selected_data = selected_data - min_val

            # Scale to 0-255 for displaying
            selected_data = (selected_data * 255).astype(np.uint8)

            height, width = selected_data.shape
            selected_data_bytes = selected_data.tobytes()
            qimage = QImage(selected_data_bytes, width, height, width, QImage.Format_Grayscale8)
            scaled_qimage = qimage.scaled(width * 10, height * 10, Qt.IgnoreAspectRatio)

            pixmap = QPixmap.fromImage(scaled_qimage)
            self.selectionLabel.setPixmap(pixmap)
            self.selectionLabel.adjustSize()

    def selectionMousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.selected_data_origin is not None:
            x = event.pos().x() // 10
            y = event.pos().y() // 10
            orig_x = self.selected_data_origin[0] + x
            orig_y = self.selected_data_origin[1] + y
            pixel_value = self.image_data[orig_y, orig_x]
            self.dataLabel.append(f'X: {orig_x}, Y: {orig_y}, Value: {pixel_value}')
            self.click_history.append((orig_x, orig_y, pixel_value))

    def closeEvent(self, event):
        if self.file_name and self.click_history:
            base_name = self.file_name.split('/')[-1].split('.')[0]
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'analysis_{base_name}_{current_time}.csv'
            with open(output_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['X', 'Y', 'Value'])
                writer.writerows(self.click_history)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageDisplayApp()
    ex.show()
    sys.exit(app.exec_())
