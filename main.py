import pyqtgraph as pg
import os
import importlib
import traceback

from base.Brain import BrainWindow
from base.SharedVisualization import Window, MyDockArea, TextOutput
from pyqtgraph.dockarea import *
from base.SharedVisualization import Group

#class to initialize filters and 3d visualizations
protectedDocks = ["Load", "Log", "Brain"]
class MainWindow(Window):
  def __init__(self):
    self.area = MyDockArea()
    super().__init__()
    #Window.__init__(self)
  def publish(self):
    self.setCentralWidget(self.area)
    #create log
    self.output = TextOutput()
    self.fPath = "filters"

    #toolbar
    menu = self.menuBar()
    file_menu = menu.addMenu("&File")
    button_action = pg.QtWidgets.QAction("Choose BCI2000 Location...", self)
    button_action.setStatusTip("BCI2000 directory location")
    file_menu.addAction(button_action)
    self.filters = {}

    #initialize 3d window
    self.b = BrainWindow(self)

    #connect windows to toolbar
    button_action.triggered.connect(self.loadOperatorPath)
    #add filters to toolbar
    filterMenu = menu.addMenu("&Filters")
    files = os.listdir(self.fPath)
    try:
      files.remove("__pycache__")
      files.remove("filterBase") #folder
    except:
      pass
    for file in files:
      fName = file.replace(".py", "")
      filterBut = pg.QtWidgets.QAction(fName, self)
      filterBut.setCheckable(True)
      filterBut.triggered.connect(lambda checked, i=fName: self.runFilter(i))

      filterMenu.addAction(filterBut)
      self.filters[fName] = filterBut

    #add log last
    self.area.addDock(Dock("Log", widget=self.output), position='right')
  def connectSetConfig(self, chNames):
    self.b.setConfig(chNames)
  def closeEvent(self, event): #overrides QMainWindow closeEvent
    #self.f.saveSettings()
    self.b.saveSettings()
    super().closeEvent(event)

  def runFilter(self, file):
    if self.bciPath == "":
      #no operator path set
      self.logPrint("BCI2000 IS NOT SET. Choose the path first.")
      self.filters[file].setChecked(False)
      return False
    mod = self.fPath + "." + file
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
      self.mod = filterModule.__dict__[file](self.win, self.bciPath) #assumes class is same name as file

      #connect windows
      self.mod.chNamesSignal.connect(self.b.setConfig)
      self.mod.dataProcessedSignal.connect(self.b.plot)
      self.b.emitElectrodeNames.connect(self.mod.acceptElecNames)

      for b in self.filters.values():
        b.setChecked(False)
      self.filters[file].setChecked(True)
      return True
    except:
      traceback.print_exc()
      self.logPrint(f"Could not access {mod}!")
      self.filters[file].setChecked(False)
      return False

  def loadOperatorPath(self):
    #ask for file name
    file_dialog = pg.QtWidgets.QFileDialog()
    file_dialog.setWindowTitle("Select BCI2000 Location")
    file_dialog.setFileMode(pg.QtWidgets.QFileDialog.FileMode.Directory)
    file_dialog.setOption(pg.QtWidgets.QFileDialog.ShowDirsOnly, True)
    file_dialog.setNameFilter("BCI2000 root folder")

    if file_dialog.exec():
      selected_files = file_dialog.selectedFiles()
      p = selected_files[0]
      print(p)
      self.logPrint(f"BCI2000 directory chosen: {p}")
      #self.bciName.setText(p)
      if p != self.bciPath:
        self.bciPath = p
        if hasattr(self, 'mod'):
          #path has changed, reset filter with new operator
          self.runFilter(self.mod.__class__.__name__)
    else:
      #file not chosen
      return
  
  #automatically start last chosen filter
  def loadSettings(self):
    Group.loadSettings(self)
    self.bciPath = self.settings.value("bciPath", "")
    if self.bciPath == "":
      self.logPrint("Welcome! Choose your BCI2000 directory (File menu)")
    else:
      self.logPrint(f"Using BCI2000 at {self.bciPath}")
    #self.bciName.setText(self.bciPath)
    
    filter = self.settings.value("filter", "")
    if filter != "":
      self.runFilter(filter)

    #load geometry after filter is in place
    Window.loadSettings(self)

  def saveSettings(self):
    super().saveSettings()
    self.settings.setValue("bciPath", self.bciPath)
    if hasattr(self, "mod"):
      self.settings.setValue("filter", self.mod.__class__.__name__)
      self.mod.saveSettings()

if __name__ == '__main__':
  #change current directory to file location
  abspath = os.path.abspath(__file__)
  dname = os.path.dirname(abspath)
  os.chdir(dname)

  #start gui
  pg.mkQApp("VisualizeBCI2000")
  main = MainWindow()
  main.show()
  pg.exec()
