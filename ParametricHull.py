import FreeCAD, FreeCADGui, os, Part
import numpy as np

ui_path = os.path.join(os.path.dirname(__file__), 'parametric-hulls.ui')

def ft(m):
    return m * 1000 / 25.4 / 12

def td(x, m, n):
    return (1 - x ** 2) ** m * ((1 - x) / 2) ** (n / 2)

def spline_from_vertices(vs):
    spline = Part.BSplineCurve()
    spline.buildFromPoles(vs)
    return spline

class ParametricHullPanel():
    def __init__(self):
        self.form = FreeCADGui.PySideUic.loadUi(ui_path)

        self.feature = FreeCAD.ActiveDocument.addObject('Part::Feature', 'boundary')
        self.stations = FreeCAD.ActiveDocument.addObject('Part::Feature', 'stations')
        self.surface = FreeCAD.ActiveDocument.addObject('Surface::Filling', 'surface')

        self.update_ft()
        self.form.length.valueChanged.connect(self.update_ft)
        self.form.beam.valueChanged.connect(self.update_ft)
        self.form.draft.valueChanged.connect(self.update_ft)
        self.form.freeboard.valueChanged.connect(self.update_ft)

        self.form.stations.valueChanged.connect(self.update)
        self.form.h_box.valueChanged.connect(self.update)
        self.form.v_box.valueChanged.connect(self.update)
        self.form.teardrop.valueChanged.connect(self.update)
    
    def update_ft(self, *args):
        length = self.form.length.value()
        self.form.length_ft.setValue(ft(length))
        beam = self.form.beam.value()
        self.form.beam_ft.setValue(ft(beam))
        draft = self.form.draft.value()
        self.form.draft_ft.setValue(ft(draft))
        freeboard = self.form.freeboard.value()
        self.form.freeboard_ft.setValue(ft(freeboard))
        self.update()
    
    def update(self, *args):
        self.create_geometry()
    
    def create_geometry(self, *args):
        lod = self.form.length.value()
        n_stations = self.form.stations.value()
        n_points = self.form.control_points.value()
        h_box = self.form.h_box.value()
        v_box = self.form.v_box.value()
        beam = self.form.beam.value()
        draft = self.form.draft.value()
        freeboard = self.form.freeboard.value()

        teardrop_factor = self.form.teardrop.value()

        x = np.arange(-1, 1.00001, 2 / (n_stations + 1.0))
        sheer_y = td(x, h_box, teardrop_factor)
        norm_beam = max(sheer_y)
        rabbet_z = td(x, v_box, teardrop_factor)
        norm_rabbet = max(rabbet_z)

        x *= lod * 1000
        sheer_y *= (beam / 2) * 1000 / norm_beam
        rabbet_z *= (draft + freeboard) * 1000 / norm_rabbet
        stations = []
        for ii, a in enumerate(x):
            station = [FreeCAD.Vector(a, sheer_y[ii], 0)]
            for jj in range(n_points + 1):
                angle = np.pi / 2 / (n_points + 1) * (jj + 1)
                v = FreeCAD.Vector(a, np.cos(angle) * sheer_y[ii], np.sin(angle)**v_box * np.sin(angle / 2)**teardrop_factor * rabbet_z[ii])
                station.append(v)
            stations.append(station)
        
        boundary = [
            spline_from_vertices([FreeCAD.Vector(a, b, 0) for a, b in zip(x, sheer_y)]),
            spline_from_vertices([FreeCAD.Vector(a, 0, b) for a, b in zip(x, rabbet_z)])
        ]
        station_curves = [spline_from_vertices(l) for l in stations]

        shape_lines = [p.toShape() for p in boundary]
        station_lines = [p.toShape() for p in station_curves]
        self.feature.Shape = Part.makeCompound(shape_lines)
        self.stations.Shape = Part.makeCompound(station_lines)

        self.surface.BoundaryEdges = [(self.feature, self.feature.Label.encode('utf-8'))]
        self.surface.UnboundEdges = [(self.stations, self.stations.Label.encode('utf-8'))]

#        self.surface.recomputeFeature()

#        self.feature.Shape = Part.makeCompound(lines)
        
        
    def accept(self):
        return True

class CmdParametricHull():
    def __init__(self):
        self.panel = None
    
    def Activated(self):
        self.panel = ParametricHullPanel()
        FreeCADGui.Control.showDialog(self.panel)
    
    def IsActive(self):
        return FreeCAD.ActiveDocument is not None
    
    def GetResources(self):
        return { 'Pixmap': ':/icons/Hull.svg',
            'MenuText': 'Generate Hull',
            'ToolTip': 'Generate parametric hull' }
