import socket
from select import select
from multiprocessing import shared_memory
import numpy as np
import sys
import os
import importlib
import io
import struct
import traceback
import platform
from enum import Enum
from PyQt5.QtCore import QThread

from base.BCI2kReaderMod import ParseParam
from dataThreads.AbstractClasses import *
#
# Data acquisition thread from BCI2000's shared memory
# Acquires signals and states, their properties, and parameters
#
class BCI2000(AbstractCommunication):
  def __init__(self, bciPath, file, sharedStates):
    self._acqThr = BCI2000DataThread()
    self._worker = BCI2000Worker(bciPath, file, sharedStates)

  @property
  def worker(self):
    return self._worker
  @property
  def acqThr(self):
    return self._acqThr
  
  def evaluate(self, state):
    return int(self.worker.bci.GetStateVariable(state).value)

#function to start connection to BCI2000 operator
def BCI2000Instance(bciPath):
  progPath = os.path.join(bciPath, "prog")
  sys.path.append(progPath) #BCI2000 prog path
  try:
    BCI2000Remote = importlib.import_module('BCI2000Remote') #in prog folder
    return BCI2000Remote.BCI2000Remote() #init BCI2000 remote
  except:
    sys.exit("Could not access BCI2000Remote.py! Make sure BCI2000/prog is in your path")

class BCI2000Worker(AbstractWorker):
  def __init__(self, bciPath, className, sharedStates):
    super().__init__()
    self.bciPath = bciPath
    self.startRemote()
    self.className = className
    self.sharedStateList = sharedStates
    self.initialized = False
    self.go = True
    self.oldSystemState = ""
    self._isRunning = True
    self.startedDataThread = False
  def stop(self):
    self._isRunning = False
  def startRemote(self):
    self.bci = BCI2000Instance(self.bciPath)
    self.bci.Disconnect()
    self.bci.Connect()
  def run(self):
    notConnected = True
    while notConnected:
      self.bci.Execute("WAIT FOR CONNECTED|RESTING 0.5")
      notConnected = self.bci.Result == 'false'
      st = self.bci.GetSystemState()
      if st == "Suspended":
        self.logPrint.emit("Press Set Config twice to connect...")
      elif st == "Running":
        self.logPrint.emit("Stop the run to connect...")
      if not self._isRunning: return

    #access sharing parameter
    ready = False
    p = ""
    while True:
      try:
        p = self.bci.GetParameter(f'Share{self.className}')
        if p == "":
          #populate parameter
          self.bci.Execute(f'SET PARAMETER Share{self.className} localhost:1897')
          QThread.msleep(50) #sleep for 50ms before accessing new parameter
        else:
          ready = True
          break
      except:
        self.logPrint.emit(f'Parameter Share{self.className} does not exist! Cannot acquire data')
        break

    #access shared states parameter
    #p = self.bci.GetParameter(f'Share{self.className}')
    if ready:
      if self.sharedStateList:
        sts = " ".join(self.sharedStateList)
        while True:
          try:
            #suppress error messages first, bc for some reason
            #getting an empty parameter gives an error
            self.bci.Execute('SET LogLevel 1')
            self.bci.Execute('SET AbortOnError 0')
            #silently check parameter
            stP = self.bci.GetParameter(f'Share{self.className}States')
            if stP == f"Parameter Share{self.className}States is empty" or stP == "":
              self.bci.Execute(f'SET PARAMETER % list Share{self.className}States= {len(self.sharedStateList)} {sts}')
              QThread.msleep(50)
            else:
              #we are ready to start data thread!
              if not self.startedDataThread:
                self.initSignal.emit(p)
                self.startedDataThread = True
              break
          except:
            self.logPrint.emit(f'Parameter Share{self.className}States is not properly populated! Cannot acquire data')
            break
      else:
        #we are ready to start data thread!
        if not self.startedDataThread:
          self.initSignal.emit(p)
          self.startedDataThread = True

    #bring error messages back
    self.bci.Execute('SET LogLevel 1')
    self.bci.Execute('SET AbortOnError 1')

