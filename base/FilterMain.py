import os
import sys
import importlib
import traceback
from base.AcquireDataThread import AcquireDataThread
from PyQt5.QtCore import QThread, pyqtSignal
from pyqtgraph.dockarea import *
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from base.SharedVisualization import Window, MyDockArea, TextOutput, Group

#master class that handles communication between threads and filters
#is inherited by every filter in "filters" folder
protectedDocks = ["Load", "Log", "Brain"]
class Filters(Group):
  chNamesSignal = pyqtSignal(list)
  dataProcessedSignal = pyqtSignal(object) #1D array: size=channels
  elecNamesSignal = pyqtSignal(object) #dict
  def __init__(self, area):
    super().__init__(area)
  def publish(self):
    self.path = "filters"
    self.lay = pg.LayoutWidget()
    self.buttons = {}

    #let user choose location of BCI2000
    self.lay.addLabel("BCI2000 Location")
    self.lay.nextRow()
    self.fileBut = pg.QtWidgets.QPushButton("Select BCI2000 Location")
    self.fileBut.clicked.connect(self.loadOperatorPath)
    self.bciName = pg.QtWidgets.QLabel()
    self.lay.addWidget(self.fileBut)
    self.lay.addWidget(self.bciName)
    self.lay.nextRow()

    #add filter visualizations from files in "filters" folder
    self.lay.addLabel("Filters")
    self.lay.nextRow()
    files = os.listdir(self.path)
    try:
      files.remove("__pycache__")
      files.remove("filterBase") #folder
    except:
      pass
    for file in files:
      fName = file.replace(".py", "")
      filterBut = pg.QtWidgets.QPushButton(fName)
      filterBut.setCheckable(True)
      filterBut.clicked.connect(lambda checked, i=fName: self.runFilter(i))
      self.lay.addWidget(filterBut)
      self.buttons[fName] = filterBut

    self.area.addDock(Dock("Load", widget=self.lay, autoOrientation=False))

  def loadOperatorPath(self):
    #ask for file name
    file_dialog = pg.QtWidgets.QFileDialog()
    file_dialog.setWindowTitle("Select BCI2000 Location")
    file_dialog.setFileMode(pg.QtWidgets.QFileDialog.FileMode.Directory)
    file_dialog.setOption(pg.QtWidgets.QFileDialog.ShowDirsOnly, True)
    file_dialog.setNameFilter("BCI2000 root folder")

    if file_dialog.exec():
      selected_files = file_dialog.selectedFiles()
      print(selected_files)
      self.bciName.setText(selected_files[0])
    else:
      #file not chosen
      return

#for filter to be run, the class name, file name, and filter name must all be equal
  def runFilter(self, file):
    mod = self.path + "." + file
    try:
      if hasattr(self, "mod"):
        #close past connection
        self.mod.stop()
        #attempt to delete all docks but protected ones
        docks = self.area.findAll()[1]
        for d in docks:
          if d not in protectedDocks:
            docks[d].close()
        self.area.apoptose()
      filterModule = importlib.import_module(mod) #in filters folder
      self.mod = filterModule.__dict__[file](self.win) #assumes class is same name as file
      self.mod.chNamesSignal.connect(self.emitChNames)
      self.mod.dataProcessedSignal.connect(self.emitData)
      self.elecNamesSignal.connect(self.mod.acceptElecNames)
      for b in self.buttons.values():
        b.setChecked(False)
      self.buttons[file].setChecked(True)
      return True
    except:
      traceback.print_exc()
      self.logPrint(f"Could not access {mod}!")
      return False
    
  #automatically start last chosen filter
  def loadSettings(self):
    super().loadSettings()
    filter = self.settings.value("filter", "")
    if filter != "":
      self.runFilter(filter)

  def saveSettings(self):
    super().saveSettings()
    self.settings.setValue("filter", self.mod.__class__.__name__)

  #button functions
  def _handleButtonPress(self, file):
    if self.runFilter(file):
      #filter has run, disable buttons
      self._toggleButtons(False)
  def _filterClosedSlot(self):
    #re-enable buttons
    self._toggleButtons(True)
    del self.mod
  def _toggleButtons(self, enable):
    for b in self.buttons:
      b.setEnabled(enable)
  
  #pass along signals from filter to brain
  def emitChNames(self, chNames):
    self.chNamesSignal.emit(chNames)
  def emitData(self, data):
    self.dataProcessedSignal.emit(data)
  
  #send signals from brain to filter
  def sendElecNames(self, elecDict):
    self.elecNamesSignal.emit(elecDict)