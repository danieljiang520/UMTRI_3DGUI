
from vedo import *
class FreeHandCutPlotter(Plotter):
    """
    A ``Plotter`` derived class which edits polygonal meshes interactively.
    Can also be invoked from command line. E.g. with:

    ``vedo --edit https://vedo.embl.es/examples/data/porsche.ply``

    Usage
    -----
        - Left-click and hold to rotate
        - Right-click and move to draw line
        - Second right-click to stop drawing
        - Press c to clear points
        -       z/Z to cut mesh (Z inverts inside-out the selection area)
        -       L to keep only the largest connected surface
        -       s to save mesh to file (tag _edited is appended to filename)
        -       u to undo last action
        -       h for help, i for info

    Parameters
    ----------
    mesh : Mesh, Points
        The input Mesh or pointcloud.

    splined : bool
        join points with a spline or a simple line.

    font : str
        Font name for the instructions.

    alpha : float
        transparency of the instruction message panel.

    lw : str
        selection line width.

    lc : str
        selection line color.

    pc : str
        selection points color.

    c : str
        backgound color of instructions.

    tc : str
        text color of instructions.

    tol : int
        tolerance of the point proximity.

    .. hint:: examples/basic/cutFreeHand.py
        .. image:: https://vedo.embl.es/images/basic/cutFreeHand.gif
    """
    # thanks to Jakub Kaminski for the original version of this script
    def __init__(
            self,
            mesh,
            splined=True,
            font="Bongas",
            alpha=0.9,
            lw=4,
            lc="red5",
            pc="red4",
            c="green3",
            tc="k9",
            tol=0.008,
            **kwargs
        ):

        super().__init__(**kwargs)

        if not isinstance(mesh, Points):
            logger.error("FreeHandCutPlotter input must be Points or Mesh")
            raise RuntimeError()


        self.mesh = mesh
        self.mesh_prev = mesh
        self.splined = splined
        self.linecolor = lc
        self.linewidth = lw
        self.pointcolor = pc
        self.color = c
        self.alpha = alpha

        self.msg  = "Right-click and move to draw line\n"
        self.msg += "Second right-click to stop drawing\n"
        self.msg += "Press L to extract largest surface\n"
        self.msg += "        z/Z to cut mesh (s to save)\n"
        self.msg += "        c to clear points, u to undo"
        self.txt2d = Text2D(self.msg, pos='top-left', font=font, s=0.9)
        self.txt2d.c(tc).background(c, alpha).frame()

        self.idkeypress = self.addCallback('KeyPress', self._onKeyPress)
        self.idrightclck = self.addCallback('RightButton', self._onRightClick)
        self.idmousemove = self.addCallback('MouseMove', self._onMouseMove)
        self.drawmode = False
        self.tol = tol       # tolerance of point distance
        self.cpoints = []
        self.points = None
        self.spline = None
        self.jline = None
        self.topline = None
        self.top_pts = []

    def init(self, initpoints):
        if isinstance(initpoints, Points):
            self.cpoints = initpoints.points()
        else:
            self.cpoints = np.array(initpoints)
        self.points = Points(self.cpoints, r=self.linewidth).c(self.pointcolor).pickable(0)
        if self.splined:
            self.spline = Spline(self.cpoints, res=len(self.cpoints)*4)
        else:
            self.spline = Line(self.cpoints)
        self.spline.lw(self.linewidth).c(self.linecolor).pickable(False)
        self.jline = Line(self.cpoints[0], self.cpoints[-1], lw=1, c=self.linecolor).pickable(0)
        self.add([self.points, self.spline, self.jline], render=False)
        return self

    def _onRightClick(self, evt):
        self.drawmode = not self.drawmode # toggle mode
        if self.drawmode:
            self.txt2d.background(self.linecolor, self.alpha)
        else:
            self.txt2d.background(self.color, self.alpha)
            if len(self.cpoints) > 2:
                self.remove([self.spline, self.jline])
                if self.splined: # show the spline closed
                    self.spline = Spline(self.cpoints, closed=True, res=len(self.cpoints)*4)
                else:
                    self.spline = Line(self.cpoints, closed=True)
                self.spline.lw(self.linewidth).c(self.linecolor).pickable(False)
                self.add(self.spline)

    def _onMouseMove(self, evt):
        if self.drawmode:
            cpt = self.computeWorldPosition(evt.picked2d) # make this 2d-screen point 3d
            if self.cpoints and mag(cpt - self.cpoints[-1]) < self.mesh.diagonalSize()*self.tol:
                return  # new point is too close to the last one. skip
            self.cpoints.append(cpt)
            if len(self.cpoints) > 2:
                self.remove([self.points, self.spline, self.jline, self.topline])
                self.points = Points(self.cpoints, r=self.linewidth).c(self.pointcolor).pickable(0)
                if self.splined:
                    self.spline = Spline(self.cpoints, res=len(self.cpoints)*4) # not closed here
                else:
                    self.spline = Line(self.cpoints)

                if evt.actor:
                    self.top_pts.append(evt.picked3d)
                    # self.topline = Line(self.top_pts)
                    # self.topline.lw(self.linewidth-1).c(self.linecolor).pickable(False)
                    self.topline = Points(self.top_pts, r=self.linewidth)
                    self.topline.c(self.linecolor).pickable(False)

                self.spline.lw(self.linewidth).c(self.linecolor).pickable(False)
                self.txt2d.background(self.linecolor)
                self.jline = Line(self.cpoints[0], self.cpoints[-1], lw=1, c=self.linecolor).pickable(0)
                self.add([self.points, self.spline, self.jline, self.topline])

    def _onKeyPress(self, evt):
        if evt.keyPressed.lower() == 'z' and self.spline: # Cut mesh with a ribbon-like surface
            inv = False
            if evt.keyPressed == 'Z':
                inv = True
            self.txt2d.background('red8').text("  ... working ...  ")
            self.render()
            self.mesh_prev = self.mesh.clone()
            tol = self.mesh.diagonalSize()/2            # size of ribbon (not shown)
            pts = self.spline.points()
            n = fitPlane(pts, signed=True).normal       # compute normal vector to points
            rb = Ribbon(pts - tol*n, pts + tol*n, closed=True)
            self.mesh.cutWithMesh(rb, invert=inv)       # CUT
            self.txt2d.text(self.msg)                   # put back original message
            if self.drawmode:
                self._onRightClick(evt)                 # toggle mode to normal
            else:
                self.txt2d.background(self.color, self.alpha)
            self.remove([self.spline, self.points, self.jline, self.topline]).render()
            self.cpoints, self.points, self.spline = [], None, None
            self.top_pts, self.topline = [], None

        elif evt.keyPressed == 'L':
            self.txt2d.background('red8')
            self.txt2d.text(" ... removing smaller ... \n ... parts of the mesh ... ")
            self.render()
            self.remove(self.mesh)
            self.mesh_prev = self.mesh
            mcut = self.mesh.extractLargestRegion()
            mcut.filename = self.mesh.filename          # copy over various properties
            mcut.name = self.mesh.name
            mcut.scalarbar= self.mesh.scalarbar
            mcut.info = self.mesh.info
            self.mesh = mcut                            # discard old mesh by overwriting it
            self.txt2d.text(self.msg).background(self.color)   # put back original message
            self.add(mcut)

        elif evt.keyPressed == 'u':                     # Undo last action
            if self.drawmode:
                self._onRightClick(evt)                 # toggle mode to normal
            else:
                self.txt2d.background(self.color, self.alpha)
            self.remove([self.mesh, self.spline, self.jline, self.points, self.topline])
            self.mesh = self.mesh_prev
            self.cpoints, self.points, self.spline = [], None, None
            self.top_pts, self.topline = [], None
            self.add(self.mesh)

        elif evt.keyPressed == 'c' or evt.keyPressed == 'Delete':
            # clear all points
            self.remove([self.spline, self.points, self.jline, self.topline]).render()
            self.cpoints, self.points, self.spline = [], None, None
            self.top_pts, self.topline = [], None

        elif evt.keyPressed == 'r': # reset camera and axes
            try:
                self.remove(self.axes_instances[0])
                self.axes_instances[0] = None
                self.addGlobalAxes(axtype=1, c=None)
                self.renderer.ResetCamera()
                self.interactor.Render()
            except:
                pass

        elif evt.keyPressed == 's':
            if self.mesh.filename:
                fname = os.path.basename(self.mesh.filename)
                fname, extension = os.path.splitext(fname)
                fname = fname.replace("_edited","")
                fname = f"{fname}_edited{extension}"
            else:
                fname="mesh_edited.vtk"
            self.write(fname)

    def write(self, filename="mesh_edited.vtk"):
        """Save the resulting mesh to file"""
        self.mesh.write(filename)
        logger.info(f"\save saved to file {filename}")
        return self

    def start(self, *args, **kwargs):
        """Start window interaction (with mouse and keyboard)"""
        acts = [self.txt2d, self.mesh, self.points, self.spline, self.jline]
        self.show(acts + list(args), **kwargs)
        return self