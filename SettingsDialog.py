from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QDialog,QFileDialog
import os

class SettingsDialog(QDialog):
    def __init__(self,default_settings):
        super(QDialog, self).__init__()

        # load the components defined in th xml file
        loadUi("SettingsDialog.ui", self)
        self.settings = default_settings
        self.applySettings()

        """ Connections for all elements in SettingsDialog """
        self.checkBox_useLastWindowSizeAndPosition.stateChanged.connect(self.checkBox_useLastWindowSizeAndPosition_state_changed)
        self.checkBox_alwaysLastFolder.stateChanged.connect(self.checkBox_alwaysLastFolder_state_changed)
        self.checkBox_alwaysCurrentDir.stateChanged.connect(self.checkBox_alwaysCurrentDir_state_changed)
        self.pushButton_changeDefaultFolder.clicked.connect(self.setDefaultExplorerFolder)

    def applySettings(self):
        try:
            self.checkBox_useLastWindowSizeAndPosition.setChecked(self.settings.value('useLastWindowSizePosition'))
            self.checkBox_alwaysLastFolder.setChecked(self.settings.value('alwaysLastFolder'))
            self.checkBox_alwaysCurrentDir.setChecked(self.settings.value('alwaysCurrentFolder'))
            self.label_explorerFolder.setText(self.settings.value('default explorer folder'))
        except:
            pass

    def checkBox_useLastWindowSizeAndPosition_state_changed(self):
        self.settings.setValue('useLastWindowSizePosition', self.checkBox_useLastWindowSizeAndPosition.isChecked())

    def checkBox_alwaysLastFolder_state_changed(self):
        self.settings.setValue('alwaysLastFolder', self.checkBox_alwaysLastFolder.isChecked())

        if(self.checkBox_alwaysLastFolder.isChecked()):
            self.checkBox_alwaysCurrentDir.setChecked(False)
            self.pushButton_changeDefaultFolder.setEnabled(False)
            self.label_explorerFolder.setEnabled(False)
        elif(not self.checkBox_alwaysCurrentDir.isChecked()):
            self.pushButton_changeDefaultFolder.setEnabled(True)
            self.label_explorerFolder.setEnabled(True)

    def checkBox_alwaysCurrentDir_state_changed(self):
        self.settings.setValue('alwaysCurrentFolder', self.checkBox_alwaysCurrentDir.isChecked())

        if(self.checkBox_alwaysCurrentDir.isChecked()):
            self.checkBox_alwaysLastFolder.setChecked(False)
            self.pushButton_changeDefaultFolder.setEnabled(False)
            self.label_explorerFolder.setEnabled(False)
        elif(not self.checkBox_alwaysLastFolder.isChecked()):
            self.pushButton_changeDefaultFolder.setEnabled(True)
            self.label_explorerFolder.setEnabled(True)

    def setDefaultExplorerFolder(self):
        folderPath = self.getDirPath()
        self.settings.setValue('default explorer folder',folderPath)
        self.label_explorerFolder.setText(self.settings.value('default explorer folder'))

    def getDirPath(self):
        """ getDirPath opens a file dialog and only allows the user to select folders """
        return QFileDialog.getExistingDirectory(self, "Open Directory",
                                                os.getcwd(),
                                                QFileDialog.ShowDirsOnly
                                                | QFileDialog.DontResolveSymlinks)

