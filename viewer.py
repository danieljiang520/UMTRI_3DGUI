# -----------------------------------------------------------
# Stripped down Qt-vtk-based viewer for ply, obj etc.
# 2022-01-24
# Building up from DanielJ example code
# 2022-02-11
# Implementing Picking
# 2022-03-01
# Fixing Picking + Implementing tree view for actors
# -----------------------------------------------------------

# %% standard lib imports
# from msilib.schema import Dialog
from shutil import ReadError
import sys, copy, time
from pathlib import Path
import os
from cutter import *
from settings import *
# %% project-specific imports
## Qt + vtk widget
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QApplication,
    QApplication,
    QFileSystemModel,
    QTabBar,
    QDialog,
    QAbstractItemView
)
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import QtCore
from PyQt5.Qt import QStandardItemModel, QStandardItem

## vedo
from vedo import (
    Plotter,
    printc,
    Mesh,
    base,
    Point
)
from vedo.cli import exe_info
# from vedo.applications import FreeHandCutPlotter

## iPython
# These for embeded pythion console
os.environ['QT_API'] = 'pyqt5'
# iPython won't work if this is not correctly installed. And the error message will be misleading
# from IPython.qt.console.rich_ipython_widget import RichIPythonWidget # deprecated
from qtconsole.rich_ipython_widget import RichIPythonWidget
# from IPython.qt.inprocess import QtInProcessKernelManager

## qtconsole
# these are updated based on error messages
from qtconsole.inprocess import QtInProcessKernelManager
# from qtconsole import rich_ipython_widget

#-------------------------------------------------------------------------------------------------
# %% Functions
# this function to find "app" in the global namespace -- lame but for now...
def get_app_qt5(*args, **kwargs):
    """Create a new qt5 app or return an existing one."""
    app = QApplication.instance()
    if app is None:
        if not args:
            args = ([''],)
        app = QApplication(*args, **kwargs)
    return app

# toy function to push to ipy
def print_process_id():
    print('Process ID is:', os.getpid())

# this class for the console
class QIPythonWidget(RichIPythonWidget):
    """ Convenience class for a live IPython console widget.
    We can replace the standard banner using the customBanner argument """
    def __init__(self,customBanner=None,*args,**kwargs):
        super(QIPythonWidget, self).__init__(*args,**kwargs)
        if customBanner!=None: self.banner=customBanner
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel_manager.kernel.gui = 'qt'
        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            get_app_qt5().exit()

        self.exit_requested.connect(stop)

    def pushVariables(self, variableDict):
        """ Given a dictionary containing name / value pairs,
        push those variables to the IPython console widget """
        self.kernel_manager.kernel.shell.push(variableDict)

    def clearTerminal(self):
        """ Clears the terminal """
        self._control.clear()

    def printText(self,text):
        """ Prints some plain text to the console """
        self._append_plain_text(text)

    def executeCommand(self,command):
        """ Execute a command in the frame of the console widget """
        self._execute(command,False)

