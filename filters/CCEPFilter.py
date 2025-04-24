# importing various libraries
import numpy as np
from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
from pyqtgraph.dockarea import *
from filters.filterBase.GridFilter import GridFilter
from base.SharedVisualization import saveFigure
from enum import Enum

backgroundColor = (14, 14, 14)
highlightColor = (60, 60, 40)
highZValue = 1000

class Column(Enum):
  Name = 0
  Electrode = 1
  Sig = 2
  AUC = 3

class CCEPFilter(GridFilter):
  def __init__(self, area, bciPath, stream):
    super().__init__(area, bciPath, stream)
    self.aucThresh = 0
  def publish(self):
    super().publish()

    self.pens = [pg.mkPen(x) for x in np.linspace(0, 1, 256)] #create all the pens we could ever need
    self.gridNums = pg.GraphicsLayoutWidget(title="CCEP Aggregate")
    self.table = QtWidgets.QTableWidget()
    #title dock widgets
    clearButton = QtWidgets.QPushButton('Clear Figures')
    clearButton.clicked.connect(self.clearFigures)
    saveButton = QtWidgets.QPushButton('Save Figures')
    saveButton.clicked.connect(self.saveFigures)
    #settings dock widgets
    #choose std dev threshold
    self.stdSpin = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    #self.stdSpin = pg.SpinBox(int=True, compactHeight=True)
    self.stdSpin.setMaximum(10*10)
    self.stdSpin.setMinimum(0)
    self.stdSpin.valueChanged.connect(self.setStdDevState)
    stdLab = QtWidgets.QLabel("Threshold (STD)", objectName="h3")
    stdLab.setToolTip("Standard Deviations for threshold, calculated from baseline")
    #specifies where to start visualizing the signal
    self.baseSpin = pg.SpinBox(int=True, compactHeight=True)
    self.baseSpin.sigValueChanged.connect(self.setBaselineBegin)
    self.baseSpin.setToolTip("First value of x axis")
    baseLab = QtWidgets.QLabel('x<sub>0</sub>', objectName="h3")
    baseLab.setToolTip("First value of x axis")
    #max window number
    self.maxSpin = pg.SpinBox(int=True, compactHeight=True)
    self.maxSpin.setMaximum(100)
    self.maxSpin.setMinimum(0)
    self.maxSpin.sigValueChanged.connect(self.setMaxWindows)
    self.maxSpin.setToolTip("Maximum number of windows to show")
    maxLab = QtWidgets.QLabel("Max Windows", objectName="h3")
    maxLab.setToolTip("Maximum number of windows to show")
    #max plots
    self.holdSpin = pg.SpinBox(int=True, compactHeight=True)
    self.holdSpin.setMaximum(100)
    self.holdSpin.setMinimum(0)
    self.holdSpin.sigValueChanged.connect(self.setMaxPlots)
    self.holdSpin.setToolTip("Maximum plots to hold (0 to hold all)")
    holdLab = QtWidgets.QLabel("Hold Plots", objectName="h3")
    holdLab.setToolTip("Maximum plots to hold (0 to hold all)")
    #toggle to average every existing plot
    self.avgBut = QtWidgets.QCheckBox("Average CCEPs")
    self.avgBut.stateChanged.connect(self.setAvgPlots)
    self.avgBut.setToolTip("New plot will be average of all CCEPs")
    #sorting toggle
    self.sortBut = QtWidgets.QCheckBox("Sort channels")
    self.sortBut.stateChanged.connect(self.setSortChs)
    self.sortBut.setToolTip("Sort by number of CCEPs detected")
    #automatically saving figures toggle
    self.saveFigBut = QtWidgets.QCheckBox("Save figures on refresh")
    self.saveFigBut.stateChanged.connect(self.setSaveFigs)
    self.saveFigBut.setToolTip("Automatically save a .svg of the CCEPs when they are cleared/refreshed")


    settingsD = Dock("Settings")
    settingsLab = QtWidgets.QLabel("Settings", objectName="h1")
    settingsLab.setWordWrap(True)
    figuresLab = QtWidgets.QLabel("Figures", objectName="h1")
    #settingsD.addWidget(figuresLab, row=0, col=0,)
    settingsD.addWidget(saveButton, row=1, col=0)
    settingsD.addWidget(settingsLab, row=3, col=0, colspan=2)
    settingsD.addWidget(stdLab, row=4, col=0)
    settingsD.addWidget(self.stdSpin, row=5, col=0)
    settingsD.addWidget(maxLab, row=6, col=0)
    settingsD.addWidget(self.maxSpin, row=7, col=0)
    settingsD.addWidget(baseLab, row=8, col=0)
    settingsD.addWidget(self.baseSpin, row=9, col=0)
    settingsD.addWidget(holdLab, row=10, col=0)
    settingsD.addWidget(self.holdSpin, row=11, col=0)
    settingsD.addWidget(self.avgBut, row=12, col=0)
    settingsD.addWidget(self.sortBut, row=13, col=0)
    settingsD.addWidget(self.saveFigBut, row=14, col=0)
    settingsD.addWidget(clearButton, row=17, col=0)

    d2 = Dock("Total CCEPs", widget=self.table)
    self.area.addDock(settingsD)
    self.area.addDock(d2, position='above', relativeTo=settingsD)
    self.area.addDock(Dock("Demo", widget=self.gridPlots), position='above', relativeTo=d2)

  def loadSettings(self):
    super().loadSettings()
    self._stds = self.settings.value("stds", 5)
    self.stdSpin.setValue(self._stds)
    self.stdSpin.setToolTip(str(self._stds/10))

    self._sortChs = eval(self.settings.value("sortChs", "False").lower().capitalize()) #take care of string
    self.sortBut.setChecked(self._sortChs)

    self._saveFigs = eval(self.settings.value("saveFigs", "False").lower().capitalize())
    self.saveFigBut.setChecked(self._saveFigs)

    self._avgPlots = eval(self.settings.value("avgPlots", "False").lower().capitalize())
    self.avgBut.setChecked(self._avgPlots)

    self._visBegin = self.settings.value("visBegin", 0)
    self.baseSpin.setValue(self._visBegin)

    self._maxWindows = self.settings.value("maxWindows", 25)
    self.maxSpin.setValue(self._maxWindows)

    self._maxPlots = self.settings.value("maxPlots", 0)
    self.holdSpin.setValue(self._maxPlots)

    self._maskStart = self.settings.value("maskStart", -5)
    self._maskEnd = self.settings.value("maskEnd", 15)

  def saveSettings(self):
    super().saveSettings()
    self.settings.setValue("stds", self._stds)
    self.settings.setValue("sortChs", bool(self._sortChs))
    self.settings.setValue("saveFigs", bool(self._saveFigs))
    self.settings.setValue("avgPlots", bool(self._avgPlots))
    self.settings.setValue("maskStart", self._maskStart)
    self.settings.setValue("maskEnd", self._maskEnd)
    self.settings.setValue("visBegin", self._visBegin)
    self.settings.setValue("maxWindows", self._maxWindows)
    self.settings.setValue("maxPlots", self._maxPlots)

  #an attempt to abstract plotting from BCI2000
  def checkPlot(self):
    return self.comm.evaluate("CCEPTriggered")
  
  def plot(self, data):
    if self.checkPlot():
      print("plotting")
      #get stim ch if we can
      try:
        chBits = self.comm.evaluate("StimulatingChannel")
      except:
        chBits = 0
      if chBits != 0:
        self.stimChs.clear()
        chBinary = str("{0:b}".format(chBits))
        for b in range(len(chBinary)): #32 bit state
          if chBinary[len(chBinary) - b - 1] == '1':
            #print(self.chNames[b] + " at " + str(b))
            self.stimChs.append(self.chNames[b]) #append ch name

      #process data
      aocs = []
      processedData = np.zeros(np.shape(data))
      for i, ch in enumerate(self.chTable.values()):
        processedData[i] = ch.computeData(data[i]) #compute data
        aocs.append(ch.auc)
      
      #send processed data
      self.dataProcessedSignal.emit(aocs)

      #we scale by 10 cause slider can only do ints
      self.aucThresh = np.std(aocs) * self._stds/10

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
    self.baselineLength = self.getParameterValue("BaselineEpochLength") #for now, assume ms
    self.latStart = 0
    self.latStartSamples = self._maskStart
    self.ccepLength = self.getParameterValue("CCEPEpochLength")
    self.sr = self.getParameterValue("SamplingRate")
    if self.sr < 30:
        self.sr = self.sr * 1000 #TODO: ugly hack if sampling rate is in kHz
    self.baseSamples = self.msToSamples(self.baselineLength)
    self.trigSamples = self._maskEnd 
    self.trigLatLength = self.trigSamples * 1000.0 / self.sr
    
    self.x = np.linspace(-self.baselineLength, self.ccepLength, self.elements)

    #to visualize stimulating channels if we can
    self.stimChs = []

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

  def setStdDevState(self, value):
    self._stds = value
    self.stdSpin.setToolTip(str(value/10))
  def setMaxWindows(self, spin):
    self._maxWindows = spin.value()
  def setMaxPlots(self, spin):
    self._maxPlots = spin.value()
  def setAvgPlots(self, state):
    self._avgPlots = state
  def setSortChs(self, state):
    if self._sortChs and not state and hasattr(self, 'chTable'):
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

  def setBaselineBegin(self, spin):
    self._visBegin = spin.value()
    if hasattr(self, "windows"):
      #windows have been configured
      for i in range(0, self.windows):
        #xEnd = self.chPlot[i].getViewBox().viewRange()[0][1]
        self.chPlot[i].getViewBox().setXRange(spin.value(), self.ccepLength)
      
  def msToSamples(self, lengthMs):
    return int(lengthMs * self.sr/1000.0)
      


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
    if self._saveFigs:
      self.saveFigures()
    for i in range(0, self.windows):
      children = self.chPlot[i].listDataItems()
      for child in children[1:]: #save first plot
        self.chPlot[i].removeItem(child)
    children[0].setPen(pg.mkPen('b')) #blend in

    for t in self.chTable.values():
      t.totalChanged(0)
      t.database = []

  def saveFigures(self):
    saveFigure(self.print, self.bciThread.savePath, self.gridPlots, '_CCEPs', '.svg')
    
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
        self.chPlot[i].changePlot(chName, self.chTable[chName])
        if newData:
          self.chPlot[i].plotData()
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
    xLim = self.p._visBegin
    yLim = self.p.ccepLength
    axView.setXRange(xLim, yLim, padding=0)
    axView.setYRange(-1000, 1000)

    self.setMinimumSize(100,100)

    self.hideAxis('left')
    self.hideAxis('bottom')

    #stim artifact filter
    self.latReg = pg.LinearRegionItem(values=(self.p.latStartSamples*1000.0/self.p.sr, self.p.trigLatLength), movable=True, brush=(9, 24, 80, 100), 
                                      pen=pg.mkPen(color=(9, 24, 80), width=1, style=QtCore.Qt.DotLine), bounds=[xLim, yLim])
    self.latReg.setZValue(highZValue) #make sure its in front of all plots
    #callbacks
    self.latReg.sigRegionChanged.connect(self.regionChanged)
    self.addItem(self.latReg)
    self.latHigh = self.p.trigLatLength
    self.latLow = 0

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

  def changePlot(self, name, link):
    #have we changed channels
    if self.name != name:
      self.setTitle(name)
      self.name = name
      self.link = link #update link
      if len(self.link.database) > 0:
        #change data of all plots but average
        for f, d in zip(self.listDataItems()[1:], self.link.database):
          f.setData(x=self.p.x, y=d, useCache=True)

      #change background based on selected
      if self.selected and not self.link.selected:
        self.vb.setBackgroundColor(backgroundColor)
        self.selected = False
      elif not self.selected and self.link.selected:
        self.vb.setBackgroundColor(highlightColor)
        self.selected = True

  #plot: new name and link is only considered if we are dynamically sorting
  def plotData(self):
    children = self.listDataItems() #all plots
    
    #update colors for old plots
    if self.p._maxPlots > 0:
      extra = len(children) - self.p._maxPlots + 1  #account for 1 more we will plot
      for i in range(extra):
        self.removeItem(children[0])
        children.pop(0)
        self.link.database.pop(0)
    expColors = [(255) * (1 - 2**(-x)) for x in np.linspace(0+1/(len(children)+1), 1-1/(len(children)+1), len(children))]
    for child, c in zip(children[1:], expColors):
      child.setPen(self.p.pens[int(c)])

    #plot new data
    p2 = 255*(1-2.5**(-1*(1-1/(len(self.link.database)+1))))
    self.plot(x=self.p.x, y=self.link.database[-1], useCache=True, pen=self.p.pens[int(p2)], _callSync='off')
    
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

    self.significant = False
    self.selected = False
    self.database = []
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

  def computeData(self, newData):        
    #new data, normalize amplitude with baseline data
    if self.p.baseSamples == 0:
      self.data = newData
      #stdBase = 0
    else:
      avBase = np.mean(newData[:self.p.baseSamples])
      #stdBase = np.std(self.rawData[:self.p.baseSamples], dtype=np.float64)
      self.data = np.subtract(newData, avBase)

    #store data
    self.database.append(self.data.copy())

    #possibly change to average, before we detect ccep
    if self.p._avgPlots:
      #calculate average of plots
      self.data = np.mean(self.database, axis=0)
    
    #get area under the curve
    ccepData = self.getActiveData(self.data)
    normData = ccepData - np.mean(ccepData)
    self.auc = np.trapz(abs(normData))/1e3
    return self.auc