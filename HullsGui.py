# -*- coding: utf-8 -*-
# FreeCAD tools of the Hulls workbench
# (c) 2001 Juergen Riegel
# License LGPL

import FreeCAD, FreeCADGui
import os
import Draft, Part


#from TableHull import CmdTableHull
from ParametricHull import CmdParametricHull

#FreeCADGui.addCommand('Hulls_GenerateHull', CmdTableHull())
FreeCADGui.addCommand('Hulls_ParametricHull', CmdParametricHull())