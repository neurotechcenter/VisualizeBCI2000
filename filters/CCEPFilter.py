# importing various libraries
import numpy as np
from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import pyqtgraph.parametertree as ptree
from filters.filterBase.GridFilter import GridFilter
from base.SharedVisualization import saveFigure
from enum import Enum
from scipy.signal import find_peaks, butter, filtfilt
from math import ceil

backgroundColor = (14, 14, 14)
highlightColor = (60, 60, 40)
highZValue = 1000

class Column(Enum):
  Name = 0
  Electrode = 1
  Sig = 2
  AUC = 3
class RefCombo(Enum):
  Average = 0
  Maximum = 1

class Filter():
  enabled = False
  cutOff = None
  b = 0
  a = 0
  def __init__(self, name):
    self.type = name


class FigureParameterItem(ptree.parameterTypes.WidgetParameterItem):
  def makeWidget(self):
    self.asSubItem = True #places it in 2nd column
    w = pg.PlotWidget(title="Detection Output")
    w.setMinimumSize(100,100)
    w.sigChanged = w.sigRangeChanged 
    w.value = w.getPlotItem
    w.setValue = w.setCentralItem
    self.hideWidget = False
    return w

class FigureParameter(ptree.Parameter):
  itemClass = FigureParameterItem
  def __init__(self, **opts):
    super().__init__(**opts)

class ScalableGroup(ptree.parameterTypes.GroupParameter):
  def __init__(self, p, **opts):
    opts['type'] = 'group'
    ptree.parameterTypes.GroupParameter.__init__(self, **opts)
    self.p = p

    #enable/disable
    self.addChild({'name': 'Enable auto-detection', 'type': 'bool', 'value': 0})
    self.a = self.param('Enable auto-detection')
    self.a.sigValueChanged.connect(self.aChanged)
    #choose detection channel behavior
    chOptionsList = ptree.parameterTypes.ListParameter(name='Combination Options', limits=[opt.name for opt in RefCombo])
    self.addChild(chOptionsList)
    self.c = chOptionsList
    self.c.sigValueChanged.connect(self.cChanged)
    #custom fig param
    ptree.registerParameterType("fig", FigureParameter)
    self.fig  = FigureParameter(name="Peak Detection Plot")
    self.addChild(self.fig)

    #text box for displaying selected channels
    self.selTextBox = ptree.parameterTypes.TextParameter(name='Selected Channels', readonly=True)
    self.addChild(self.selTextBox)
    #checklist for detection channels
    self.chGroup = ptree.parameterTypes.ChecklistParameter(name='Detection Channels')
    self.addChild(self.chGroup)
    self.chGroup.sigValueChanging.connect(self.checkChanged)
    self.chGroup.sigValueChanged.connect(self.checkChanged)
    self.chList = []

  def aChanged(self):
    self.p.setAutoDetect(self.a.value())
  def cChanged(self):
    self.p.setRefChOptions(self.c.value())
  def checkChanged(self, val, ev):
    if self.chList != ev:
      self.chList = ev
      if len(ev)>0:
        listStr = ev[0]
        for el in ev[1:]:
          listStr += ", " + str(el)
      else:
        listStr = ""
      self.selTextBox.setValue(listStr)

class FilterParams(ptree.parameterTypes.GroupParameter):
  def __init__(self, p, **opts):
    self.p = p
    ptree.parameterTypes.GroupParameter.__init__(self, **opts)

    self.lp = ptree.parameterTypes.ListParameter(name="Low Pass", limits= [None, 30, 40, 70])
    #self.lp.sigValueChanged.connect(self.p.filterChanged)
    self.addChild(self.lp)

    self.hp = ptree.parameterTypes.ListParameter(name="High Pass", limits= [None, 0.1, 1, 5])
    #self.hp.sigValueChanged.connect(self.p.filterChanged)
    self.addChild(self.hp)

    self.notch = ptree.parameterTypes.ListParameter(name="Notch", limits= [None, 50, 60])
    #self.notch.sigValueChanged.connect(self.p.filterChanged)
    self.addChild(self.notch)