class BCI2000DataThread(AbstractDataThread):
  def __init__(self):
    super(BCI2000DataThread, self).__init__()
    self._isRunning = True
  def stop(self):
    self._isRunning = False

  def waitForRead(self, sock):
    """polling wait for data on the socket so we may react to a keyboard interrupt"""
    pollingIntervalSeconds = 0.1
    ready, _, _ = select([sock], [], [], pollingIntervalSeconds)
    while not ready and self._isRunning:
      try:
        ready, _, _ = select([sock], [], [], pollingIntervalSeconds)
      except KeyboardInterrupt:
        self.print('Keyboard interrupt, exiting')
        quit()

  def initalize(self, address):
    try:
      # With the help of bind() function 
      # binding host and port
      self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.s.bind((address[0], int(address[1])))
        
    except socket.error as message:
      # if any error occurs then with the 
      # help of sys.exit() exit from the program
      print('Bind failed. Error Code : '
          + str(message[0]) + ' Message '
          + message[1])
      sys.exit()
    self.s.listen(1)
    self.s.settimeout(0.1)        
    
  def receiveSignal(self, msg):
    if msg.shm not in self.memInfo:
      memObj = shared_memory.SharedMemory(msg.shm)
      self.memInfo[msg.shm] = memObj
    else:
      memObj = self.memInfo[msg.shm]

    signal = np.ndarray((msg.channels, msg.elements),dtype=np.double, buffer=memObj.buf)
    return signal

  def run(self):
    while self._isRunning:
      self.memInfo = {}
      #listen for connection on specified port
      try:
        address = self.s.getsockname()
        self.printSignal.emit("Waiting for BCI2000 at %s:%s" %(address[0], address[1]))
        self.waitForRead(self.s)
        conn, addr = self.s.accept()
        self.printSignal.emit(f"Connected by {addr}")
        stream = conn.makefile('rb')
        while self._isRunning: #go until we receive an EOFError exception
          QThread.usleep(1) #use sleep to not get stuck waiting for read
          self.waitForRead(conn)
          msg = receiveBciMessage(stream)
          
          if msg.kind == 'SignalProperties' and msg.sourceID == 'Signal':
            print("SIGNAL PROPERTIES")
            self.propertiesSignal.emit(msg.elements, msg.chNames)

          elif msg.kind == 'SignalProperties' and msg.sourceID == 'States':
            pass
          
          elif msg.kind == 'Signal' and msg.sourceID == 'Signal':
            self.dataSignal.emit(self.receiveSignal(msg))

          elif msg.kind == 'Parameter':
            self.parameterSignal.emit(msg.param)
            continue

          elif msg.kind == 'Signal' and msg.sourceID == 'States':
            #round incoming signal to nearest int
            self.stateSignal.emit(np.round(self.receiveSignal(msg)))
            pass

          elif msg.kind == 'SysCommand' and msg.command == 'EndOfData':
            continue

          elif msg.kind == 'SysCommand' and msg.command == 'EndOfTransmission':
            print('end of transmission')
            continue

          else:
            raise RuntimeError('Unexpected BCI2000 message')

      except EOFError:
        self.disconnected.emit()
        QThread.sleep(1) #wait for update if we are disconnected from BCI2000
        if not self._isRunning:
          print('stopping acq thread')
          conn.close()
          self.s.close()
          return
        continue

      except socket.timeout:
        pass

      except Exception:
        print("excpetion")
        conn.close()
        traceback.print_exc()
        return

###____________________###
###___HELPER METHODS___###
###____________________###
class Object(object):
  pass

def readLine(stream, terminator = b'\n'):
  """read a line from a stream up to terminator character"""
  chars = []
  c = stream.read(1)
  while c != terminator and c != b'':
    chars.append(c)
    c = stream.read(1)
  return str(b''.join(chars), 'utf-8')

class BciDescSupp(Enum):
  """BCI2000 descriptor and supplement for relevant messages"""
  Parameter = b'\x02\x00'
  State = b'\x03\x00'
  SignalData = b'\x04\x01'
  SignalProperties = b'\x04\x03'
  SysCommand = b'\x06\x00'

def readBciLengthField(stream, fieldSize):
  """read a length field of specified size from a stream"""
  # read fieldSize bytes that make up a little-endian number
  b = stream.read(fieldSize)
  if b == b'':
    raise EOFError()
  if len(b) != fieldSize:
    raise RuntimeError('Could not read size field')
  n = int.from_bytes(b, 'little')
  # if all bytes are 0xff, ignore them and read the field value as a string
  if n == (1 << (fieldSize * 8)) - 1:
    n = int(readLine(stream, b'\x00'))
  return n

def writeBciLengthField(stream, fieldSize, value):
  """write a length field of specified size to a stream"""
  n = (1 << (fieldSize * 8)) - 1
  if value < n:
    b = value.to_bytes(fieldSize, 'little')
    stream.write(b)
  else:
    b = n.to_bytes(fieldSize, 'little')
    stream.write(b)
    b = value.to_string()
    stream.write(b)
    stream.write(b'\x00')

def readBciIndexCount(stream):
  """read a channel or element index, ignoring the actual indices"""
  s = readLine(stream, b' ')
  if s == '{':
    n = 0
    s = readLine(stream, b' ')
    while s != '}':
      n += 1
      s = readLine(stream, b' ')
  else:
    n = int(s)
  return n

def readBciIndexList(stream):
  """obtain the list of values"""
  v = []
  s = readLine(stream, b' ')
  if s == '{':
    s = readLine(stream, b' ')
    while s != '}':
      v.append(s.replace('%20', ' '))
      s = readLine(stream, b' ')
  else:
    v = range(1, int(s)+1)
  return v

def readBciPhysicalUnit(stream):
  """read the members of a physical unit from a stream"""
  pu = Object()
  pu.offset = float(readLine(stream, b' '))
  pu.gain = float(readLine(stream, b' '))
  pu.unit = readLine(stream, b' ')
  pu.rawMin = float(readLine(stream, b' '))
  pu.rawMax = float(readLine(stream, b' '))
  return pu

