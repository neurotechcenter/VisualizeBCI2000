# importing various libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import pyqtgraph.opengl as gl
import scipy.io

from base.SharedVisualization import Window, MyDockArea, TextOutput, Group
from PyQt5.QtCore import QObject, QThread, pyqtSignal
import threading

class BrainWorker(QObject):
  brainLoaded = pyqtSignal(object)
  elLoaded = pyqtSignal(dict)
  _progress = pyqtSignal(int) #progress 0-100
  def __init__(self, filename, rad, lock):
    super().__init__()
    self.filename = filename
    self.radius = rad
    self.lock = lock
  def run(self):
    #worker thread
    #load brainmat
    print("Loading 3d brain")
    self.lock.acquire()
    self.brainmat = scipy.io.loadmat(self.filename)
    mdl = self.brainmat['surfaceModel']
    verts = mdl['Model'][0][0]['vert'][0][0]
    faces = mdl['Model'][0][0]['tri'][0][0]
    faces -= 1 #change index from starting at 1 to starting at 0
    self._progress.emit(15)
    ###############
    a = mdl['Annotation'][0][0]
    aLabel = mdl['AnnotationLabel'][0][0]
    labelIDs = aLabel['Identifier'].ravel()
    pCol = aLabel['PreferredColor']
    #make sure labels are sorted
    _sorted = False
    if all(labelIDs[i] <= labelIDs[i+1] for i in range(len(labelIDs) - 1)):
      _sorted = True
    c = np.ones([np.shape(verts)[0], 4])*0.3 #change multiplier for opacity
    prog = 20
    updateFact = 10000 #slows down how often we update progress bar
    dp = 60/np.shape(verts)[0]*updateFact
    self._progress.emit(prog)
    for i in range(np.shape(verts)[0]):
      #create color array
      id = a[i][0]
      if _sorted:
        #much more efficient
        n = np.searchsorted(labelIDs, id)
      else:
        n = np.where(labelIDs == id)
        if not np.size(n) == 0:
          n = n[0][0]
      c[i,0:3] = (pCol[n][0]).ravel()
      if i % updateFact == 0:
        prog += dp
        self._progress.emit(int(prog))
    #################
    #load electrodes
    elecDef = self.brainmat['electrodes'][0][0]['Definition']
    nElectrodesPerLead = elecDef['NElectrodes']
    nLeads = np.shape(elecDef)[0]
    locs = self.brainmat['electrodes'][0][0]['Location']
    names = self.brainmat['electrodes'][0][0]['Name']
    self.electrodes = {} #empty dict
    elecCount = 0
    for i in range(nLeads):
      nElec = nElectrodesPerLead[i][0][0][0]
      for j in range(nElec):
        e = elecCount+j
        meshData = gl.MeshData.sphere(rows=10, cols=10, radius=self.radius)
        #use electrode name as key
        name = names[e][0][0]
        self.electrodes[name] = gl.GLMeshItem(meshdata=meshData, drawFaces=True, color=[0, 0, 0, 1])
        self.electrodes[name].active = False #set own property
        self.electrodes[name].translate(locs[e,0],locs[e,1],locs[e,2])
      elecCount += nElec
    self.elLoaded.emit(self.electrodes)
    self._progress.emit(90)

    #render brain
    p2 = gl.GLMeshItem(vertexes=verts, faces=faces, drawEdges=False, vertexColors=c, shader="balloon",
                        glOptions='translucent', computeNormals=True, smooth=False)
    self.brainLoaded.emit(p2)
    self._progress.emit(100)
    self.lock.release()

class BrainInitWorker(QObject):
  finished = pyqtSignal()
  def __init__(self, lock1, lock2):
    super().__init__()
    self.lock1 = lock1
    self.lock2 = lock2
    self.lock1.acquire()
    self.lock2.acquire()
  def run(self):
    #wait for brain to be loaded
    self.lock1.acquire()
    #wait for set config
    self.lock2.acquire()
    #finished!
    self.finished.emit()

