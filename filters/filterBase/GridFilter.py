from filters.filterBase.BCI2000Communication import MasterFilter
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock

#abstract class for any grid visualizations
class GridFilter(MasterFilter):
  def __init__(self, area):
    super().__init__(area)
  def publish(self):
    super().publish()
    self.gridPlots = pg.GraphicsLayoutWidget()

  def setConfig(self):
    super().setConfig()
    self.gridPlots.clear()
    if hasattr(self, '_maxWindows'):
      self.windows = min(self._maxWindows, self.channels)
    else:
      self.windows = self.channels
    self.windows = max(self.windows, 0)
    if self.windows == 0:
      self.numRows = 0
      self.numColumns = 0
    else:
      self.numColumns = int(np.floor(np.sqrt(self.windows)))
      self.numRows = int(np.ceil(self.windows / self.numColumns))
    pass