"""
/***************************************************************************
PseudoGrid
A QGIS plugin
Create fake environmental grids following a model
                             -------------------
begin                : 2010-12-20
copyright            : (C) 2010 by Chris Yesson
email                : chris.yesson@ioz.ac.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from Ui_PseudoGrid import Ui_PseudoGrid
from numpy.random import rand
from math import sqrt, pow, log, exp
from numpy import zeros, logical_and, cos, sin, pi, mean, power, int, array, round, std, nonzero, equal
from numpy.random import rand, random_integers, randn, randint, normal
from ecogis.UI_Tools import *

import resources

class PseudoGrid(QDialog, Ui_PseudoGrid):

  # initiate some global variables
  #debug=open("PseudoGrid.log", "w")
  debug=None
  
  ################################################################
  def __init__(self, iface):
    QDialog.__init__(self)

    self.setupUi(self)
    self.repaint()

    # set up output file handling
    self.ascOutput=gisOutputSelect(self, self.outButton, self.outFile, "AAIGrid", "asc")
    #QObject.connect(self.outButton, SIGNAL("clicked()"), self.outFile)

    # set up about box 
    QObject.connect(self.aboutButton, SIGNAL("clicked()"), self.about)

    # get qgis map canvas
    self.iface=iface
    self.mapCanvas=self.iface.mapCanvas()

    # display the available raster layer
    self.rasterLayerSelect = rasterLayerSelect(self, self.iface, self.rasterLayers)

  ################################################################
  # Called when "OK" button pressed (based on the Carson Farmer's PointsInPoly Plugin, 2008)
  def accept(self): 
    if self.rasterLayerSelect.checkSelected() and \
          self.ascOutput.checkOutFile():
      # all tests passed! Let's go on
      self.statusLabel.setText("Processing...")
      self.repaint()
      self.runAnalysis()

  ################################################################
  # Show information when the info button is pressed
  # based on about box of csw client by Alexander Bruy & Maxim Dubinin
  def about( self ):
    dlgAbout = QDialog()
    dlgTitle="PseudoGrid"
    dlgAbout.setWindowTitle( QApplication.translate(dlgTitle, "PseudoGrid Info", "Window title" ) )
    lines = QVBoxLayout( dlgAbout )
    title = QLabel( QApplication.translate( dlgTitle, "<b>PseudoGrid </b>" ) )
    title.setAlignment( Qt.AlignHCenter | Qt.AlignVCenter )
    lines.addWidget( title )
    myText="""
Generate an ascii grid of simulated data following a model.  
Output is the same extent as the input template raster grid.  
The following models are implemented:

Gradient: Output a continuous gradient running from the top
          left corner to the bottom right of the form X+Y.
Regular peaks: Output a grid of regular curved peaks following
          the form cos X + sin Y

A random noise element can be added to the ouput with the
noise option.  For example selecting 5 in the random noise
box will add or subtract up to 5% of value of each pixel.

The rate of change can be tuned by using the power factor
option.  This raises the output to the given factor.  Thus
the gradient model with power factor=1 will produce a linear
gradient, with power factor=2 there will be an exponential
gradient.
"""
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, myText)))

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Developer:</b>" ) ) )
    lines.addWidget( QLabel( "          Chris Yesson" ) )

    btnClose = QPushButton( QApplication.translate( dlgTitle, "Close" ) )
    lines.addWidget( btnClose )
    QObject.connect( btnClose, SIGNAL( "clicked()" ), dlgAbout, SLOT( "close()" ) )

    dlgAbout.exec_()

  ################################################################
  # analysis bit starts here

  ################################################################
  def doGradient(self):
    # environmental dataset 1 - simple gradient

    # Simple function to create a gradient for one variable.
    for ii in range(len(self.Grid)):        ## loop through grid array
      for jj in range(len(self.Grid[0])):   ## already cut into X x Y dimensions
        self.Grid[ii, jj] = power((ii + jj),self.outPower.value())+100
        if self.debug:
          self.debug.write("x=%s,y=%s,z=%s\n" %(ii,jj,power((ii + jj),self.Power)))
          self.debug.flush()


  ################################################################
  def doRegularPeak(self):
    # grid with regular peaks at intervals of wavelength

    piWave=pi*self.peakRepeatInt.value()
    # Simple function to create a gradient for one variable.
    for ii in range(len(self.Grid)):        ## loop through grid array
      for jj in range(len(self.Grid[0])):   ## already cut into X x Y dimensions
        self.Grid[ii, jj] = power(sin(ii/piWave)+cos(jj/piWave),self.outPower.value())*100
        if self.debug:
          self.debug.write("x=%s,y=%s,z=%s\n" %(ii,jj,(sin(ii/piWave)+cos(jj/piWave))*100))
          self.debug.flush()

  ################################################################
  def writeascii(self):

    # write out the data to a simple ascii gis-file
    asciiheader = """ncols           %s
nrows           %s
xllcorner       %s
yllcorner       %s
cellsize        %s
""" %(self.template.width(),
      self.template.height(),
      self.template.extent().xMinimum(),
      self.template.extent().yMinimum(),
      (self.template.extent().xMaximum()-self.template.extent().xMinimum())/self.template.width())

    myOutF=open(self.outFile.displayText(), 'w')
    myOutF.write(asciiheader)
    # assume the array is the right shape
    for jj in range(len(self.Grid[0])):
      for ii in range(len(self.Grid)):
        myOutF.write(" %s " %(self.Grid[ii,jj]))
        myOutF.write("\n")
        
    myOutF.close()

    return

  ################################################################
  def runAnalysis(self):

    if self.debug:
      # set up a log file
      self.debug.write("PseudoGrid: run called!\n")
      self.debug.write("output AAIGrid %s\n" %self.outFile.displayText())
      self.debug.flush()
    
    # find which raster layers are selected
    self.rasterLayerSelected=self.rasterLayerSelect.getSelected()

    # fetch selected raster layer
    self.template=self.rasterLayerSelected[0][0]

    # Create matrix to hold the data
    self.Grid = zeros(self.template.width()*self.template.height(), dtype=int).reshape(self.template.width(),self.template.height())

    if self.gradientButton.isChecked():
      self.doGradient()
    elif self.regularPeakButton.isChecked():
      self.doRegularPeak()

    # add noise to the grid (+/- X% of value)
    if self.outNoise.value()>0:
      noiseGrid=rand(self.template.width(), self.template.height())
      if self.debug:
        self.debug.write("randomGrid=%s\n" %(noiseGrid))

      # rescale to between 1+/- Noise%
      noiseGrid=(noiseGrid*2.0*self.outNoise.value()/100.0)
      if self.debug:
        self.debug.write("randomGrid2=%s\n" %(noiseGrid))
      noiseGrid=noiseGrid+1.0-(self.outNoise.value()/100.0)
      self.Grid = self.Grid * noiseGrid
      # convert back to ints as the above will convert to float
      if self.debug:
        self.debug.write("NoiseGrid=%s\n Grid%s\n" %(noiseGrid, self.Grid))
        self.debug.flush()

      self.Grid = array(self.Grid.round(), dtype=int)

    # write out the grid
    self.writeascii()

    # load into qgis if asked
    if self.addToToc.checkState() == Qt.Checked:
      myOutQ=QFileInfo(self.outFile.displayText())
      myRlayer = QgsRasterLayer(self.outFile.displayText(), 
                                myOutQ.baseName())

      QgsMapLayerRegistry.instance().addMapLayer(myRlayer)

    self.statusLabel.setText("Finished")

