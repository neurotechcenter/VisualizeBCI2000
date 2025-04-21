import pyqtgraph as pg
import os

from base.FilterMain import Filters
from base.Brain import BrainWindow
from base.SharedVisualization import Window, MyDockArea, TextOutput
from pyqtgraph.dockarea import *

#class to initialize filters and 3d visualizations
class MainWindow(Window):
  def __init__(self):
    super().__init__()
  def publish(self):
    self.area = MyDockArea()
    self.setCentralWidget(self.area)

    #initialize windows
    self.f = Filters(self)
    self.b = BrainWindow(self)

    #connect windows
    self.f.chNamesSignal.connect(self.b.setConfig)
    self.f.dataProcessedSignal.connect(self.b.plot)
    self.b.emitElectrodeNames.connect(self.f.sendElecNames)
    #create log
    self.output = TextOutput()
    self.area.addDock(Dock("Log", widget=self.output), position='right')
  def connectSetConfig(self, chNames):
    self.b.setConfig(chNames)
  def closeEvent(self, event): #overrides QMainWindow closeEvent
    self.f.saveSettings()
    self.b.saveSettings()
    super().closeEvent(event)

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
