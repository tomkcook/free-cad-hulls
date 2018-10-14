# -*- coding: utf-8 -*-
# Hulls gui init module
# (c) 2001 Juergen Riegel
# License LGPL

class HullsWorkbench ( Workbench ):
    "Hulls workbench object"
    Icon = FreeCAD.getHomePath() + "Mod/Hulls/Resources/icons/HullsWorkbench.svg"
    MenuText = "Hulls"
    ToolTip = "Hulls workbench"
    
    def Initialize(self):
        # load the module
        import HullsGui
        self.appendToolbar('Hulls',['Hulls_ParametricHull'])
        self.appendMenu('Hulls',['Hulls_ParametricHull'])
    
    def GetClassName(self):
        return "Gui::PythonWorkbench"

Gui.addWorkbench(HullsWorkbench())
