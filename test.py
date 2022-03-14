import sys
from PyQt5 import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vedo import Plotter, Cone, printc, Point
from vedo.cli import exe_info


class MainWindow(Qt.QMainWindow):

    def __init__(self, size, parent=None):
        Qt.QMainWindow.__init__(self, parent)
        self.frame = Qt.QFrame()
        self.layout = Qt.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)

        # Create renderer and add the vedo objects and callbacks
        self.plt = Plotter(qtWidget=self.vtkWidget, pos=(0,0))
        self.id1 = self.plt.addCallback("mouse click", self.onMouseClick)
        self.plt += Cone().rotateX(20)
        self.plt.show()                  # <--- show the vedo rendering

        # Set-up the rest of the Qt window
        self.layout.addWidget(self.vtkWidget)
        self.frame.setLayout(self.layout)
        self.setCentralWidget(self.frame)
        self.show()                     # <--- show the Qt Window

    def onMouseClick(self, event):
        printc("Left button pressed on 2D", event.picked2d, c='y')
        if not event.actor:
            return
        printc("Left button pressed on 3D", event.picked3d, c='g')
        pt = Point(event.picked3d).c('pink').ps(12)
        self.plt.add(pt)


if __name__ == "__main__":

    exe_info([]) # will dump some info about the system

    app = Qt.QApplication(sys.argv)
    screen = app.primaryScreen()
    size = screen.size()
    print('Screen: %s' % screen.name())
    print('Size: %d x %d' % (size.width(), size.height()))

    window = MainWindow(size)
    app.exec_()