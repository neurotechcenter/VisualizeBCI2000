
from base.BCI2000Connection import BCI2000Instance, BCI2000Worker
from base.data.AcquireDataThread import AcquireDataThread
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from base.SharedVisualization import Group

#master class that handles communication between threads and filters
#is inherited by every filter in "filters" folder
class MasterFilter(Group):
  chNamesSignal = pyqtSignal(list)
  dataProcessedSignal = pyqtSignal(object) #1D array: size=channels
  def __init__(self, area, bciPath):
    self.setBCIOperator(bciPath)
    super().__init__(area)
    self.elecDict = {}
  def publish(self):
    #BCI2000
    self.t1 = QThread()
    self.w = BCI2000Worker(self.bci, self.__class__.__name__)
    self.w.moveToThread(self.t1)
    self.t1.started.connect(self.w.run)
    self.w.initSignal.connect(self.getParameters)
    self.w.logPrint.connect(self.logPrint)
    self.w.disconnected.connect(self.stop)
    print("starting BCI2000 thread")
    self.t1.start()

    #data thread
    self.t2 = QThread()
    self.acqThr = AcquireDataThread()
    self.acqThr.moveToThread(self.t2)
    self.t2.started.connect(self.acqThr.run)
    self.acqThr.propertiesSignal.connect(self.propertiesAcquired)
    self.acqThr.dataSignal.connect(self.dataAcquired)
    self.acqThr.parameterSignal.connect(self.parameterReceived)
    #self.acqThr.message.connect(self.messageReceived)
    self.acqThr.logPrint.connect(self.logPrint)

    #holds all parameters setn by signal sharing
    self.parameters = {}

    self.address = ('', 0) #default address if none provided
  def setConfig(self):
    self.logPrint(f'Acquiring {self.channels} channels')
    self.chNamesSignal.emit(self.chNames)
    pass
  def stop(self):
    print("STOPPING")
    self.w.stop()
    self.acqThr.stop()
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
    self.acqThr.initalizeAddress(self.address)
    print("starting data thread")
    self.t2.start()
  
  def propertiesAcquired(self, ch, el, chNames):
    print("props acquired")
    self.channels = ch
    self.elements = el
    self.chNames = chNames
    self.setConfig()
  def dataAcquired(self, data):
    self.plot(data)
  def parameterReceived(self, param):
    self.parameters[param['name']] = param
  def messageReceived(self, msg):
    print(msg)
  def logPrint(self, msg):
    self.win.output.append(">>" + msg)
    self.win.output.moveCursor(pg.QtGui.QTextCursor.End)

  def setBCIOperator(self, path):
    try:
      print("setting bci")
      self.bci = BCI2000Instance(path)
    except:
      self.logPrint(f'Could not access BCI2000Remote.dll at {path}')


  ##--slots, inherited by filters--##
  def acceptElecNames(self, elecDict):
    self.elecDict = elecDict