class TestBooleanParams(ptree.parameterTypes.GroupParameter):
  def __init__(self, p, **opts):
    self.p = p
    ptree.parameterTypes.GroupParameter.__init__(self, **opts)
    self.addChild({'name': 'Sort channels', 'type': 'bool', 'value': 0})
    self.a = self.param('Sort channels')
    self.a.sigValueChanged.connect(self.aChanged)

    self.addChild({'name': 'Average CCEPS', 'type': 'bool', 'value': 0})
    self.b = self.param('Average CCEPS')
    self.b.sigValueChanged.connect(self.bChanged)

    self.addChild({'name': 'Threshold (STD)', 'type': 'slider', 'value': 2, 'span': np.linspace(0, 10, 100)})
    self.c = self.param('Threshold (STD)')
    #self.c.sigValueChanged.connect(self.cChanged)
    
    self.addChild({'name': 'Max Windows', 'type': 'int', 'value': 16, 'limits': [0, 100]})
    self.d = self.param('Max Windows')
    self.d.sigValueChanged.connect(self.dChanged)
            
    self.addChild({'name': 'Save Figures on Refresh', 'type': 'bool', 'value': 0})
    self.f = self.param('Save Figures on Refresh')
    self.f.sigValueChanged.connect(self.fChanged)
    
    self.addChild({'name': 'Save Figures', 'type': 'action'})
    self.g = self.param('Save Figures')
    self.g.sigActivated.connect(self.gChanged)

    self.addChild({'name': 'Clear Figures', 'type': 'action'})
    self.h = self.param('Clear Figures')
    self.h.sigActivated.connect(self.hChanged)

  def aChanged(self):
    self.p.setSortChs(self.a.value())
  def bChanged(self):
    self.p.setAvgPlots(self.b.value())
  def cChanged(self):
    self.p.setStdDevState(self.c.value())
  def dChanged(self):
    self.p.setMaxWindows(self.d)
  def eChanged(self):
    self.p.setMaxPlots(self.e)
  def fChanged(self):
    self.p.setSaveFigs(self.f.value())
  def gChanged(self):
    self.p.saveFigures()
  def hChanged(self):
    self.p.clearFigures()

