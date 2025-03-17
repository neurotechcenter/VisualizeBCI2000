import socket
from select import select
from multiprocessing import shared_memory
import numpy as np
import sys
import io
import struct
import traceback
import platform
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from base.BCI2kReaderMod import ParseParam
#
# Data acquisition thread from BCI2000's shared memory
# Acquires signals and states, their properties, and parameters
#

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

class AcquireDataThread(QObject):
  #QThread signal/slots 
  propertiesSignal = pyqtSignal(int, int, list) #ch, el, ch names
  dataSignal       = pyqtSignal(np.ndarray)
  parameterSignal  = pyqtSignal(object)
  disconnected     = pyqtSignal()
  logPrint = pyqtSignal(str)

  def __init__(self,):
    super(AcquireDataThread, self).__init__()
    self.go = True
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

  def initalizeAddress(self, address):
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
    self.logPrint.emit("Waiting for BCI2000 on %s at port %s" %(address[0], address[1]))
    self.s.settimeout(0.1)        
    
  def run(self):
    while self._isRunning:
      #listen for connection on specified port
      memoryName = ""
      try:
        self.waitForRead(self.s)
        conn, addr = self.s.accept()
        self.logPrint.emit(f"Connected by {addr}")
        stream = conn.makefile('rb')
        while self._isRunning: #go until we receive an EOFError exception
          QThread.usleep(1) #use sleep to not get stuck waiting for read
          self.waitForRead(conn)
          msg = receiveBciMessage(stream)
          
          if msg.kind == 'SignalProperties' and msg.sourceID == 'Signal':
            print("SIGNAL PROPERTIES")
            chs = len(msg.chNames)

            els = msg.elements
            self.propertiesSignal.emit(chs, els, msg.chNames)

          elif msg.kind == 'SignalProperties' and msg.sourceID == 'States':
            pass
          
          elif msg.kind == 'Signal' and msg.sourceID == 'Signal':
            if memoryName != msg.shm:
              # update shared memory object
              memoryName = msg.shm
              mem = shared_memory.SharedMemory(memoryName)
            
            #update visualization with new data
            data = np.ndarray((msg.channels, msg.elements),dtype=np.double, buffer=mem.buf)
            self.dataSignal.emit(data)

          elif msg.kind == 'Parameter':
            self.parameterSignal.emit(msg.param)
            continue

          elif msg.kind == 'Signal' and msg.sourceID == 'States':
            pass

          elif msg.kind == 'SysCommand' and msg.command == 'EndOfData':
            continue

          elif msg.kind == 'SysCommand' and msg.command == 'EndOfTransmission':
            print('end of transmission')
            continue

          else:
            raise RuntimeError('Unexpected BCI2000 message')

      except EOFError:
        print('disconnected')
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
    