#main window displaying 3d information in real-time
#updating is handled by master, updates when dataProcessedSignal is called 
class BrainWindow(Group):
  emitElectrodeNames = pyqtSignal(object) #dict
  class MyViewWidget(gl.GLViewWidget):
    def __init__(self, myParent, parent=None, devicePixelRatio=None, rotationMethod='euler'):
      super().__init__(parent, devicePixelRatio, rotationMethod)
      self.myParent = myParent
      self.loaded = False
    def mousePressEvent(self, event):
      if not self.loaded:
        #load brain
        print("LOAD BRAIN")
        self.loaded = self.myParent.loadBrain()
  
  def __init__(self, area):
    super().__init__(area)
  def publish(self):
    super().publish()
    self.activeEls = {}
    self.loadLock = threading.Lock()
    self.configLock = threading.Lock()
    self.layout = pg.LayoutWidget()
    #self.optionsD = Dock("Options")
    self.loadBut = pg.QtWidgets.QPushButton("Load brain")
    self.loadBut.clicked.connect(self.loadBrain)

    #scale slider to scale how much we change the radius of electrodes
    #slider is index to use for scaleMap (1-100%)
    self.scaleSlider = pg.QtWidgets.QSlider(pg.QtCore.Qt.Horizontal)
    self.scaleSlider.setMaximum(99)
    self.scaleSlider.setMinimum(0)
    self.scaleSlider.valueChanged.connect(self.changeScale)
    self.scaleMap = np.linspace(1e-3, 80e-3, 100)

    self.themes = [ColorScheme('black', [1,1,1,1], [0.3, 0.3, 0.3, 1]), #dark
                   ColorScheme('w', [0,0,0,0], [0.6, 0.6, 0.6, 1])]     #light
    self.themeBut = pg.QtWidgets.QPushButton("Toggle light/dark mode")
    self.themeBut.setCheckable(True)
    self.themeBut.clicked.connect(self.toggleTheme)

    #initialize brain view
    self.viewWidget = self.MyViewWidget(self, rotationMethod='quaternion')
    self.viewWidget.setCameraPosition(distance=200)
    self.layout.addWidget(self.viewWidget, rowspan=6, colspan=6)

    self.layout.addWidget(self.loadBut, row=7, col=0, colspan=3)
    self.layout.addWidget(self.themeBut, row=7, col=3, colspan=3)
    self.layout.addWidget(pg.QtWidgets.QLabel("Scaling Factor", objectName="h2"), row=8, col=0, colspan=1)
    self.layout.addWidget(self.scaleSlider, row=8, col=1, colspan=5)

    #self.area.addDock(Dock("Brain", widget=self.viewWidget), position='above', relativeTo=self.optionsD)

    #add text to tell user to load brain
    # griditem = gl.GLGridItem()
    # griditem.setSize(100, 100)
    # griditem.setSpacing(10, 10)
    # self.viewWidget.addItem(griditem)
    self.insrtTxt = gl.GLTextItem(pos=(-30, 0, 0), text="Click to load VERA brain")
    self.viewWidget.addItem(self.insrtTxt)

    #add dock
    self.dock = Dock("Brain", widget=self.layout)
    self.area.addDock(self.dock)


  def loadBrain(self):
    #ask for file name
    file_dialog = pg.QtWidgets.QFileDialog()
    file_dialog.setWindowTitle("Open File")
    file_dialog.setFileMode(pg.QtWidgets.QFileDialog.FileMode.ExistingFile)
    file_dialog.setViewMode(pg.QtWidgets.QFileDialog.ViewMode.Detail)
    file_dialog.setNameFilter("VERA mat file (*.mat)")
    if file_dialog.exec():
      #create progress bar
      self.progBar = pg.QtWidgets.QProgressBar()
      self.progBar.setValue(10)
      self.layout.addWidget(self.progBar, row=9, col=0, colspan=6)
      selected_files = file_dialog.selectedFiles()
    else:
      #file not chosen
      return False

    #file has been chosen
    self.insrtTxt.setVisible(False)
    #load brain
    self.radius = 1
    self.t = QThread()
    self.w = BrainWorker(selected_files[0], self.radius, self.loadLock)
    self.w.moveToThread(self.t)
    self.t.started.connect(self.w.run)
    self.w.brainLoaded.connect(self.brainLoaded)
    self.w.elLoaded.connect(self.electrodesLoaded)
    self.w._progress.connect(self.progSignalAccept)
    self.t.start()
    return True

  def toggleTheme(self, checked):
    self._theme = checked
    self.colorScene()

  def colorScene(self):
    self.viewWidget.setBackgroundColor(self.themes[self._theme].backgroundC)
    if hasattr(self, 'w'):
      if len(self.activeEls):
        for el in self.w.electrodes.values():
          if el.active:
            c = self.themes[self._theme].elDynamicC
          else:
            c = self.themes[self._theme].elStaticC
          el.setColor(c)
      else:
        #since channels haven't been loaded yet, make all of them actively visible
        for el in self.w.electrodes.values():
          el.setColor(self.themes[self._theme].elDynamicC)

  def loadSettings(self):
    super().loadSettings()
    self._scale = self.settings.value("scale", 50)
    self.scaleSlider.setValue(self._scale)
    self._theme = eval(self.settings.value("theme", "False").lower().capitalize())
    self.themeBut.setChecked(self._theme)
    self.viewWidget.setBackgroundColor(self.themes[self._theme].backgroundC)

  def saveSettings(self):
    super().saveSettings()
    
    self.settings.setValue("scale", self._scale)
    self.settings.setValue("theme", self._theme)

  def progSignalAccept(self, msg):
    self.progBar.setValue(int(msg))
    if self.progBar.value() == 100:
      #done
      self.progBar.setVisible(False)
      self.loaded = True
  
  def changeScale(self, val):
    self._scale = val
  def brainLoaded(self, mesh):
    self.viewWidget.addItem(mesh)
    print("brain loaded")
    #QApplication.restoreOverrideCursor()
  def electrodesLoaded(self, elMeshes):
    for el in elMeshes:
      self.viewWidget.addItem(elMeshes[el])
      elMeshes[el].setColor(self.themes[self._theme].elDynamicC)

  ###--slots--###
  def setConfig(self, chNames):
    print("setting config")
    self.chNames = chNames
    if self.configLock.locked():
      #first time we pressed set config
      self.configLock.release()
    elif not self.loadLock.locked():
      #otherwise, if loaded, go directly to slot
      self.readyForConfig()

  def plot(self, data):
    print("plotting brain...")
    if not self.activeEls:
      return
    for name, i in zip(self.activeEls, range(len(self.prevRadius))):
      dr = data[i] * self.scaleMap[self._scale]  / self.prevRadius[i]
      if dr == 0:
        dr = 1e-5 / self.prevRadius[i] #manually set small radius
      self.activeEls[name].scale(dr, dr, dr)
      self.prevRadius[i] *= dr
  ######
  
  def readyForConfig(self):
    print("READY FOR CONFIG")
    if not hasattr(self, 'chNames'):
      #we are quitting prematurely
      return
    #brain has been loaded, and ready to initialize
    #initialize working array of updating channels
    self.activeEls = {}
    #match up channel names with electrode labels
    keyStr = 'electrodeNamesKey'
    try:
      key = self.w.brainmat[keyStr]
    except:
      self.logPrint(f'VERA struct does not have \'{keyStr}\'. Cannot convert BCI2000 channel names to VERA electrode names')
      return
    #set up dict for quick access
    namesDict = {}
    for i in range(len(key)):
      if not key['VERANames'][i]:
        #empty VERAName, channel not an electrode
        v = False
      else:
        v = key['VERANames'][i][0][0]
      namesDict[key['EEGNames'][i][0][0]] = v
    #get electrodes in which the channels are shared
    n = 0
    invalN = 0
    for ch in self.chNames:
      if namesDict.get(ch) == None:
        invalN += 1
        continue
      if not namesDict[ch]:
        continue #channel not an electrode
      self.w.electrodes[namesDict[ch]].active = True
      self.activeEls[ch] = self.w.electrodes[namesDict[ch]]
      n+=1
    if n == 0:
      self.logPrint("No electrodes were found. Electrodes will not be updated")
    elif n == 1:
      self.logPrint("1 electrode found. 'TransmitChList' might be set to 1")
    else:
      self.logPrint(f'Connected to {n} electrodes')
    if invalN > 0:
      self.logPrint(f'Found {invalN} invalid channel names. Make sure correct VERA struct has been loaded')
    
    #update electrode colors
    self.colorScene()
    #emit names
    self.emitElectrodeNames.emit(namesDict)

    #reset electrode radii
    if hasattr(self, 'prevRadius'):
      for name, rad in zip(self.activeEls, self.prevRadius):
        self.activeEls[name].scale(self.radius/rad, self.radius/rad, self.radius/rad)
    self.prevRadius = np.ones(len(self.activeEls))*self.radius

class ColorScheme():
  def __init__(self, background, dynamicElectrodes, staticElectrodes):
    self.backgroundC = background
    self.elDynamicC = dynamicElectrodes
    self.elStaticC = staticElectrodes