class CCEPFilter(GridFilter):
  def __init__(self, area, bciPath, stream):
    super().__init__(area, bciPath, stream)
    self.aucThresh = 0
    self.numTrigs = 0


  def publish(self):
    super().publish()

    self.pens = [pg.mkPen(x) for x in np.linspace(0, 1, 256)] #create all the pens we could ever need
    self.gridNums = pg.GraphicsLayoutWidget(title="CCEP Aggregate")
    self.table = QtWidgets.QTableWidget()

    settingsD = Dock("Settings")
    settingsLab = QtWidgets.QLabel("Settings", objectName="h1")

    #create parameter tree
    self.autoParam = ScalableGroup(name="Auto Detect Options", p=self, tip='Click to add channels', readonly=False)
    self.filterParams = FilterParams(name="Filters", p=self)
    params = [
        TestBooleanParams(name= 'General Options', p=self, showTop=False),
        self.filterParams,
        self.autoParam
    ]

    self.p = ptree.Parameter.create(name="Settings", type='group', children=params, title=None)
    self.t = ptree.ParameterTree()
    self.t.setParameters(self.p)

    self.t.header().setSectionResizeMode(pg.QtWidgets.QHeaderView.Stretch)
    settingsD.addWidget(settingsLab)
    settingsD.addWidget(self.t)

    d2 = Dock("Table", widget=self.table)
    self.area.addDock(settingsD)
    self.area.addDock(d2, position='above', relativeTo=settingsD)
    self.area.addDock(Dock("Plots", widget=self.gridPlots), position='above', relativeTo=d2)

  def loadSettings(self):
    super().loadSettings()
    self._stds = self.settings.value("stds", 5)

    self._maskStart = self.settings.value("maskStart", -5)
    self._maskEnd = self.settings.value("maskEnd", 15)

    #pState = self.settings.value("pState", {})

    #if pState != {}:
    #  self.p.restoreState(pState, addChildren=False, removeChildren=False)
    self._maxWindows = self.p.child('General Options')['Max Windows']
    self._sortChs = self.p.child('General Options')['Sort channels']
    self._comboOpt = RefCombo[self.p.child('Auto Detect Options')['Combination Options']]

  def saveSettings(self):
    super().saveSettings()

    self.settings.setValue("maskStart", self._maskStart)
    self.settings.setValue("maskEnd", self._maskEnd)
    #delete detection graph before saving
    try:
      self.autoParam.fig.remove()
    except:
      pass
    self.settings.setValue("pState", self.p.saveState())

  #an attempt to abstract plotting from BCI2000
  def checkPlot(self):
    return self.comm.evaluate("CCEPTriggered")
  
  #define shared states we need for filter
  @property
  def sharedStates(self):
    return ["CCEPTriggered", "StimulatingChannel"]
  
  #define abstract methods
  def receiveStates(self, state):
    #get CCEPTriggered state to detect CCEPs
    self.numTrigs += np.count_nonzero(state[0])

    #find stim ch if possible
    if np.shape(state)[0] > 1:
      stimCh = state[1].nonzero()[0]
      if stimCh.any():
        #just get first non-zero value
        chBits = state[1][stimCh[0]]
        testStimChs = []
        chBinary = '{0:08b}'.format(chBits)
        for b in range(len(chBinary)): #32 bit state
          if chBinary[len(chBinary) - b - 1] == '1':
            #print(self.chNames[b] + " at " + str(b))
            testStimChs.append(self.chNames[b]) #append ch name
        #minimally change used array
        if testStimChs != self.stimChs:
          self.stimChs = testStimChs

  
  def plot(self, data):
    #if self.checkPlot():
    if self.numTrigs > 0:
      print(f"plotting {self.numTrigs}")
      self.numTrigs -= 1

      #process data
      aocs = []
      chunk = False
      peaks = None
      if self.p.child('Auto Detect Options')['Enable auto-detection']:
        #get channels to use as trigger
        if not self.autoParam.chList:
          self.logPrint("Cannot auto-detect peaks without a detection channel!")
        else:
          refIndices = []
          try:
            for ch in self.autoParam.chList:
              refIndices.append(self.chNames.index(ch))
          except:
            self.logPrint("Detection chs have an invalid channel name")
          if len(refIndices) == 0:
            self.logPrint('Cannot auto-detect without Detection Channels specified!')
          else:
            if self._comboOpt == RefCombo.Average:
              self.trigData =  np.mean(data[refIndices, :],axis=0)
            elif self._comboOpt == RefCombo.Maximum:
              self.trigData = np.max(data[refIndices, :], axis=0)
            #remove mean before peak detection
            self.trigData -= np.mean(self.trigData)

            #get chunks by peaks
            #hard code parameters just to test
            peaks, properties = find_peaks(self.trigData, 200, width=(None,20), threshold=20, distance=20)
            print(f"Found {len(peaks)} peaks")
            if len(peaks) <= 1:
              chunk = False
            else:
              chunk = True

            #plot detection plot
            pltItem = self.autoParam.fig.value()
            pltItem.clear()
            for peak in peaks:
              pltItem.addLine(x=self.detectX[peak], pen={'color': "#d94350", 'width': 3})
            pltItem.plot(x=self.detectX, y=self.trigData)
            self.autoParam.fig.setValue(pltItem)
      
      #compute and chunk data
      avgPlots = self.p.child('General Options')['Average CCEPS']
      for i, ch in enumerate(self.chTable.values()):
        if chunk:
          ch.chunkData(data[i], peaks, avgPlots) #chunks and computes
        else:
          ch.computeData(data[i], avgPlots) #compute data
        aocs.append(ch.auc)
      
      #send processed data
      self.dataProcessedSignal.emit(aocs)

      #set threshold
      stds = self.p.child('General Options')['Threshold (STD)']
      self.aucThresh = np.std(aocs) * stds

      #plot!
      self._renderPlots()

  def setConfig(self):
    super().setConfig()

    self.gridNums.clear()

    self.chPlot = list(range(self.channels))
    self.tableRows = list(range(self.channels))
    #self.chPlot = {}
    self.chTable = {}
    self.regs = list(range(self.channels))
    #init variables
    self.baselineLength = self.getParameterValue("BaselineEpochLength")
    self.latStart = 0
    self.latStartSamples = self._maskStart
    self.ccepLength = self.getParameterValue("CCEPEpochLength")
    self.sr = self.getParameterValue("SamplingRate")
    self.baseSamples = self.msToSamples(self.baselineLength)
    self.ccepSamples = self.msToSamples(self.ccepLength)
    self.trigSamples = self._maskEnd 
    self.trigLatLength = self.trigSamples * 1000.0 / self.sr
    
    #redefine element size
    self.elements = self.baseSamples + self.ccepSamples
    self.x = np.linspace(-self.baselineLength, self.ccepLength, self.elements)

    #to visualize stimulating channels if we can
    self.stimChs = []
    #for filters
    self.filters = { 'Notch':  Filter('bandstop'), 'Low Pass': Filter('lowpass'), 'High Pass':  Filter('highpass')}
    self.filterValChanged = False
    for param in self.filterParams.children():
      param.sigValueChanged.connect(self.filterChanged)

    #go thru all channels for table
    count = 0
    for chName in self.chNames:
      sub1 = self.gridNums.addLayout()
      sub1.addLabel("<b>%s"%(chName), size='20pt', bold=True)

      sub1.nextRow()
      self.chTable[chName] = CCEPCalc(self, ch=count, title=chName)
      count = count + 1

    #only initialize plots up to max number 
    for r in range(self.numRows):
      for c in range(self.numColumns):
        ch = r*self.numColumns+c
        #print(self.chPlot)
        if ch < self.windows:
          chName = self.chNames[ch]
          self.chPlot[ch] = CCEPPlot(self, title=chName, row=self.chTable[chName])
          self.gridPlots.addItem(self.chPlot[ch])
          if ch != 0:
            self.chPlot[ch].setLink(self.chPlot[ch-1])
          else:
            self.chPlot[ch].showAxis('left')
            self.chPlot[ch].showAxis('bottom')
      self.gridPlots.nextRow()
    
    #give first plot a friend
    if self.windows > 1:
      self.chPlot[0].friend = self.chPlot[self.windows-1] #give first plot a friend
    
    #table
    self.table.setRowCount(self.channels)
    self.table.setColumnCount(len(Column))
    self.table.setHorizontalHeaderLabels([c.name for c in Column])
    for ch, chName in enumerate(self.chNames):
      c = ch % self.numColumns
      r = int(np.floor(ch/self.numColumns))
      #add table
      if self.elecDict:
        eName = self.elecDict[chName]
      else:
        eName = ""
      self.tableRows[ch] = TableRow(ch, r, c, self.chPlot[ch], chName, eName, self.channels)
      self.tableRows[ch].addRow(self.table)
      
      if ch < self.windows:
        self.chPlot[ch].setRow(self.tableRows[ch]) #link plot to row
    
    #finish table
    if not self.elecDict:
      self.table.setColumnHidden(Column.Electrode.value, True) #hide electrode name col
    else:
      self._hideNonElectrodes()
    self.table.resizeColumnsToContents()
    #self.table.setSortMode(0,'index')
    self.table.sortItems(0, QtCore.Qt.DescendingOrder)
    for i, chName in enumerate(self.chNames):
      self.chTable[chName].setTableItem(i)
    #self.setSortChs(self._sortChs)
    #make sure user can't change sorting
    for i in range(self.table.columnCount()):
      h = self.table.horizontalHeaderItem(i)
      #h.setFlags(h.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
      self.table.setHorizontalHeaderItem(i, h)
    # print(self.table.horizontalHeaderItem(1).text())
    self.selectedRows = []
    #self.table.itemClicked.connect(self.tableItemClickedCallback)
    self.table.itemSelectionChanged.connect(self._selectionChanged)
    #self.table.itemChanged.connect(self._itemChanged)

    #set parameter tree
    self.autoParam.chGroup.setLimits(self.chNames)
    #set detection plot with settings
    pltItem = self.autoParam.fig.value()
    #prepare view
    axView = pltItem.getViewBox()
    axView.disableAutoRange()
    #axView.setMouseEnabled(x=False, y=True)
    axView.setDefaultPadding(0)
    xLim = self.getParameterValue("PreStimLength")
    yLim = self.getParameterValue("PostStimLength")
    #redefine element size
    self.detectX = np.linspace(-xLim, yLim, self.msToSamples(xLim) + self.msToSamples(yLim))
    axView.setXRange(-xLim, yLim, padding=0)
    axView.setYRange(-1000, 1000)
    #set it back after adjustments
    self.autoParam.fig.setValue(pltItem)

  def setStdDevState(self, value):
    self._stds = value
    #self.stdSpin.setToolTip(str(value/10))
  def setMaxWindows(self, spin):
    self._maxWindows = spin.value()
  def setAvgPlots(self, state):
    self._avgPlots = state
  def setSortChs(self, state):
    if hasattr(self, 'chTable') and self._sortChs and not state:
      #re-initialize order
      for ch in self.chTable.values():
        ch.totalChanged(False)
      self.table.sortItems(Column.Name.value, QtCore.Qt.DescendingOrder)
    
    self._sortChs = state
    #plot everything again with original order
    if hasattr(self, 'chTable'):
      self._renderPlots(newData=False)
  def setSaveFigs(self, state):
    self._saveFigs = state
  def setAutoDetect(self, state):
    self._autoDetect = state
  def setRefChOptions(self, val):
    self._comboOpt = RefCombo[val]
      
  def msToSamples(self, lengthMs):
    return int(ceil(lengthMs * self.sr/1000.0))

  def updateParameter(self, latStart, newLat):
    if newLat != self.trigLatLength:
      self.trigLatLength = newLat
      self.trigSamples = self.msToSamples(newLat)
      self._maskEnd = self.latStartSamples + self.trigSamples
    if latStart != self.latStart:
      self.latStart = latStart
      self.latStartSamples = self.msToSamples(latStart)
      self._maskStart = self.latStartSamples
  
  def clearFigures(self):
    if self.p.child('General Options')['Save Figures on Refresh']:
      self.saveFigures()
    for i in range(0, self.windows):
      children = self.chPlot[i].listDataItems()
      for child in children[1:]: #save first plot
        self.chPlot[i].removeItem(child)
    children[0].setPen(pg.mkPen('b')) #blend in

    for t in self.chTable.values():
      t.totalChanged(0)
      t.database = []
      t.rawDatabase = []
  
  def filterChanged(self, param, val):
    filter = self.filters[param.name()]
    #if val != filter.cutOff:
    filter.cutOff = val
    filter.enabled = val != None
    if filter.enabled:
      print("filter enabled")
      if filter.type == 'bandstop':
        f = np.array([filter.cutOff - 5, filter.cutOff + 5])
      else:
        f = filter.cutOff
      filter.b, filter.a = butter(2, f * 2 / self.sr , btype=filter.type)

    #change past data
    for ch in self.chTable.values():
      for i in range(np.size(ch.rawDatabase, 0)):
        ch.database[i] = ch.filterData(ch.rawDatabase[i])
      ch.data = np.mean(ch.database, axis=0)
    #display changes
    print("changing data")
    self.filterValChanged = True
    self._renderPlots()
    self.filterValChanged = False

  def lpChanged(self, p, val):
    print(val)
  def hpChanged(self, p, val):
    print(val)
  def notchChanged(self, p, val):
    print(val)

  def saveFigures(self):
    #beautiful hack
    #mimic minimal mouse click
    class Dummy():
      def __init__(self):
        acceptedItem = None
      def screenPos(self):
        return pg.QtCore.QPointF(0,0)

    if self.gridPlots.getItem(0,0) != None:
      scene = self.gridPlots.scene()
      if not hasattr(scene, "contextMenuItem"):
        vb = self.gridPlots.getItem(0,0).getViewBox()
        
        event = Dummy()
        event.acceptedItem = vb
        vb.raiseContextMenu(event)
      scene.showExportDialog()

    return
    saveFigure(self.gridPlots)
    
  def _renderPlots(self, newData=True):
    #update table with new data
    for ch in self.chTable.values():
      ch.totalChanged(ch.auc > self.aucThresh)
    
    #sort table with updated numbers, if toggled
    if self._sortChs:
      self.table.sortItems(Column.Name.value, QtCore.Qt.DescendingOrder)
    
    #plot
    i = 0
    for r in range(self.table.rowCount()):
      if i == self.windows:
        break
      if not self.table.isRowHidden(r):
        chName = self.table.item(r, Column.Name.value).text()
        chng = self.chPlot[i].checkForChange(chName, self.chTable[chName])
        if chng or self.filterValChanged:
          self.chPlot[i].changePlot()
        self.chPlot[i].plotData(newData)
        i+=1

  def _changeBackgroundColor(self, row, emph):
    if row >= self.windows:
      return
    c = backgroundColor
    if emph:
      c = highlightColor
    self.chPlot[row].vb.setBackgroundColor(c)
    chName = self.table.item(row,Column.Name.value).text()
    self.chPlot[row].selected = emph
    self.chTable[chName].selected = emph
  
  def _selectionChanged(self):
    items = self.table.selectedItems()
    newRows = []
    for p in items:
      if p.row() not in self.selectedRows:
        self._changeBackgroundColor(p.row(),True)
      newRows.append(p.row())
    for oldS in self.selectedRows:
      if oldS not in newRows:
        self._changeBackgroundColor(oldS, False)
    self.selectedRows = newRows

  ####---inherited slots---####
  def acceptElecNames(self, elecDict):
    super().acceptElecNames(elecDict)
    if hasattr(self, 'chTable'):
      for name in self.chNames:
        r = self.table.row(self.chTable[name].tableItem)
        self.table.item(r,Column.Electrode.value).setData(QtCore.Qt.DisplayRole, self.elecDict[name])
      self.table.setColumnHidden(Column.Electrode.value, False)
      self._hideNonElectrodes()
    else:
      #we haven't initialized table yet
      pass
  
  #if we have electrode names, we can hide channels that aren't electrodes
  def _hideNonElectrodes(self):
    if self.elecDict and hasattr(self, 'chTable'):
      for r in range(self.table.rowCount()):
        if self.table.item(r,Column.Electrode.value).text() == "":
          self.table.setRowHidden(r, True)
        else:
          self.table.setRowHidden(r, False)

