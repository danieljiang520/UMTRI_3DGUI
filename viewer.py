# Stripped down Qt-vtk-based viewer for ply, obj etc.
# 2022-01-24
# Building up from DanielJ example code


# %%

# standard lib imports

# from msilib.schema import RadioButton
from shutil import ReadError
import sys, copy, time
from pathlib import Path
import os

from vedo import Plotter, printc,Mesh,base,pointcloud
from PyQt5 import Qt, QtCore

# %% project-specific imports
## Qt
from PyQt5.uic import loadUi

from PyQt5.QtWidgets import (
    QMainWindow, 
    QFileDialog, 
    QListWidgetItem, 
    QMessageBox, 
    QApplication,
    QApplication
)
from numpy import polymul

## These for embeded pythion console

#import os
os.environ['QT_API'] = 'pyqt5'

from PyQt5.QtCore import QSize
# ipython won't work if this is not correctly installed. And the error message will be misleading
from PyQt5 import QtSvg 
#

from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
#from IPython.qt.inprocess import QtInProcessKernelManager
# these are updated based on error messages
#from qtconsole import rich_ipython_widget

from qtconsole.inprocess import QtInProcessKernelManager

## vtk
# from vtkmodules.vtkIOPLY import (
#     vtkPLYReader
# )
# from vtkmodules.vtkRenderingCore import (
#     vtkActor,
#     vtkPolyDataMapper,
#     # vtkRenderWindow,
#     # vtkRenderWindowInteractor,
#     vtkRenderer
# )
# from vtkmodules.vtkCommonColor import vtkNamedColors
# from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

# from vtkmodules.vtkIOGeometry import (
#     vtkBYUReader,
#     vtkOBJReader,
#     vtkSTLReader
# )

# from vtkmodules.vtkIOLegacy import vtkPolyDataReader
# from vtkmodules.vtkIOPLY import vtkPLYReader
# from vtkmodules.vtkIOXML import vtkXMLPolyDataReader



# project imports

# from job import *

# %%




# %%



# def ReadPolyData(file_name):
#     valid_suffixes = ['.g', '.obj', '.stl', '.ply', '.vtk', '.vtp']
#     path = Path(file_name)
#     if path.suffix:
#         ext = path.suffix.lower()
#     if path.suffix not in valid_suffixes:
#         print(f'No reader for this file suffix: {ext}')
#         return None
#     else:
#         if ext == ".ply":
#             reader = vtkPLYReader()
#             reader.SetFileName(file_name)
#             reader.Update()
#             poly_data = reader.GetOutput()
#         elif ext == ".vtp":
#             reader = vtkXMLPolyDataReader()
#             reader.SetFileName(file_name)
#             reader.Update()
#             poly_data = reader.GetOutput()
#         elif ext == ".obj":
#             reader = vtkOBJReader()
#             reader.SetFileName(file_name)
#             reader.Update()
#             poly_data = reader.GetOutput()
#         elif ext == ".stl":
#             reader = vtkSTLReader()
#             reader.SetFileName(file_name)
#             reader.Update()
#             poly_data = reader.GetOutput()
#         elif ext == ".vtk":
#             reader = vtkPolyDataReader()
#             reader.SetFileName(file_name)
#             reader.Update()
#             poly_data = reader.GetOutput()
#         elif ext == ".g":
#             reader = vtkBYUReader()
#             reader.SetGeometryFileName(file_name)
#             reader.Update()
#             poly_data = reader.GetOutput()

#         return poly_data


# %%

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
# %%
# this class for the console


class QIPythonWidget(RichIPythonWidget):
    """ Convenience class for a live IPython console widget. We can replace the standard banner using the customBanner argument
    """
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
        """ Given a dictionary containing name / value pairs, push those variables to the IPython console widget """
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


# %%

