import sys
import os
import importlib
from PyQt5.QtCore import QThread, pyqtSignal, QObject

#function to start connection to BCI2000 operator
def BCI2000Instance(bciPath):
  progPath = os.path.join(bciPath, "prog")
  sys.path.append(progPath) #BCI2000 prog path
  try:
    BCI2000Remote = importlib.import_module('BCI2000Remote') #in prog folder
    return BCI2000Remote.BCI2000Remote() #init BCI2000 remote
  except:
    sys.exit("Could not access BCI2000Remote.dll! Make sure BCI2000/prog is in your path")

#worker that waits for connection in separate thread, 
# then populates sharing parameter if empty.
# Then waits for BCI2000 to quit to stop and close threads
class BCI2000Worker(QObject):
  disconnected = pyqtSignal()
  filtersListed = pyqtSignal(list)
  initSignal = pyqtSignal(str)
  logPrint = pyqtSignal(str)
  def __init__(self, bci, className):
    super().__init__()
    self.bci = bci
    self.className = className
    self.bci.Connect()
    self.initialized = False
    self.go = True
    self.oldSystemState = ""
    self._isRunning = True
  def stop(self):
    self._isRunning = False
  def waitForState(self, state):
    print(f'waiting for {state}...')
    self.bci.Execute(f'WAIT FOR {state}')
    self.initSignal.emit()
  def run(self):
    notConnected = True
    while notConnected:
      self.bci.Execute("WAIT FOR CONNECTED|RESTING 0.5")
      notConnected = self.bci.Result == 'false'
      st = self.bci.GetSystemState()
      if st == "Suspended":
        self.logPrint.emit("Press Set Config to connect...")
      elif st == "Running":
        self.logPrint.emit("Stop the run to connect...")
      if not self._isRunning: return

    #access sharing parameter
    while True:
      try:
        p = self.bci.GetParameter(f'Share{self.className}')
        if p == "":
          #populate parameter
          self.bci.Execute(f'SET PARAMETER Share{self.className} localhost:1897')
          QThread.msleep(50) #sleep for 50ms before accessing new parameter
        else:
          self.initSignal.emit(p)
          break
      except:
        self.logPrint.emit(f'Parameter Share{self.className} does not exist! Cannot acquire data')
        break

    while self._isRunning:
      try:
        QThread.sleep(1)
        st = self.bci.GetSystemState()
        if st == "Idle" or st == "":
          break
      except:
        break
      
    #we have disconnected from bci2000
    print("DISCONNECTED")
    self.disconnected.emit()
