import pyqtgraph as pg
import os
import sys
import importlib
import traceback

from base.Vis3D import BrainWindow
from base.SharedVisualization import Window
import pyqtgraph.parametertree as ptree
from pyqtgraph.parametertree import interact
import pyqtgraph.parametertree.parameterTypes as pTypes

#class to initialize filters and 3d visualizations
class MainWindow(Window):
  def __init__(self):
    super().__init__()
  def publish(self):
    super().publish()
    self.path = "filters"
    self.lay = pg.LayoutWidget()
    self.buttons = []

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
    files.remove("__pycache__")
    for file in files:
      filter = pg.QtWidgets.QPushButton(file.replace(".py", ""))
      filter.clicked.connect(lambda checked, i=file.replace(".py", ""): self._handleButtonPress(i))
      self.lay.addWidget(filter)
      self.buttons.append(filter)

    #add option to also visualize 3d
    self.lay.nextRow()
    self.lay.addLabel("3D Visualization")
    self.lay.nextRow()    
    self.brainBut = pg.QtWidgets.QPushButton("Brain visualization")
    self.brainBut.clicked.connect(self.start3dVis)
    self.lay.addWidget(self.brainBut, colspan=len(files))

    self.setCentralWidget(self.lay)

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
      filterModule = importlib.import_module(mod) #in filters folder
      self.mod = filterModule.__dict__[file]() #assumes class is same name as file
      self.mod.show()
      self.mod.chNamesSignal.connect(self.sendChNamesToBrain)
      self.mod.dataProcessedSignal.connect(self.sendDataToBrain)
      self.mod.closed.connect(self._filterClosedSlot)
      return True
    except:
      traceback.print_exc() 
      sys.exit(f"Could not access {mod}!")
      return False

  #brain functions
  def sendChNamesToBrain(self, names):
    if hasattr(self, 'brain'):
      self.brain.setConfig(names)
  #data should be 1D vector, 1 element for each channel
  def sendDataToBrain(self, data):
    if hasattr(self, 'brain'):
      self.brain.plot(data)
  def start3dVis(self):
    self.brain = BrainWindow()
    self.brain.closed.connect(self.enableBrainBut)
    self.brainBut.setEnabled(False)
    self.brain.show()
  def enableBrainBut(self):
    self.brainBut.setEnabled(True)
    # if hasattr(self.brain, "viewWidget"):
    #   self.brain.viewWidget.clear()
    #   self.brain.viewWidget.reset()
    # del self.brain

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
