import pyqtgraph as pg

#set the styles, obj is some QWidget
def setStyle(obj):
  darkBackground = "#1D1D1F"
  darkGrey = "#606060"
  darkEmphasis = "#0E0E0F"
  darkColor = "#091850"
  lightColor = "rgb(94, 125, 237)"
  pg.setConfigOption("background", pg.mkColor("#1D1D1F"))
  obj.setStyleSheet(f"""
ParameterTree {{
                    color: black;
                    background-color: {darkGrey};
                    font-size: 14pt;
}}
ParameterTree QPushButton {{
    color: {darkBackground};
    background-color: white; 
    border-style: outset; 
    border-width: 2px; 
    border-radius: 5px; 
    border-color: #303030; 
    font: bold 17px; 
    padding: 2px;
    margin: 1px;
    }}
ParameterTree QPushButton:hover {{
    background-color: #A0A0A0;
    margin: 2px;
}}
ParameterTree QPushButton:disabled {{background-color: grey; color: darkgrey;}}
ParameterTree QPushButton:checked {{background-color: {lightColor}; margin: 15px; border-width: 0;}}
QLabel#h1 {{
    font: bold 24px; 
    color: white;
    padding: 1px;
}}
QLabel#h2 {{
    font: bold 20px; 
    color: white;
    padding: 2px;
}}
QLabel#h3 {{
    font: 16px; 
    color: white;
    margin-top: 10px;
}}
QLabel {{
    font: bold 16px; 
    color: white;
}}   
Dock > QWidget {{
    background: {darkGrey};
    background-color: {darkGrey};
}}
SpinBox {{
    background-color: white;
    color: {darkBackground};
    font: 16px;
    border-width: 4px; 
    border-radius: 2px; 
    border-color: black;
    min-width: 1em;
    min-height: 1.2em;
    margin-bottom: 10px;
}}
QLineEdit {{
    font: 16px;
}}
QCheckBox {{
    font: 16px;
    color: white;
}}
QProgressBar {{
    border: 1px solid white;
    text-align: center;
    background-color: {darkGrey};
    color: white;
    border-radius: 5px;
    padding: 2px;
    margin: 5px;
}}
QProgressBar::chunk {{
    background-color: rgb(9, 24, 80);
    border-radius: 5px;
}}
QSlider::groove:horizontal {{
    border-radius: 3px;
    height: 3px;
    margin: 0px;
    background-color: rgb(52, 59, 72);
}}
QSlider::groove:horizontal:hover {{
    background-color: rgb(55, 62, 76);
}}
QSlider::handle:horizontal {{
    background-color: {darkColor};
    border: none;
    width: 15px;
    margin: -20px 0;
}}
QSlider::handle:horizontal:hover {{
    background-color:{lightColor};
}}
QSlider::handle:horizontal:pressed {{
    background-color: rgb(65, 255, 195);
}}
QMainWindow {{
    background-color: {darkGrey};
    font: 20px;
}}
QPushButton {{
    color: white;
    background-color: {darkEmphasis}; 
    border-style: outset; 
    border-width: 2px; 
    border-radius: 10px; 
    border-color: #303030; 
    font: bold 26px; 
    padding: 5px;
    margin: 15px;
    }}
QPushButton:hover {{
    background-color: #A0A0A0;
    margin: 5px;
}}
QPushButton:disabled {{background-color: grey; color: darkgrey;}}
QPushButton:checked {{background-color: {lightColor}; margin: 15px; border-width: 0;}}
QHeaderView {{
  background-color: {darkBackground};
  color: #f0f0f0;    
}}
QHeaderView::section {{
  background-color: {darkEmphasis};
  color: #f0f0f0;    
}}
QTableView {{
    background-color: {darkBackground};
    border: 1px solid #32414B;
    color: #f0f0f0;
    gridline-color: #8faaff;
    outline : 0;
}}
QTableView::disabled {{
    background-color: {darkBackground};
    border: 1px solid #32414B;
    color: #656565;
    gridline-color: #656565;
    outline : 0;
}}
QTableView::item:hover {{
    background-color: "#26264f";
    color: #f0f0f0;
}}
QTableView::item:selected {{
    background-color: #1a1b1c;
    border: 2px solid #4969ff;
    color: #F0F0F0;
}}
QTableView::item:selected:disabled {{
    background-color: #1a1b1c;
    border: 2px solid #525251;
    color: #656565;
}}
QTableCornerButton::section {{
    background-color: #505050;
    color: #fff;
}}
""")
