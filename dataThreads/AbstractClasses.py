from abc import abstractmethod
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

class AbstractDataThread(QObject):
  #QThread signal/slots 
  propertiesSignal = pyqtSignal(int, list) #num of elements, ch names
  dataSignal       = pyqtSignal(np.ndarray)
  stateSignal  = pyqtSignal(object)
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
  
class AbstractWorker(QObject):
  disconnected = pyqtSignal()
  initSignal = pyqtSignal(str) #address, e.g., "localhost:1890"
  logPrint = pyqtSignal(str)

  @abstractmethod
  def run(self):
    pass

  @abstractmethod
  def stop(self):
    pass

class AbstractCommunication():
  def __init__(self):
    pass

  #the communication worker run in a separate thread. QObject
  @property
  @abstractmethod
  def worker(self):
    pass
  
  #the data acquisition method which runs in a separate thread. QObject
  @property
  @abstractmethod
  def acqThr(self):
    pass

  #returns boolean
  @abstractmethod
  def evaluate(self, string):
    pass