# Main application window
class MainWindow(QMainWindow):
    inputPath = "" # absolute path to the input ply scan
    outputPath = "" # absolute path to the output folder
    resultPath = "" # path to the most recent finished project ply file
    vertexSelections = [None]
    actorSelection = None

    def __init__(self,size):
        super(MainWindow, self).__init__()
        # loadUi("SAS_GUI.ui", self) # load the components defined in th xml file
        loadUi("viewer_gui.ui", self)
        self.screenSize = size
        # Connections for all elements in Mainwindow
        self.pushButton_inputfile.clicked.connect(self.getFilePath)
        self.pushButton_clearSelection.clicked.connect(self.clearScreen)
        # self.textBrowser_inputDir.textChanged.connect(self.textBrowserDir_state_changed)
        # self.pushButton_outputDir.clicked.connect(self.getOutputFilePath)
        # self.textBrowser_outputDir.textChanged.connect(self.textBrowserDir_state_changed)
        # self.pushButton_monitor.clicked.connect(self.expandMonitor)
        # self.pushButton_start.clicked.connect(self.startProcessing)
        # self.pushButton_saveAndContinue.clicked.connect(self.saveAndContinue)
        # self.pushButton_dontSave.clicked.connect(self.deleteAndContinue)
        # self.pushButton_redo.clicked.connect(self.redo)

        # Set up VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor()
        self.verticalLayout_midMid.addWidget(self.vtkWidget)
        # self.ren = vtkRenderer()
        # colors = vtkNamedColors()
        # self.ren.SetBackground(colors.GetColor3d('White')) # DarkSlateBlue
        # self.ren.SetBackground2(colors.GetColor3d('MidnightBlue'))
        # self.ren.GradientBackgroundOn()
        # self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        # self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        # style = vtkInteractorStyleTrackballCamera()
        # self.iren.SetInteractorStyle(style)

        # ipy console
        self.ipyConsole = QIPythonWidget(customBanner="Welcome to the embedded ipython console\n")
        self.horizontalLayout_midBottom.addWidget(self.ipyConsole)
        self.ipyConsole.pushVariables({"foo":43, "print_process_id":print_process_id, "ipy":self.ipyConsole, "self":self})
        self.ipyConsole.printText("The variable 'foo' and the method 'print_process_id()' are available. Use the 'whos' command for information.\n\nTo push variables run this before starting the UI:\n ipyConsole.pushVariables({\"foo\":43,\"print_process_id\":print_process_id})")
       
        # Create renderer and add the vedo objects and callbacks
        # s = QtCore.QSize(size[0],size[1])
        # print("x:",self.vtkWidget.x(),"; y: ",self.vtkWidget.y())
        self.plt = Plotter(qtWidget=self.vtkWidget,bg='DarkSlateBlue',bg2='MidnightBlue')
        self.id1 = self.plt.addCallback("mouse click", self.onMouseClick)
        self.id2 = self.plt.addCallback("key press",   self.onKeypress)
        self.plt.show(__doc__)                  # <--- show the vedo rendering

        

        

    def onMouseClick(self, event):
        if(self.radioButton_selectActor.isChecked()):
            self.selectActor(event)
        elif(self.radioButton_selectVertex.isChecked()):
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
        printc("Left button pressed on", [event.picked3d])
        printc(event.picked3d[0]," ",len(event.picked3d))
        p = pointcloud.Point(pos=(event.picked3d[0],event.picked3d[1],event.picked3d[2]),r=12,c='red',alpha=0.5)
        # self.plt.remove(self.vertexSelections.pop()).add(p)
        self.vertexSelections.append(p)        
        self.plt += p

    def onKeypress(self, evt):
        printc("You have pressed key:", evt.keyPressed, c='b')

    def onClose(self):
        #Disable the interactor before closing to prevent it
        #from trying to act on already deleted items
        printc("..calling onClose")
        self.vtkWidget.close()

    def getDirPath(self):
        """
        getDirPath opens a file dialog and only allows the user to select folders
        """ 
        return QFileDialog.getExistingDirectory(self, "Open Directory",
                                                os.getcwd(),
                                                QFileDialog.ShowDirsOnly
                                                | QFileDialog.DontResolveSymlinks)
    ## MPR
    def getFilePath(self, button_state, load_file=True, display_result=True):
        """
        open a file dialog and select a file
        """ 
        self.inputPath = QFileDialog.getOpenFileName(self, 'Open File', 
         os.getcwd(), "Ply Files (*.ply);;OBJ Files (*.obj);;STL Files (*.stl)")[0]
        
        print("got input path: ", self.inputPath)

        # display the file?
        
        if load_file:
            # print("trying to load file")
            # self.loadFile(self.inputPath)
            self.displayResult()
            print("loaded file: ", self.inputPath)
            # if display_result:
            #     print("displaying results...")
            #     self.displayResult(self.polyData)
        else: 
            print("load_file must not be true!", load_file)
            
            
        # self.displayResult(self.inputPath)
        return self.inputPath

    # def loadFile(self, filename):
    #     """ load the specified file """
    #     print("in load file")
    #     self.polyData = ReadPolyData(filename)
    #     return self.polyData 

    def textBrowserDir_state_changed(self):
        """
        enable the start button if both the input and output paths are selected.
        """ 
        if (self.inputPath and self.outputPath):
            self.pushButton_start.setEnabled(True)
        else:
            self.pushButton_start.setEnabled(False)
    
    def clearScreen(self):
        self.plt.clear(actors=self.vertexSelections)
        self.plt.clear(actors=self.actorSelection)
        self.plt.show(__doc__)
        print("Cleared screen!")

    def displayResult(self):
    #     self.ren.RemoveAllViewProps()
    #     # Read and display for verification
    #     #reader = vtkPLYReader()
    #    # reader.SetFileName(filename)
    #    # temp hardcode file name
    #     # reader.SetFileName(self.inputPath)
    #     #reader.Update()
    #     # self.polyData = ReadPolyData(self.inputPath)
    #     # Create a mapper
    #     mapper = vtkPolyDataMapper()
    #     # mapper.SetInputConnection(reader.GetOutputPort())
    #     #mapper.SetInputConnection(reader.GetOutputPort())
    #     mapper.SetInputData(polyData)
    #     # Create an actor
    #     actor = vtkActor()
    #     actor.SetMapper(mapper)
    #     self.ren.AddActor(actor)
    #     self.ren.ResetCamera()
    #     # Show
    #     self.iren.Initialize()
    #     self.iren.Start()
        m = Mesh(self.inputPath)
        self.plt.show(m,__doc__)                 # <--- show the vedo rendering
        printc("Number of points",base.BaseActor.N(m))

# %% 

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
