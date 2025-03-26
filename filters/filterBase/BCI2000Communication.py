
from base.BCI2000Connection import BCI2000Instance, BCI2000Worker
from base.AcquireDataThread import AcquireDataThread
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from base.SharedVisualization import Group

#master class that handles communication between threads and filters
#is inherited by every filter in "filters" folder
class MasterFilter(Group):
  chNamesSignal = pyqtSignal(list)
  dataProcessedSignal = pyqtSignal(object) #1D array: size=channels
  def __init__(self, area):
    super().__init__(area)
    self.elecDict = {}
  def publish(self):
    #BCI2000
    self.t1 = QThread()
    self.bci = BCI2000Instance('C:/bci2000.x64/prog')
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
    #self.acqThr.disconnected.connect(self.dataThreadDisconnected) #will start again when connected again

    #holds all parameters setn by signal sharing
    self.parameters = {}

    self.address = ('', 0) #default address if none provided
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

  def setConfig(self):
    self.logPrint(f'Acquiring {self.channels} channels')
    self.chNamesSignal.emit(self.chNames)
    pass

  #slots to accept data thread signals
  def dataThreadDisconnected(self):
    st = self.bci.GetSystemState()
    print(st)
    if st == "Busy":
      return #do nothing
    elif st == "Idle":
      #restart, BCI2000 has quit
      self.t2.quit()
      self.area.close()
    return
    print("stopping data thread")
    self.t1.start()
    #get new connection
    self.t2.quit()
    #self.w.run()
  
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

  ##--slots, inherited by filters--##
  def acceptElecNames(self, elecDict):
    self.elecDict = elecDict