# Main application window
class MainWindow(QMainWindow):
    # inputPath = "" # absolute path to the input ply scan
    outputPath = "" # absolute path to the output folder
    resultPath = "" # path to the most recent finished project ply file
    currentFolder = "" # path to current folder
    vertexSelections = []
    actorSelection = None
    objs = []
    dirModel = QFileSystemModel()

    def __init__(self,size):
        super(MainWindow, self).__init__()

        self.settings = QtCore.QSettings('UMTRI','3DViewer')
        print(self.settings.fileName())

        # load the components defined in th xml file
        loadUi("viewer_gui.ui", self)
        self.screenSize = size

        """ Connections for all elements in Mainwindow """
        self.action_importMesh.triggered.connect(self.importMesh)
        self.action_clearSelection.triggered.connect(self.clearScreen)
        self.action_selectVertex.toggled.connect(self.actionSelectVertex_state_changed)
        self.action_selectActor.toggled.connect(self.actionSelectActor_state_changed)
        self.action_cutter.triggered.connect(self.actionCutter_state_changed)
        self.action_openExplorerFolder.triggered.connect(self.setExplorerFolder)
        self.action_preferences.triggered.connect(self.openSettings)
        self.pushButton_settings.clicked.connect(self.openSettings)
        self.toolButton_explorer.clicked.connect(self.setExplorerFolder)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)
        self.treeView_explorer.doubleClicked.connect(self.treeView_explorer_doubleClicked)

        """ Set up file explorer """
        parser = QtCore.QCommandLineParser()
        parser.setApplicationDescription("Qt Dir View Example")
        parser.addHelpOption()
        parser.addVersionOption()
        dontUseCustomDirectoryIconsOption = QtCore.QCommandLineOption("c", "Set QFileSystemModel::DontUseCustomDirectoryIcons")
        parser.addOption(dontUseCustomDirectoryIconsOption)
        dontWatchOption = QtCore.QCommandLineOption("w", "Set QFileSystemModel::DontWatch")
        parser.addOption(dontWatchOption)
        parser.process(app)

        """ Set up tree view for file explorer """
        self.dirModel.setRootPath(QtCore.QDir.currentPath())
        self.treeView_explorer.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeView_explorer.setModel(self.dirModel)
        self.treeView_explorer.setRootIndex(self.dirModel.index(QtCore.QDir.currentPath()))
        # availableSize = QtCore.QSize(self.tree.screen().availableGeometry().size())
        # self.tree.resize(availableSize / 2)
        # self.tree.setColumnWidth(0, int(self.tree.width() / 3))
        self.treeView_explorer.hideColumn(1)
        self.treeView_explorer.hideColumn(2)
        self.treeView_explorer.hideColumn(3)

        """ Set up tree view for projects """
        self.treeModel = QStandardItemModel()
        self.rootNode = self.treeModel.invisibleRootItem()
        self.treeView_projects.setModel(self.treeModel)

        """ Set up VTK widget """
        self.vtkWidget = QVTKRenderWindowInteractor()
        self.tabWidget.addTab(self.vtkWidget, "Main Viewer")
        self.tabWidget.tabBar().tabButton(0, QTabBar.LeftSide).resize(0, 0) # Windows should be QTabBar.RightSide

        """ ipy console """
        self.ipyConsole = QIPythonWidget(customBanner="Welcome to the embedded ipython console\n")
        self.ipyConsole.console_height = 5
        self.splitter_viewer.addWidget(self.ipyConsole)
        self.ipyConsole.pushVariables({"foo":43, "print_process_id":print_process_id, "ipy":self.ipyConsole, "self":self})
        self.ipyConsole.printText("The variable 'foo' and the method 'print_process_id()' are available.\
            Use the 'whos' command for information.\n\nTo push variables run this before starting the UI:\
                \n ipyConsole.pushVariables({\"foo\":43,\"print_process_id\":print_process_id})")

        """ Create renderer and add the vedo objects and callbacks """
        self.plt = Plotter(qtWidget=self.vtkWidget,bg='DarkSlateBlue',bg2='MidnightBlue',screensize=(1792,1120))
        self.plt.addCallback("RightButtonPress", self.onRightClick)
        # self.plt.addCallback("key press", self.onKeyPress)
        # self.plt.addCallback('MouseMove', self.onMouseMove)
        self.plt.show(zoom=True)                  # <--- show the vedo rendering

    def onClose(self):
        #Disable the interactor before closing to prevent it
        #from trying to act on already deleted items
        printc("..calling onClose")
        self.vtkWidget.close()

    def onRightClick(self, event):
        if(self.action_selectActor.isChecked()):
            self.selectActor(event)
        elif(self.action_selectVertex.isChecked()):
            self.selectVertex(event)

    def selectActor(self,event):
        if(not event.actor):
            return
        # i = event.at
        printc("Left button pressed on 3D", event.picked3d, c='g')
        # adding a silhouette might cause some lags
        # self.plt += event.actor.silhouette().lineWidth(2).c('red')
        #an alternative solution
        self.actorSelection = event.actor.clone()
        self.actorSelection.c('red')
        # self.plt.at(i).add(self.actorSelection)
        self.plt.add(self.actorSelection)

    def selectVertex(self,event):
        if(not event.isPoints):
            return
        # i = event.at
        printc("Left button pressed on 3D", event.picked3d, c='g')
        pt = Point(event.picked3d).c('pink').ps(12)
        self.vertexSelections.append(pt)
        # self.plt.at(i).add(pt)
        self.plt.add(pt)

    def clearScreen(self):
        if(len(self.vertexSelections)>0):
            self.plt.clear(self.vertexSelections)
        self.vertexSelections.clear()
        self.plt.show()
        print("Cleared screen!")

    def getDirPath(self):
        """ getDirPath opens a file dialog and only allows the user to select folders """
        return QFileDialog.getExistingDirectory(self, "Open Directory",
                                                os.getcwd(),
                                                QFileDialog.ShowDirsOnly
                                                | QFileDialog.DontResolveSymlinks)

    def getFilePath(self):
        """ open a file dialog and select a file """
        return QFileDialog.getOpenFileName(self, 'Open File',
         os.getcwd(), "Ply Files (*.ply);;OBJ Files (*.obj);;STL Files (*.stl)")[0]

    def setExplorerFolder(self):
        self.currentFolder = self.getDirPath()
        self.treeView_explorer.setRootIndex(self.dirModel.index(self.currentFolder))

    def importMesh(self,inputPath=""):
        if (not inputPath):
            inputPath = self.getFilePath()
        if (not inputPath.lower().endswith(('.ply', '.obj', '.stl'))):
            return
        inputBaseName = os.path.basename(inputPath)
        print("displaying ",inputBaseName)
        m = Mesh(inputPath)
        m.name = inputBaseName
        self.objs.append(m)
        self.plt.add(m)
        self.plt.show(zoom=True)                 # <--- show the vedo rendering
        objectTreeItem = QStandardItem(inputBaseName)
        fileDirTreeItem = QStandardItem("File: "+inputPath)
        numVerticesTreeItem = QStandardItem("Vertices: "+str(base.BaseActor.N(m)))
        numFacesTreeItem = QStandardItem("Faces: "+str(base.BaseActor.NCells(m)))
        objectTreeItem.appendRows([fileDirTreeItem,numVerticesTreeItem,numFacesTreeItem])
        self.rootNode.appendRow(objectTreeItem)

    def actionSelectActor_state_changed(self):
        if(self.action_selectActor.isChecked()):
            self.action_selectVertex.setChecked(False)

    def actionSelectVertex_state_changed(self):
        if(self.action_selectVertex.isChecked()):
            self.action_selectActor.setChecked(False)

    def actionCutter_state_changed(self):
        if(len(self.objs)<1): return
        self.cutterWidget = QVTKRenderWindowInteractor()
        self.tabWidget.addTab(self.cutterWidget, "Cutter Viewer")
        FreeHandCutPlotter(mesh=self.objs[0], qtWidget=self.cutterWidget).start()
        self.tabWidget.setCurrentWidget(self.cutterWidget)

    def closeTab(self,index):
        self.tabWidget.removeTab(index)

    def treeView_explorer_doubleClicked(self,index):
        indexes = self.treeView_explorer.selectionModel().selectedIndexes()
        # print(indexes)
        item =index.model().filePath(index)
        self.importMesh(item)

    def openSettings(self):
        dialog = QDialog()
        dialog.ui = Settings()
        dialog.ui.setupUi(dialog)
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.exec_()


#-------------------------------------------------------------------------------------------------
# %% Main
if __name__ == "__main__":

    exe_info([]) # will dump some info about the system

    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    size = screen.size()
    print('Screen: %s' % screen.name())
    print('Size: %d x %d' % (size.width(), size.height()))

    mainwindow = MainWindow(size)
    mainwindow.show()
    sys.exit(app.exec())