
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

class AbstractDataThread(QObject):
  #QThread signal/slots 
  propertiesSignal = pyqtSignal(int, int, list) #ch, el, ch names
  dataSignal       = pyqtSignal(np.ndarray)
  parameterSignal  = pyqtSignal(object)
  printSignal         = pyqtSignal(str)