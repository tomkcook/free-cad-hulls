import FreeCAD, FreeCADGui, os, Part, scipy.optimize
import numpy as np

ui_path = os.path.join(os.path.dirname(__file__), 'parametric-hulls.ui')

def ft(m):
    return m * 1000 / 25.4 / 12

def td(m, n):
    def func(x):
        return (1 - x ** 2) ** m * ((1 - x) / 2) ** (n / 2)
    return func

def td_max(m, n):
    return -n / (-n + 4*m)

def td_inv(f, y, centre, endpoint = 1):
    step = endpoint - centre
    x = centre
    while abs(y - f(x)) > 1e-6:
        step /= 2
        direction = np.sign(f(x) - y)
        x += direction * step
    return x
    
def spline_from_vertices(vs):
#    spline = Part.BSplineCurve()
#    spline.buildFromPoles(vs)
#    return spline
    spline = Part.BSplineCurve()
    spline.interpolate(vs)
    return spline

def parabolic_sheer(x, teardrop_y_func, centre, rise, sheer_y):
    """Calculate the z-coordinates of the sheer line.
    
    The sheer line is constructed by the following method:

    From the point of maximum beam forward to the bow, the sheer line
    is a parabola, fitted through these two points and with the
    maximum beam at the parabola's minimum.
   
    From the point of maximum beam aft to the sterm, the sheer line is
    constructed so that fore-aft deck beams running parallel to the
    centreline are horizontal.  This makes the deck easy to construct,
    easier to walk on and gives it a more traditional, 'shippy' look.

    Mathematically, to construct the rear half of the sheer line's
    z-coordinates, we start with that point's x,y coordinates.  We
    then find the x-coordinate forward of the maximum beam which has
    the same y-coordinate as the point we're trying to construct and
    use that point's z-coordinate as the z-coordinate of the point
    we're constructing.

    Or, put another way, "points on the sheer that have equal
    y-coordinates also have equal z-coordinates".
    """

    # The forward half is a parabola.
    p = 1.
    q = centre * 2. - 1.
    sheer_z = np.array([0.] * len(x))
    ps = (x >= centre)
    def z_func(x):
        return (x - p) * (x - q)
    sheer_z[ps] = z_func(x[ps])

    # The aft half is constructed from the forward half.
    nps = ~ps
    indices = np.array(range(len(x)))
    for ii, xp, y in zip(indices[nps], x[nps], sheer_y[nps]):
        # We know the stern is at the same elevation as the bow without doing
        # any fancy maths
        if ii == 0:
            sheer_z[ii] = sheer_z[-1]
            continue
        if ii == len(x)-1:
            sheer_z[ii] = sheer_z[0]
            continue
        opposite_x = td_inv(teardrop_y_func, y, centre)
        sheer_z[ii] = z_func(opposite_x)

    # Scaled to the correct fall at maximum beam.
    sheer_z *= -rise / ((centre - p) * (centre - q))
    return sheer_z

