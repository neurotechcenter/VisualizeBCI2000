# importing various libraries
import numpy as np
from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
from pyqtgraph.dockarea import *
from filters.filterBase.GridFilter import GridFilter
from base.SharedVisualization import saveFigure

backgroundColor = (14, 14, 14)
highlightColor = (60, 60, 40)
highZValue = 1000

class CCEPFilter(GridFilter):
  def __init__(self, area):
    super().__init__(area)
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
    #reset onset period
    self.onsetSpin = pg.SpinBox(int=True, compactHeight=True)
    self.onsetSpin.setMaximum(2**8 - 1)
    self.onsetSpin.setMinimum(1)
    #onsetSpin.setValue(self._maxPlots)
    self.onsetSpin.sigValueChanged.connect(self.setOnset)
    self.onsetSpin.setToolTip("Frequency of triggers that are displayed (e.g. 2 = every other trigger)")
    onsetLab = QtWidgets.QLabel("Onset Period", objectName="h3")
    onsetLab.setToolTip("Frequency of triggers that are displayed (e.g. 2 = every other trigger)")

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
    settingsD.addWidget(onsetLab, row=15, col=0)
    settingsD.addWidget(self.onsetSpin, row=16, col=0)
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


  def plot(self, data):
    try:
      newVal = int(self.bci.GetStateVariable("CCEPTriggered").value)
    except:
      newVal = 0

    #if newVal != self.oldVal:
    if newVal:
      print("plotting")
      #get stim ch if we can
      try:
        chBits = int(self.bci.GetStateVariable("StimulatingChannel").value)
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
      i = 0
      processedData = np.zeros(np.shape(data))
      for ch in self.chTable.values():
      #for ch in self.chTable.values():
        processedData[i] = ch.computeData(data[i]) #compute data
        aocs.append(ch.auc)
        i+=1
      #send processed data
      self.dataProcessedSignal.emit(aocs)

      #we scale by 10 cause slider can only do ints
      t = np.std(aocs) * self._stds/10
      #update table with new data
      for ch in self.chTable.values():
        ch.totalChanged(ch.auc > t)
      #sort table with updated numbers
      self.table.sortItems(0, QtCore.Qt.DescendingOrder)

      #plot!
      for i in range(0, self.windows):
        chName = self.table.item(i, 0).text()
        self.chPlot[i].plotData(chName, self.chTable[chName])

      self.oldVal = newVal

  def changeBackgroundColor(self, row, emph):
    if row >= self.windows:
      return
    c = backgroundColor
    if emph:
      c = highlightColor
    self.chPlot[row].vb.setBackgroundColor(c)
    chName = self.table.item(row,0).text()
    self.chPlot[row].selected = emph
    self.chTable[chName].selected = emph
      
  def itemChanged(self):
      items = self.table.selectedItems()
      newRows = []
      for p in items:
          if p.row() not in self.selectedRows:
              self.changeBackgroundColor(p.row(),True)
          newRows.append(p.row())
      for oldS in self.selectedRows:
          if oldS not in newRows:
              self.changeBackgroundColor(oldS, False)
      self.selectedRows = newRows                

  def setConfig(self):
      super().setConfig()

      self.gridNums.clear()

      self.chPlot = list(range(self.channels))
      self.chOrder = list(range(self.channels))
      #self.chPlot = {}
      self.chTable = {}
      self.regs = list(range(self.channels))
      #init variables
      self.oldVal = 0
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
      onsetPeriod = int(self.getParameterValue("OnsetPeriod"))
      self.onsetSpin.setValue(onsetPeriod)

      #go thru all channels for table
      self.tableArray = []
      count = 0
      for chName in self.chNames:
          sub1 = self.gridNums.addLayout()
          sub1.addLabel("<b>%s"%(chName), size='20pt', bold=True)
          #print(self.tableArray)
          self.tableArray.append({
              "Name": chName,
              "Count": 0,
              "AUC": 0
          })
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
            self.chOrder[ch] = chName
            self.chPlot[ch] = CCEPPlot(self, title=chName, row=self.chTable[chName])
            self.gridPlots.addItem(self.chPlot[ch])
            if ch != 0:
              self.chPlot[ch].setLink(self.chPlot[ch-1])
        self.gridPlots.nextRow()
      
      if self.windows > 1:
        self.chPlot[0].friend = self.chPlot[self.windows-1] #give first plot a friend
      
      #table
      self.table.setRowCount(self.channels)
      heads = ["Name", "Sig?", "AUC"]
      self.table.setColumnCount(len(heads))
      self.table.setHorizontalHeaderLabels(heads)
      for i, name in enumerate(self.chNames):
        n = MyTableWidgetItem(name, self.channels - i, self.channels) #save order as rank
        s = MyTableWidgetItem(0)
        a = MyTableWidgetItem(0)
        self.table.setItem(i, 0, n)
        self.table.setItem(i, 1, s)
        self.table.setItem(i, 2, a)
      self.table.resizeColumnsToContents()
      #self.table.setData(self.tableArray)
      #self.table.setSortMode(0,'index')
      self.table.sortItems(0, QtCore.Qt.DescendingOrder)
      count = 0
      for chName in self.chNames:
        self.chTable[chName].setTableItem(count)
        count = count + 1
      self.setSortChs(self._sortChs)
      #make sure user can't change sorting
      for i in range(self.table.columnCount()):
        h = self.table.horizontalHeaderItem(i)
        h.setFlags(h.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.table.setHorizontalHeaderItem(i, h)
      # print(self.table.horizontalHeaderItem(1).text())
      self.selectedRows = []
      #self.table.itemClicked.connect(self.tableItemClickedCallback)
      self.table.itemSelectionChanged.connect(self.itemChanged)

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
    self._sortChs = state
  def setSaveFigs(self, state):
    self._saveFigs = state

  def setBaselineBegin(self, spin):
    self._visBegin = spin.value()
    if hasattr(self, "windows"):
      #windows have been configured
      for i in range(0, self.windows):
        #xEnd = self.chPlot[i].getViewBox().viewRange()[0][1]
        self.chPlot[i].getViewBox().setXRange(spin.value(), self.ccepLength)

  def setOnset(self, spin):
    try:
      self.bci.Execute("SET STATE ResetOnsetPeriod " + str(spin.value()))
    except:
      print("Could not connect to BCI2000")
  def resetOnsetPeriod(self):
    try:
      self.bci.Execute("SET STATE ResetOnsetPeriod 1")
    except:
      print("Could not connect to BCI2000")
      
  def msToSamples(self, lengthMs):
    return int(lengthMs * self.sr/1000.0)
      
  def getParameterValue(self, pName):
    p = self.parameters[pName]
    return float(p['val'])


  def updateParameter(self, latStart, newLat):
    if newLat != self.trigLatLength:
      self.trigLatLength = newLat
      self.trigSamples = self.msToSamples(newLat)
      if round(newLat) >= 0:
        latP = round(newLat)
      else:
        latP = 0
      #self.bciThread.bci.SetParameter("TriggerLatencyLength", str(latP)+"ms")
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

class MyTableWidgetItem(QtWidgets.QTableWidgetItem):
  def __init__(self, parent=None, rank=0, maxVal=0):
    QtWidgets.QTableWidgetItem.__init__(self, parent)
    self.rank = rank
    self.sig = 0
    self.max = maxVal
  #define less than (<) operator for table sorting
  def __lt__(self, b):
    return (self.rank + self.sig*self.max) < (b.rank + b.sig*b.max)
        

class CCEPPlot(pg.PlotItem):
  def __init__(self, parent, title, row):
    super().__init__(title=title)
    self.p = parent
    self.name = title
    self.link = row
    self.selected = False
    #prepare view
    axView = self.getViewBox()
    axView.disableAutoRange()
    axView.setMouseEnabled(x=False, y=True)
    axView.setDefaultPadding(0)
    xLim = self.p._visBegin
    yLim = self.p.ccepLength
    axView.setXRange(xLim, yLim, padding=0)
    axView.setYRange(-1000, 1000)

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

  #plot: new name and link is only considered if we are dynamically sorting
  def plotData(self, name, link):
    children = self.listDataItems() #all plots
    #have we changed channels
    if self.name != name:
      self.setTitle(name)
      self.name = name
      self.link = link #update link
      plotNum = len(self.link.database) - 1
      #simply change, except for average plot
      expColors = [(255) * (1 - 2**(-x)) for x in np.linspace(0+1/(plotNum+1), 1-1/(plotNum+1), plotNum)]
      for f, d, p in zip(children[1:], self.link.database[:-1], expColors):
        f.setData(x=self.p.x, y=d, useCache=True, pen=self.p.pens[int(p)])
      # #now add
      # expColors = [(255) * (1 - 2**(-x)) for x in np.linspace(0+1/(len(self.link.database)+1), 1-1/(len(self.link.database)+1), len(self.link.database))]
      # for f, d, p in zip(self.listDataItems(), self.link.database, expColors):
      #   f.setData(x=self.p.x, y=d, useCache=True, pen=self.p.pens[int(p)])
      
      # #channel has changed, need to re-plot everything
      # for child in self.listDataItems():
      #   self.removeItem(child)
      # #TODO: use multiDataPlot for more efficient plotting, figure out pens
      # #self.multiDataPlot(x=self.p.x, y=self.link.database)
      # for d, p in zip(self.link.database, expColors):
      #   self.plot(x=self.p.x, y=d, useCache=True, pen=self.p.pens[int(p)])
      #change background based on selected
      if self.selected and not self.link.selected:
        self.vb.setBackgroundColor(backgroundColor)
        self.selected = False
      elif not self.selected and self.link.selected:
        self.vb.setBackgroundColor(highlightColor)
        self.selected = True
    else:
      #update colors for old plots
      # if self.link.averaged and np.size(children) > 0:
      #   #remove average plot
      #   self.removeItem(children[-1]) #average should be most recent one
      #   self.link.averaged = False
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
    if len(self.link.database) > 1:
      #if averaged, plot most recent ccep before average
      p2 = 255*(1-2.5**(-1*(1-1/(len(self.link.database)+1))))
      self.plot(x=self.p.x, y=self.link.database[-1], useCache=True, pen=self.p.pens[int(p2)], _callSync='off')
    #self.plot(x=self.p.x, y=self.link.data, useCache=True, pen=p)

    #update average plot
    #if self.p._avgPlots:
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

  def getActiveData(self, data):
    p1 = data[:self.p.baseSamples+self.p.latStartSamples]
    p2 = data[self.p.baseSamples+self.p.trigSamples:]
    d = np.concatenate((p1, p2))
    #print(np.shape(d))
    return p2

  def setTableItem(self, ch):
    self.tableItem = self.p.table.item(ch,0)

  #t = boolean, if significant or not
  def totalChanged(self, t):
    self.tableItem.sig = t
    r = self.p.table.row(self.tableItem) #find new row we are at
    self.p.table.item(r,1).setData(QtCore.Qt.DisplayRole, int(t)) #change number at that row
    self.p.table.item(r,2).setData(QtCore.Qt.DisplayRole, int(self.auc))
    self.significant = t
    if (self.significant):
      self.p.table.item(r,0).setBackground(pg.QtGui.QColor(56,50,0))
      

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