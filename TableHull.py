import FreeCAD, FreeCADGui, Draft, Part, os

ui_path = os.path.join(os.path.dirname(__file__), 'hulls.ui')

class HullsPanel():
    def __init__(self):
        self.form = FreeCADGui.PySideUic.loadUi(str(ui_path))

    def accept(self):
        ActiveDocument = FreeCAD.ActiveDocument
        filename = self.form.filename.text()
        symmetric = self.form.symmetric.isChecked()
        chine_count = self.form.chine_count.value()
        keel_width = [self.form.keel_width.value()]

        if not os.path.exists(filename):
            return
        
        def tonum(x):
            if isinstance(x, float):
                return x
            try:
                x = x.strip()
                return float(x)
            except:
                return None
        def tonumarr(x):
            return[tonum(y) for y in x]

        with open(filename, 'r') as f:
            lines = [x.split(',')[1:] for x in f]

        station_names = lines[0]
        x = lines[1]            
        sheer_height = lines[2]
        sheer_x = lines[3]
        # Apart from the chines, there are six rows:
        # - Station names
        # - Station distance from stern
        # - Sheer height
        # - Sheer x
        # - Rabbet height
        # - Rabbet x
        # - Keel height
        # - Keel x
        # - Sheer half-width
        # Each height or width row has a second row below it.  If a column of this second row
        # is not empty, it means that the corresponding poiot is a corner point, rather than
        # a smooth B-spline point.
        chine_height = lines[4:2*chine_count + 4:2]
        chine_x = lines[5:2*chine_count+5:2]
        rabbet_height = lines[2*chine_count + 4]
        rabbet_x = lines[2*chine_count+5]
        keel_height = lines[2*chine_count + 6]
        keel_x = lines[2*chine_count + 7]
        sheer_width = lines[2*chine_count + 8]
        chine_width = lines[2*chine_count + 9:]
        
        print('\n'.join(str(x) for x in [keel_height, keel_x]))

        print(keel_width)
        keel_width = keel_width * len(station_names)
        print(keel_width)

        def end_tangent(pt, pt1, t):
            diff = pt - pt1
            angle = diff.getAngle(t)
            axis = diff.cross(t)
            rot = FreeCAD.Rotation(axis, -angle)
            return rot.multVec(-diff) * (t.Length / diff.Length)

        def trivial_tangent(pt1, pt2):
            return pt1 - pt2
        
        def middle_tangent(pt_prev, pt, pt_next):
            a = pt_prev - pt
            b = pt_next - pt
            tangent = (a + b) / 2
            axis = a.cross(b)
            rot = FreeCAD.Rotation(axis, 90)
            return rot.multVec(tangent)

        def tangents(pts, corner):
            assert len(pts) == len(corner)
            assert len(pts) > 1
            if len(pts) == 2:
                return [pts[1] - pts[0], pts[0] - pts[1]]
            
            calc_tangents = [None] * len(pts)
            non_none_pts = (item for item in pts if item is not None)
            first = next(non_none_pts)
            second = next(non_none_pts)
            prev = first
            prev_tangent = None
            last_pt_index = next(reversed([index for index, item in enumerate(pts) if item is not None]))
            for ii in range(1, last_pt_index - 1):
                if pts[ii] is None:
                    continue
                pt = pts[ii]
                nxt = next(item for item in pts[ii+1:] if item is not None)
                calc_tangents[ii] = middle_tangent(prev, pt, nxt)
                prev = pt
                prev_tangent = calc_tangents[ii]

            second_tangent = [t for pt, t in zip(pts, calc_tangents) if pt is not None][1]
            calc_tangents[0] = end_tangent(first, second, second_tangent)
            calc_tangents[last_pt_index] = end_tangent(pts[last_pt_index], prev, prev_tangent)
            return calc_tangents

        def make_part(x, y, z, corner):
            print('Part')
            x, y, z = tonumarr(x), tonumarr(y), tonumarr(z)
            print(x, y, z)
            vertices = [FreeCAD.Vector(a, b, c) if (a is not None and b is not None and c is not None) else None for a, b, c in zip(x, y, z)]
            print(vertices)
            segments = []
            segment = []
            segment_corners = []
            overall_tangents = tangents(vertices, corner)
            first_tangent = None
            for vertex, c, t in zip(vertices, corner, overall_tangents):
                if vertex is None:
                    continue
                segment.append(vertex)
                segment_corners.append(c)
                if c is not None and c == 'x':
                    curve = Part.BSplineCurve()
                    ts = tangents(segment, segment_corners)
                    if first_tangent:
                        ts[0] = first_tangent
                    curve.interpolate(segment, Tangents=ts)
                    segments.append(curve)
                    segment = [vertex]
                    segment_corners = [c]
                    first_tangent = None
                if c is not None and c == 'y':
                    curve = Part.BSplineCurve()
                    ts = tangents(segment, segment_corners)
                    ts[-1] = t
                    if first_tangent:
                        ts[0] = first_tangent
                    curve.interpolate(segment, Tangents=ts)
                    segments.append(curve)
                    segment = [vertex]
                    segment_corners = [c]
                    first_tangent = t
            if(len(segment) > 0):
                curve = Part.BSplineCurve()
                curve.interpolate(segment)
                segments.append(curve)
            print('\n'.join(str(s) for s in segments))
            shape = Part.makeCompound([x.toShape() for x in segments])
            part = ActiveDocument.addObject('Part::Feature', 'Feature')
            part.Shape = shape
            return part

        hull = ActiveDocument.addObject("App::Part", "Hull")
        ActiveDocument.Tip = hull

        print(', '.join(str(x) for x in (x[0], sheer_width[0], sheer_height[0], sheer_x[0])))
        sheer = make_part(x, sheer_width, sheer_height, sheer_x)
        chines = [make_part(x, y, z, c) for y, z, c in zip(chine_width, chine_height, chine_x)]
        rabbet = make_part(x, keel_width, rabbet_height, rabbet_x)
        keel = make_part(x, keel_width, keel_height, keel_x)

        sheer.Label = "Sheer"
        hull.addObject(sheer)
        for i, chine in enumerate(chines):
            chine.Label = "Chine{}".format(i)
            hull.addObject(chine)
        rabbet.Label = "Rabbet"
        hull.addObject(rabbet)
        keel.Label = "Keel"
        hull.addObject(keel)
        surf = Part.makeRuledSurface(sheer.Shape, chine.Shape)

class CmdTableHull():
    def __init__(self):
        self.hulls_panel = None
    
    def Activated(self):
        self.hulls_panel = HullsPanel()
        FreeCADGui.Control.showDialog(self.hulls_panel)

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None
    
    def GetResources(self):
        return { 'Pixmap': ':/icons/Hull.svg',
                 'MenuText': 'Generate Hull',
                 'ToolTip': 'Generate hull from file'}

