from abc import abstractmethod
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

class AbstractDataThread(QObject):
  #QThread signal/slots 
  propertiesSignal = pyqtSignal(int, list) #num of elements, ch names
  dataSignal       = pyqtSignal(np.ndarray)
  parameterSignal  = pyqtSignal(object)
  printSignal      = pyqtSignal(str)

  @abstractmethod
  def stop(self):
    pass

  @abstractmethod
  def initialize(self, address):
    pass

  @abstractmethod
  def run(self):
    pass
  