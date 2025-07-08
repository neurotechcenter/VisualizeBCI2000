
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from base.SharedVisualization import Group
import importlib
import traceback
from abc import abstractmethod

#master class that handles communication between threads and filters
#is inherited by every filter in "filters" folder
class MasterFilter(Group):
  chNamesSignal = pyqtSignal(list)
  dataProcessedSignal = pyqtSignal(object) #1D array: size=channels

  @abstractmethod
  def plot(self, data):
    pass

  @abstractmethod
  def receiveStates(self, state):
    pass

  #must be defined for each filter
  #defines states that will be used by the filter to be shared in BCI2000
  @property
  @abstractmethod
  def sharedStates(self):
    pass

  def __init__(self, area, bciPath, stream):
    self.bciPath = bciPath
    self.streamName = stream
    super().__init__(area)
    self.elecDict = {}
  def publish(self):
    #initialize desired communication
    self.comm = self.setDataStream(self.bciPath, self.streamName[0], self.streamName[1])

    #data thread
    self.t2 = QThread()
    self.comm.acqThr.moveToThread(self.t2)
    self.t2.started.connect(self.comm.acqThr.run)
    self.comm.acqThr.propertiesSignal.connect(self.propertiesAcquired)
    self.comm.acqThr.dataSignal.connect(self.plot)
    self.comm.acqThr.stateSignal.connect(self.receiveStates)
    self.comm.acqThr.parameterSignal.connect(self.parameterReceived)
    self.comm.acqThr.printSignal.connect(self.logPrint)
    self.comm.acqThr.disconnected.connect(self.resetConnection)

    #BCI2000
    self.t1 = QThread()
    self.comm.worker.moveToThread(self.t1)
    self.t1.started.connect(self.comm.worker.run)
    self.comm.worker.initSignal.connect(self.getParameters)
    self.comm.worker.logPrint.connect(self.logPrint)
    print("starting BCI2000 thread")
    self.t1.start()

    #holds all parameters sent by signal sharing
    self.parameters = {}

    self.address = ('', 0) #default address if none provided
  def setConfig(self):
    self.logPrint(f'Acquiring {self.channels} channels')
    self.chNamesSignal.emit(self.chNames)
    pass

  def resetConnection(self):
    try: #try to reset connection to BCI2000 if we can
      if not self.comm.worker.bci.GetSystemState() == "Resting":
        self.t1.sleep(1)
        self.comm.worker.startRemote()
        self.t1.quit()
        self.t1.wait()
        self.t1.start()
    except:
      pass

  def stop(self):
    print("STOPPING")
    self.comm.worker.stop()
    self.comm.acqThr.stop()
    #stop BCI2000 thread
    self.t1.quit()
    #stop data acquisition
    self.t2.quit()
    #wait for both threads to exit
    self.t1.wait()
    self.t2.wait()
  
  def getParameters(self, addy):
    newAddy = addy.split(':')
    if newAddy != self.address:
      self.address = newAddy
    self.t1.quit()
    self.comm.acqThr.initalize(self.address)
    print("starting data thread")
    self.t2.start()
  
  def propertiesAcquired(self, el, chNames):
    print("props acquired")
    self.channels = len(chNames)
    self.elements = el
    self.chNames = chNames
    self.setConfig()

  def parameterReceived(self, param):
    self.parameters[param['name']] = param

  def getParameterValue(self, pName):
    p = self.parameters[pName]
    return float(p['val'])

  def logPrint(self, msg):
    self.win.output.append(">>" + msg)
    self.win.output.moveCursor(pg.QtGui.QTextCursor.End)

  def setDataStream(self, bciPath, path, file):
    try:
      mod = importlib.import_module(path + "." + file)
      return mod.__dict__[file](bciPath, self.__class__.__name__, self.sharedStates)
    except:
      #self.logPrint(f"Data thread could not be loaded! Chosen stream: {file}")
      traceback.print_exc()

  ##--slots, inherited by filters--##
  def acceptElecNames(self, elecDict):
    self.elecDict = elecDict
