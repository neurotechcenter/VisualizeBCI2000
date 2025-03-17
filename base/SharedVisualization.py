# importing various libraries
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import os
from PyQt5.QtCore import pyqtSignal
from base.style import setStyle

# main window inherited by all GUIs.
# Children should call publish first to add GUI elements,
# then the style will be set and settings will be loaded
class Window(pg.QtWidgets.QMainWindow):
  closed = pyqtSignal()
  def __init__(self, **kargs):
    super().__init__(**kargs)
    self.publish() #load window
    setStyle(self)
    self.loadSettings() #set past config
  
  def publish(self):
    pass
    
  def closeEvent(self, event): #overrides QMainWindow closeEvent
    self.saveSettings()
    self.closed.emit() #to let main window know we closed
    super().closeEvent(event)
    
  def loadSettings(self):
    #load unique settings to window
    self.settings = pg.QtCore.QSettings("BCI2000", self.__class__.__name__)
    self.restoreGeometry(self.settings.value("geometry", pg.QtCore.QByteArray()))
    if hasattr(self, 'area'):
      self.area.restoreState(self.settings.value("dockConfig", {'main': None, 'float': []})) #default dock
  
  def saveSettings(self):
    self.settings.setValue("geometry", self.saveGeometry())
    if hasattr(self, 'area'):
      self.settings.setValue("dockConfig", self.area.saveState())

#inherit DockArea just to keep style for floating docks
class MyDockArea(DockArea):
  def __init__(self, parent=None, temporary=False, home=None):
    super().__init__(parent, temporary, home)
  def floatDock(self, dock):
    super().floatDock(dock)
    setStyle(dock)

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