class TableRow():
  class TableItem(QtWidgets.QTableWidgetItem):
    def __init__(self, p, parent=0):
      super().__init__(parent)
      self.p = p
      #make un-editable
      self.setFlags(self.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
      pass
    #define less than (<) operator for table sorting
    def __lt__(self, b):
      return (self.p.rank + self.p.sig*self.p.max) < (b.p.rank + b.p.sig*b.p.max)
  def __init__(self, i, row, col, fig, chName, elName, maxVal):
    self.plotR = row
    self.plotC = col
    self.rank = maxVal - i
    self.sig = 0
    self.max = maxVal
    self.oldRow = i
    self.chName = chName
    self.elName = elName
    self.figure = fig
  def getRowNumber(self):
    return self.n.row()
  def addRow(self, table):
    self.n = self.TableItem(self, self.chName) #save order as rank
    s = self.TableItem(self)
    a = self.TableItem(self)
    e = self.TableItem(self, self.elName)

    table.setItem(self.oldRow, Column.Name.value, self.n)
    table.setItem(self.oldRow, Column.Electrode.value, e)
    table.setItem(self.oldRow, Column.Sig.value, s)
    table.setItem(self.oldRow, Column.AUC.value, a)

class CCEPPlot(pg.PlotItem):
  def __init__(self, parent, title, row):
    super().__init__(title=title)
    self.p = parent
    self.name = title
    self.link = row
    self.selected = False
    self.tableRow = None
    #prepare view
    axView = self.getViewBox()
    axView.disableAutoRange()
    axView.setMouseEnabled(x=False, y=True)
    axView.setDefaultPadding(0)
    xLim = -self.p.baselineLength
    yLim = self.p.ccepLength
    axView.setXRange(xLim, yLim, padding=0)
    axView.setYRange(-1000, 1000)

    self.setMinimumSize(100,100)

    #stim artifact filter
    self.latLow = self.p.latStartSamples*1000.0/self.p.sr
    self.latHigh = self.p.trigLatLength
    self.latReg = pg.LinearRegionItem(values=(self.latLow, self.latHigh), movable=True, brush=(9, 24, 80, 100), 
                                      pen=pg.mkPen(color=(9, 24, 80), width=1, style=QtCore.Qt.DotLine), bounds=[xLim, yLim])
    self.latReg.setZValue(highZValue) #make sure its in front of all plots
    #callbacks
    self.latReg.sigRegionChanged.connect(self.regionChanged)
    self.addItem(self.latReg)

    #initialize average plot
    self.avg = self.plot(x=self.p.x, y=np.zeros(self.p.elements), pen=pg.mkPen(backgroundColor)) #filler data
    self.avg.setZValue(highZValue-1) #behind filter region, in front of every other plot

    #self.backgroundC = (14, 14, 14)
    self.vb.setBackgroundColor(backgroundColor)
  def setRow(self, row):
    self.tableRow = row
  
  def setLink(self, plt):
    self.friend = plt #each plot gets one friend they affect
    self.getViewBox().setYLink(self.friend.getViewBox())

  def regionChanged(self, reg):
    newReg = reg.getRegion()
    self.latHigh = newReg[1]
    self.latLow = newReg[0]
    if self.latHigh != self.friend.latHigh or self.latLow != self.friend.latLow:
      self.p.updateParameter(self.latLow, self.latHigh) 
      self.friend.latReg.setRegion(reg.getRegion())
  
  def checkForChange(self, name, link):
    #have we changed channels
    if self.name != name:
      self.setTitle(name)
      self.name = name
      self.link = link #update link
      return True
  def changePlot(self):
    if len(self.link.database) > 0:
      #change data of all plots but average
      for f, d in zip(self.listDataItems()[1:], self.link.database):
        f.setData(x=self.p.x, y=d, useCache=True)
      self.updateAveragePlot()

    #change background based on selected
    if self.selected and not self.link.selected:
      self.vb.setBackgroundColor(backgroundColor)
      self.selected = False
    elif not self.selected and self.link.selected:
      self.vb.setBackgroundColor(highlightColor)
      self.selected = True

  #plot: new name and link is only considered if we are dynamically sorting
  def plotData(self, newData, maxPlots=0):
    if newData:
      children = self.listDataItems() #all plots
      
      if len(self.link.database) > len(children):
        #update plots with newly computed data (will be true if chunking)
        newPlots = len(self.link.database) - len(children)
        #print("new plots: " + str(newPlots))
        for i in range(newPlots):
          self.plot(x = self.p.x, y = self.link.database[-i - 1])

      expColors = [(255) * (1 - 2**(-x)) for x in np.linspace(0+1/(len(children)+1), 1-1/(len(children)+1), len(children))]
      for child, c in zip(children[1:], expColors):
        child.setPen(self.p.pens[int(c)])

      #plot new data
      p2 = 255*(1-2.5**(-1*(1-1/(len(self.link.database)+1))))
      self.plot(x=self.p.x, y=self.link.database[-1], useCache=True, pen=self.p.pens[int(p2)], _callSync='off')

      self.updateAveragePlot()
    
  def updateAveragePlot(self):
    #update average plot
    if self.link.significant:
      p = pg.mkPen('y', width=1.5) #ccep!
    else:
      p = pg.mkPen('w', width=1.5)
    if self.name in self.p.stimChs:
      p = pg.mkPen('c', width=1.5)
    self.avg.setData(x=self.p.x, y=self.link.data, useCache=True, pen=p)

class CCEPCalc():
  def __init__(self, parent, ch, title):
    self.p = parent
    self.ch = ch
    self.name = title

    self.significant = False
    self.selected = False
    self.database = []
    self.rawDatabase = []
    self.auc = 0
    self.data = np.zeros(self.p.elements)

  def getActiveData(self, data):
    p1 = data[:self.p.baseSamples+self.p.latStartSamples]
    p2 = data[self.p.baseSamples+self.p.trigSamples:]
    d = np.concatenate((p1, p2))
    #print(np.shape(d))
    return p2

  def setTableItem(self, ch):
    self.tableItem = self.p.table.item(ch,Column.Name.value)

  #t = boolean, if significant or not
  def totalChanged(self, t):
    empColor = pg.QtGui.QColor(56,50,0)
    self.tableItem.p.sig = t
    r = self.p.table.row(self.tableItem) #find new row we are at
    self.p.table.item(r,Column.Sig.value).setData(QtCore.Qt.DisplayRole, int(t))
    self.p.table.item(r,Column.AUC.value).setData(QtCore.Qt.DisplayRole, int(self.auc))
    self.significant = t

    if self.significant and self.tableItem.background() != empColor:
      self.tableItem.setBackground(empColor)
    elif not self.significant and self.tableItem.background() == empColor:
      self.tableItem.setBackground(pg.QtGui.QColor(0,0,0,0)) #transparent

  def computeData(self, newData, avgPlots=True):        
    #new data, normalize amplitude with baseline data
    if self.p.baseSamples == 0:
      self.data = newData
      #stdBase = 0
    else:
      #avBase = np.mean(newData[:self.p.baseSamples])
      avBase = np.median(newData[:self.p.baseSamples])
      #stdBase = np.std(self.rawData[:self.p.baseSamples], dtype=np.float64)
      self.data = np.subtract(newData, avBase)


    if np.shape(self.data) != np.shape(self.p.x):
      self.p.logPrint(f"Expected: {np.shape(self.p.x)}, received: {np.shape(self.data)}")
    else:
      #store data
      self.rawDatabase.append(self.data.copy())

      #filter if enabled
      self.data = self.filterData(self.data)
      # for filter in self.p.filters:
      #   if filter.enabled:
      #     self.data = filtfilt(filter.b, filter.a, self.data)

      self.database.append(self.data.copy())

    #possibly change to average, before we detect ccep
    if avgPlots:
      #calculate average of plots
      self.data = np.mean(self.database, axis=0)
    
    #get area under the curve
    ccepData = self.getActiveData(self.data)
    normData = ccepData - np.mean(ccepData)
    self.auc = np.trapz(abs(normData))/1e3

  def filterData(self, data):
    for filter in self.p.filters.values():
      if filter.enabled:
        data = filtfilt(filter.b, filter.a, data)
    return data

  def chunkData(self, newData, peaks, avgPlots=True):
    for peak in peaks:
      data = newData[peak - self.p.baseSamples : peak + self.p.ccepSamples]
      self.computeData(data, avgPlots)