class ParametricHullPanel():
    def __init__(self):
        self.form = FreeCADGui.PySideUic.loadUi(ui_path)

        self.left = self.create_objects('left')
        self.right = self.create_objects('right')
        dev = 0.2
        self.set_deviation(self.left, dev)
        self.set_deviation(self.right, dev)
        
        self.update_ft()
        self.form.length.valueChanged.connect(self.update_ft)
        self.form.beam.valueChanged.connect(self.update_ft)
        self.form.draft.valueChanged.connect(self.update_ft)
        self.form.freeboard.valueChanged.connect(self.update_ft)

        self.form.stations.valueChanged.connect(self.update)
        self.form.h_box.valueChanged.connect(self.update)
        self.form.v_box.valueChanged.connect(self.update)
        self.form.l_box.valueChanged.connect(self.update)
        self.form.teardrop.valueChanged.connect(self.update)
        self.form.sheer_rise.valueChanged.connect(self.update)

    def create_objects(self, suf):
        return dict(
            feature=FreeCAD.ActiveDocument.addObject('Part::Feature', 'boundary' + suf),
            stations=FreeCAD.ActiveDocument.addObject('Part::Feature', 'stations' + suf),
            beams=FreeCAD.ActiveDocument.addObject('Part::Feature', 'beams' + suf),
            surface=FreeCAD.ActiveDocument.addObject('Surface::Filling', 'surface' + suf),
            deck=FreeCAD.ActiveDocument.addObject("Surface::Filling", "deck" + suf)
        )

    def set_deviation(self, d, dev = 0.01):
        for k, v in d.iteritems():
            v.ViewObject.Deviation = dev
            
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
        lod = self.form.length.value()
        n_stations = self.form.stations.value()
        n_points = self.form.control_points.value()
        h_box = self.form.h_box.value()
        v_box = self.form.v_box.value()
        l_box = self.form.l_box.value()
        beam = self.form.beam.value()
        draft = self.form.draft.value()
        freeboard = self.form.freeboard.value()
        sheer_rise = self.form.sheer_rise.value()

        teardrop_factor = self.form.teardrop.value()

        self.create_geometry(1, lod, n_stations, n_points, h_box, v_box, l_box,
                             beam, draft, freeboard, sheer_rise, teardrop_factor,
                             self.left)
        self.create_geometry(-1, lod, n_stations, n_points, h_box, v_box, l_box,
                             beam, draft, freeboard, sheer_rise, teardrop_factor,
                             self.right)

    def create_geometry(self, direction, lod, n_stations, n_points, h_box, v_box, l_box,
                        beam, draft, freeboard, sheer_rise, teardrop_factor,
                        side):
        feature = side['feature']
        stations = side['stations']
        beams = side['beams']
        surface = side['surface']
        deck = side['deck']
        
        # Convert dimensions to mm
        lod *= 1000
        sheer_rise *= 1000
        # TODO: other dimensions        

        # Generate normalised geometry on the domain [-1, 1]
        print('Basic geom')
        x = np.arange(-1, 1.00001, 2 / (n_stations + 1.0))
        sheer_y_func = td(h_box, teardrop_factor)
        sheer_y_norm = sheer_y_func(x)
        norm_beam = max(sheer_y_norm)
        rabbet_z_func = td(v_box, teardrop_factor)
        rabbet_z = -rabbet_z_func(x)
        norm_rabbet = max(abs(rabbet_z))
        rabbet_z *= (draft + freeboard) * 1000 / norm_rabbet
        beam_max = td_max(h_box, teardrop_factor)
        sheer_z = parabolic_sheer(x, sheer_y_func, beam_max, sheer_rise, sheer_y_norm)
        sheer_y = sheer_y_norm * (beam / 2) * 1000 / norm_beam * direction
        rabbet_z[0] = sheer_z[0]
        rabbet_z[-1] = sheer_z[-1]

        ps = (x > beam_max)
        
        # Now convert the x co-ordinates to the domain [0, lod]
        x += 1
        x *= lod / 2

        # Now generate ribs at each design station
        print('stations')
        stations_geom = []
        for ii, a in enumerate(x):
            station = [FreeCAD.Vector(a, sheer_y[ii], sheer_z[ii])]
            for jj in range(n_points):
                angle = np.pi / 2 / (n_points + 1) * (jj + 1)
                v = FreeCAD.Vector(
                    a,
                    np.cos(angle) * sheer_y[ii],
                    #np.sin(angle)**v_box * np.sin(angle / 2)**teardrop_factor * rabbet_z[ii])
                    np.sin(angle)**l_box * rabbet_z[ii])
                station.append(v)
            station.append(FreeCAD.Vector(
                a, 0, rabbet_z[ii]
            ))
            stations_geom.append(station)

        print('Splines')
        boundary = [
            spline_from_vertices([FreeCAD.Vector(a, b, c) for a, b, c in zip(x, sheer_y, sheer_z)]),
            spline_from_vertices([FreeCAD.Vector(a, 0, b) for a, b in zip(x, rabbet_z)])
        ]
        # At either end, the "curves" resolve to a single point and so can't be interpolated
        station_curves = [spline_from_vertices(l) for l in stations_geom[1:-1]]

        print('beams')
        beams_geom = []
        for px, ny, py, pz in zip(x[ps], sheer_y_norm[ps], sheer_y[ps], sheer_z[ps]):
            if px == 0:
                opx = 1
            else:
                opx = td_inv(sheer_y_func, ny, beam_max, -1)
            opposite_x = (opx + 1) * lod / 2
            print(px, py, pz, opx, opposite_x)
            beams_geom.append(spline_from_vertices([FreeCAD.Vector(px, py, pz), FreeCAD.Vector(opposite_x, py, pz)]))

        print('Shapes')
        shape_lines = [p.toShape() for p in boundary]
        station_lines = [p.toShape() for p in station_curves]
        beam_lines = [p.toShape() for p in beams_geom]
        print('Parts')
        feature.Shape = Part.makeCompound(shape_lines)
        stations.Shape = Part.makeCompound(station_lines)
        beams.Shape = Part.makeCompound(beam_lines)

        FreeCAD.ActiveDocument.recompute()

        print('Surfaces')
        surface.BoundaryEdges = [
            (feature, ['Edge{}'.format(ii+1) for ii in range(len(boundary))])
        ]
        surface.UnboundEdges = [
            (stations, ['Edge{}'.format(ii+1) for ii in range(len(station_lines))])
        ]
        surface.recompute()

        deck.BoundaryEdges = [
            (feature, ["Edge1"]),
            (beams, ["Edge{}".format(len(beam_lines))])
        ]
        deck.UnboundEdges = [
            (beams, ["Edge{}".format(ii + 1) for ii in range(1, len(beam_lines)-1)])
        ]
        deck.recompute()
        
#        self.surface.recomputeFeature()
        
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
