import pyqtgraph as pg
from pyqtgraph.dockarea import *
from filters.filterBase.GridFilter import GridFilter

#barebones default visualization
class DataIOFilter(GridFilter):
  def __init__(self, area, bciPath):
    super().__init__(area, bciPath)
  def publish(self):
    super().publish()
    self.area.addDock(Dock("button", widget=pg.QtWidgets.QPushButton("push")))

  def setConfig(self):
    super().setConfig()
    self.chPlot = list(range(self.channels))

    for r in range(self.numRows):
      for c in range(self.numColumns):
        ch = r*self.numColumns+c
        if ch < self.channels:
          self.chPlot[ch] = DefaultPlot(title=self.chNames[ch])
          self.gridPlots.addItem(self.chPlot[ch])
      self.gridPlots.nextRow()

  def plot(self, data):
    self.dataProcessedSignal.emit(data)
    for r in range(self.numRows):
      for c in range(self.numColumns):
        ch = r*self.numColumns+c
        if ch < self.channels:
          self.chPlot[ch].plotData(data[ch])

class DefaultPlot(pg.PlotItem):
  def __init__(self, title):
    super().__init__(title=title)
    self.plotItem = self.plot()

  def plotData(self, data):
    self.plotItem.setData(data)