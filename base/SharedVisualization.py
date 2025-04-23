# importing various libraries
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import os
from PyQt5.QtCore import pyqtSignal, QObject
from base.style import setStyle
import traceback

class Group(QObject):
  def __init__(self, win):
    super().__init__()
    self.win = win
    self.area = win.area
    self.publish()
    setStyle(win)
    self.loadSettings()
  def publish(self):
    pass
  def loadSettings(self):
    #load unique settings to window
    self.settings = pg.QtCore.QSettings("BCI2000", self.__class__.__name__)
  
  def saveSettings(self):
    pass

  def logPrint(self, msg):
    self.win.output.append(">>" + msg)
    self.win.output.moveCursor(pg.QtGui.QTextCursor.End)

# main window inherited by all GUIs.
# Children should call publish first to add GUI elements,
# then the style will be set and settings will be loaded
class Window(pg.QtWidgets.QMainWindow, Group):
  def __init__(self, **kargs):
    pg.QtWidgets.QMainWindow.__init__(self, **kargs)
    Group.__init__(self, self)
    
  def closeEvent(self, event): #overrides QMainWindow closeEvent
    self.saveSettings()
    super().closeEvent(event)
    
  def loadSettings(self):
    super().loadSettings()
    #load unique settings to window
    self.restoreGeometry(self.settings.value("geometry", pg.QtCore.QByteArray()))

    try:
      s = self.settings.value("dockConfig", {'main': None, 'float': []})
      if len(s['float']) == 0:
        self.area.restoreState(self.settings.value("dockConfig", {'main': None, 'float': []}), missing='ignore') #default dock
      else:
        #for some reason it breaks if it stored floating windows, so reset
        self.settings.setValue("dockConfig", {'main': None, 'float': []})

    except:
      print("Could not restore geometry. Using defaults...")
  
  def saveSettings(self):
    super().saveSettings()
    self.settings.setValue("geometry", self.saveGeometry())
    self.settings.setValue("dockConfig", self.area.saveState())

#inherit DockArea just to keep style for floating docks
class MyDockArea(DockArea):
  def __init__(self, parent=None, temporary=False, home=None):
    super().__init__(parent, temporary, home)

  def addTempArea(self):
    area = super().addTempArea()
    setStyle(area)
    return area

#Style text output for log
class TextOutput(pg.QtWidgets.QTextEdit):
  def __init__(self):
    super().__init__()
    self.setReadOnly(True)
    #self.setTextBackgroundColor(pg.QtGui.QColor(29,29,31))
    #self.setTextColor(pg.QtGui.QColor(255, 255, 255))
    self.setFontPointSize(11)
    self.ensureCursorVisible()  


#-----SAVING FIGURE------#
def saveFigure(myPrint, path, graphicsLayoutObj, suffix, ext='.png', antialias=True):
  newPath = _getPath(path)
  myPrint("Saving image at " + newPath + suffix + ext)
  if ext == '.svg':
    exporter = pg.exporters.SVGExporter(graphicsLayoutObj.ci)
  else:
    exporter = pg.exporters.ImageExporter(graphicsLayoutObj.ci)
    exporter.parameters()['antialias'] = antialias
  #double size to make image quality better
  #exporter.parameters()['width'] = exporter.parameters()['width'] * 2
  #exporter.parameters()['height'] = exporter.parameters()['height'] * 2
  exporter.export(_nonExistantFileName(newPath + suffix, ext) + ext)

########################
#### HELPER METHODS ####
########################
def _getPath(path):
  base = path
  #remove file type
  for i in range(len(path)-1, 0, -1):
    if base[i] == '.':
      base = base[:i]
      break
  #print(base)
  return _nonExistantFileName(base, '.dat')

#return file path with name, without an extension
def _nonExistantFileName(path, ext):
  #print(path)
  if path[-2:] == '00':
    path = path[:-1] + '1' #BCI2000 run numbers are never 00
  oldPath = path
  while os.path.isfile(path + ext):
    #print(path + ext + " is a file")
    #increment run number until we are not overwriting
    oldPath = path
    path = _changeName(path, -1)
  if ext == '.dat':
    path = oldPath #bc current dat file exists, but we want that number
  return path

def _changeName(path, index):
  #tries to match BCI2000 dat file name
  def getSuffix(path, index):
    if index+1 == 0:
      suf = ''
    else:
      suf = path[index+1:]
    return suf
  def replaceStr(path, index, v):
    newPath = path[:index] + str(v) + getSuffix(path, index)
    return newPath
  if path[index].isnumeric():
    if path[index] == '9':
      path = replaceStr(path, index, 0)
      path = _changeName(path, index - 1)
    else:
      path = replaceStr(path, index, int(path[index]) + 1)
  else:
    if index == -1:
      pre = path[::]
    else:
      pre = path[:index+1]
    path = pre + '1' + getSuffix(path, index) #add new digit
    #print(path)
  return path