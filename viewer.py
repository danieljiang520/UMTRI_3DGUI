# Stripped down Qt-vtk-based viewer for ply, obj etc.
# 2022-01-24
# Building up from DanielJ example code
# 2022-02-11
# Implementing Picking
# 2022-03-01
# Fixing Picking + Implementing tree view for actors

# %% standard lib imports
from shutil import ReadError
import sys, copy, time
from pathlib import Path
import os
# %%

# %% project-specific imports
## Qt + vtk widget
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (
    QMainWindow, 
    QFileDialog,
    QApplication,
    QApplication,
    QFileSystemModel
)
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import Qt, QtCore

## vedo
from vedo import Plotter, printc,Mesh,base,pointcloud

## iPython
# These for embeded pythion console
os.environ['QT_API'] = 'pyqt5'
# iPython won't work if this is not correctly installed. And the error message will be misleading
from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
# from IPython.qt.inprocess import QtInProcessKernelManager

## qtconsole
# these are updated based on error messages
from qtconsole.inprocess import QtInProcessKernelManager
# from qtconsole import rich_ipython_widget
# %%

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
    inputPath = "" # absolute path to the input ply scan
    outputPath = "" # absolute path to the output folder
    resultPath = "" # path to the most recent finished project ply file
    vertexSelections = [None]
    actorSelection = None

    def __init__(self,size):
        super(MainWindow, self).__init__()

        # load the components defined in th xml file
        loadUi("viewer_gui.ui", self)
        self.screenSize = size

        # Connections for all elements in Mainwindow
        self.actionImportMesh.triggered.connect(self.getFilePath)
        self.actionclearSelection.triggered.connect(self.clearScreen)
        self.action_selectVertex.toggled.connect(self.actionSelectVertex_state_changed)
        self.action_selectActor.toggled.connect(self.actionSelectActor_state_changed)

        # Set up file explorer
        parser = QtCore.QCommandLineParser()
        parser.setApplicationDescription("Qt Dir View Example")
        parser.addHelpOption()
        parser.addVersionOption()
        dontUseCustomDirectoryIconsOption = QtCore.QCommandLineOption("c", "Set QFileSystemModel::DontUseCustomDirectoryIcons")
        parser.addOption(dontUseCustomDirectoryIconsOption)
        dontWatchOption = QtCore.QCommandLineOption("w", "Set QFileSystemModel::DontWatch")
        parser.addOption(dontWatchOption)
        parser.process(app)
        model = QFileSystemModel()
        model.setRootPath("")
        if (parser.isSet(dontUseCustomDirectoryIconsOption)):
            model.setOption(QFileSystemModel.DontUseCustomDirectoryIcons)
        if (parser.isSet(dontWatchOption)):
            model.setOption(QFileSystemModel.DontWatchForChanges)
        self.tree.setModel(model)
        availableSize = QtCore.QSize(self.tree.screen().availableGeometry().size())
        self.tree.resize(availableSize / 2)
        self.tree.setColumnWidth(0, int(self.tree.width() / 3))


        # Set up VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor()
        self.splitter_viewer.addWidget(self.vtkWidget)

        # ipy console
        self.ipyConsole = QIPythonWidget(customBanner="Welcome to the embedded ipython console\n")
        self.splitter_viewer.addWidget(self.ipyConsole)
        self.ipyConsole.pushVariables({"foo":43, "print_process_id":print_process_id, "ipy":self.ipyConsole, "self":self})
        self.ipyConsole.printText("The variable 'foo' and the method 'print_process_id()' are available.\
            Use the 'whos' command for information.\n\nTo push variables run this before starting the UI:\
                \n ipyConsole.pushVariables({\"foo\":43,\"print_process_id\":print_process_id})")

        # Create renderer and add the vedo objects and callbacks
        self.plt = Plotter(qtWidget=self.vtkWidget,bg='DarkSlateBlue',bg2='MidnightBlue',screensize=(1792,1120))
        self.id1 = self.plt.addCallback("mouse click", self.onMouseClick)
        self.id2 = self.plt.addCallback("key press",   self.onKeypress)
        self.plt.show()                  # <--- show the vedo rendering

    def onMouseClick(self, event):
        if(self.action_selectActor.isChecked()):
            self.selectActor(event)
        elif(self.action_selectVertex.isChecked()):
            self.selectVertex(event)

    def selectActor(self,event):
        if(not event.actor):
            return
        printc("You have clicked your mouse button. Event info:\n", event, c='y')
        printc("Left button pressed on", [event.picked3d])
        # adding a silhouette might cause some lags
        # self.plt += event.actor.silhouette().lineWidth(2).c('red')
        #an alternative solution
        self.actorSelection = event.actor.clone()
        self.actorSelection.c('red')
        self.plt += self.actorSelection

    def selectVertex(self,event):
        if(not event.isPoints):
            return
        # print(arr[event.actor.closestPoint(event.picked3d, returnPointId=True)])
        printc("You have clicked your mouse button. Event info:\n", event, c='y')
        printc("Left button pressed on 3d: ", [event.picked3d])
        printc("Left button pressed on 2d: ", [event.picked2d])
        p = pointcloud.Point(pos=(event.picked3d[0],event.picked3d[1],event.picked3d[2]),r=12,c='red',alpha=0.5)
        self.vertexSelections.append(p)
        # self.plt.remove(self.vertexSelections.pop()).add(p)        
        self.plt += p

    def onKeypress(self, evt):
        printc("You have pressed key:", evt.keyPressed, c='b')

    def onClose(self):
        #Disable the interactor before closing to prevent it
        #from trying to act on already deleted items
        printc("..calling onClose")
        self.vtkWidget.close()

    def getDirPath(self):
        """ getDirPath opens a file dialog and only allows the user to select folders """
        return QFileDialog.getExistingDirectory(self, "Open Directory",
                                                os.getcwd(),
                                                QFileDialog.ShowDirsOnly
                                                | QFileDialog.DontResolveSymlinks)

    def getFilePath(self, button_state, load_file=True, display_result=True):
        """ open a file dialog and select a file """
        self.inputPath = QFileDialog.getOpenFileName(self, 'Open File', 
         os.getcwd(), "Ply Files (*.ply);;OBJ Files (*.obj);;STL Files (*.stl)")[0]
        
        print("got input path: ", self.inputPath)
        if load_file:
            if display_result:
                print("displaying results...")
                self.displayResult()
        else: 
            print("load_file must not be true!", load_file)
        return self.inputPath

    def textBrowserDir_state_changed(self):
        """ enable the start button if both the input and output paths are selected. """
        if (self.inputPath and self.outputPath):
            self.pushButton_start.setEnabled(True)
        else:
            self.pushButton_start.setEnabled(False)
    
    def actionSelectActor_state_changed(self):
        if(self.action_selectActor.isChecked()):
            self.action_selectVertex.setChecked(False)

    def actionSelectVertex_state_changed(self):
        if(self.action_selectVertex.isChecked()):
            self.action_selectActor.setChecked(False)
    
    def clearScreen(self):
        self.plt.clear(actors=self.vertexSelections)
        self.plt.clear(actors=self.actorSelection)
        self.plt.show(__doc__)
        print("Cleared screen!")

    def displayResult(self):
        m = Mesh(self.inputPath)
        self.plt.show(m,__doc__)                 # <--- show the vedo rendering
        printc("Number of points",base.BaseActor.N(m))

# %% 
#-------------------------------------------------------------------------------------------------
# %% Main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    print('Screen: %s' % screen.name())
    size = screen.size()
    print('Size: %d x %d' % (size.width(), size.height()))
    mainwindow = MainWindow(size)
    mainwindow.show()
    
    sys.exit(app.exec())
    
# %%