def readBciSourceIdentifier(stream):
  """read a BCI2000 source identifier from a stream"""
  b = stream.read(1)
  if b != b'\xff':
    return str(b[0])
  return readLine(stream, b'\x00')

def readBciRawMessage(stream):
  """read a full raw BCI2000 message from a stream"""
  descsupp = stream.read(2) # get descriptor and descriptor supplement
  if descsupp == b'':
    raise EOFError()
  if len(descsupp) != 2:
    raise RuntimeError('Could not read descriptor fields')
  messageLength = readBciLengthField(stream, 2)
  chunks = []
  bytesRead = 0
  while bytesRead < messageLength:
    chunk = stream.read(min(messageLength - bytesRead, 2048))
    if chunk == b'':
      raise EOFError()
    chunks.append(chunk)
    bytesRead = bytesRead + len(chunk)
  return descsupp, b''.join(chunks)

def parseBciSignalProperties(stream):
  """parse a raw signal properties message into an object"""
  sp = Object()
  sp.kind = 'SignalProperties'
  sp.sourceID = readBciSourceIdentifier(stream)
  sp.name = readLine(stream, b' ')
  #sp.channels = readBciIndexCount(stream)
  sp.chNames = readBciIndexList(stream)
  sp.elements = readBciIndexCount(stream)
  sp.type = readLine(stream, b' ')
  sp.channelUnit = readBciPhysicalUnit(stream)
  sp.elementUnit = readBciPhysicalUnit(stream)
  return sp

def parseBciSignalData(stream):
  """parse a raw signal data message into an object"""
  signal = Object()
  signal.kind = 'Signal'
  signal.sourceID = readBciSourceIdentifier(stream)
  signal.type = ord(stream.read(1))
  signal.channels = readBciLengthField(stream, 2)
  signal.elements = readBciLengthField(stream, 2)
  signal.shm = readLine(stream, b'\x00')

  if signal.channels != 0 and signal.elements != 0:
    if signal.type & 64 == 0:
      raise RuntimeError('Signal data not located in shared memory')
    signal.type = signal.type & ~64
    if signal.type == 0:
      signal.type = 'int16'
    elif signal.type == 1:
      signal.type = 'float24'
    elif signal.type == 2:
      signal.type = 'float32'
    elif signal.type == 3:
      signal.type = 'int32'
    else:
      raise RuntimeError('Invalid signal type')
    if platform.system() == 'Windows':
      signal.shm = signal.shm.split("/")[1]

  return signal

def parseBciParameter(stream):
  """parse a raw parameter message into an object"""
  param = Object()
  param.kind = 'Parameter'
  param.param = ParseParam(stream) #uses BCI2kReader function
  #param = Object()

  return param

def parseBciSysCommand(stream):
  """parse a raw syscommand message into an object"""
  syscmd = Object()
  syscmd.kind = 'SysCommand'
  syscmd.command = readLine(stream, b'\x00')
  return syscmd

def receiveBciMessage(stream):
  """read and parse a single BCI2000 message from a stream"""
  descsupp, data = readBciRawMessage(stream)
  stream2 = io.BytesIO(data)
  if descsupp == BciDescSupp.SignalProperties.value:
    return parseBciSignalProperties(stream2)
  elif descsupp == BciDescSupp.SignalData.value:
    return parseBciSignalData(stream2)
  elif descsupp == BciDescSupp.Parameter.value:
    return parseBciParameter(stream2)
  elif descsupp == BciDescSupp.SysCommand.value:
    return parseBciSysCommand(stream2)
  else:
    raise RuntimeError('Unexpected BCI2000 message type')

def writeBciMessage(stream, descSupp, payload):
  """write a signal BCI2000 message to a stream"""
  stream.write(descSupp)
  length = len(payload)
  writeBciLengthField(stream, 2, length)
  stream.write(payload)
  stream.flush()

def writeBciStateMessage(stream, stateLine):
  """write a single BCI2000 state message to a stream"""
  writeBciMessage(stream, BciDescSupp.State.value, bytes(stateLine, 'utf-8') + b'\r\n')

def writeBciSysCommandMessage(stream, syscmd):
  """write a single BCI2000 sys command message to a stream"""
  writeBciMessage(stream, BciDescSupp.SysCommand.value, bytes(syscmd, 'utf-8') + b'\0')

def writeBciSignalMessage(stream, data):
  """write a numpy array's contents as a signal message to a stream"""
  stream2 = io.BytesIO()
  stream2.write(b'\xff' + bytes('Signal', 'utf-8') + b'\x00' + b'\x02')
  writeBciLengthField(stream2, 2, data.shape[0])
  writeBciLengthField(stream2, 2, data.shape[1])
  for ch in range(0, data.shape[0]):
    for el in range(0, data.shape[1]):
      stream2.write(struct.pack('<f', data[ch, el]))
  writeBciMessage(stream, BciDescSupp.SignalData.value, stream2.getvalue())
  stream2.close()
    


