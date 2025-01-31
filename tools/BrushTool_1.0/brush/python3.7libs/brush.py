import hou


class Brush():
    _radius = 0.1
    _brush_opacity =   0.5
    _smooth_opacity = 0.25
    _separate_move = 4
    
    _doreflect = False
    _symaxis = (1, 0, 0)
    _symorig = (0, 0 ,0)
    _symthreshold = 0.0001

    hit_point = hit_point_string = hit_edge = hit_prim = None
    last_mouse_move_x = last_mouse_move_y = None

    radius_drawable_geo = hou.Geometry()    
    circle = hou.sopNodeTypeCategory().nodeVerb("circle")
    circle.setParms({ "type": 2 })
    circle.execute(radius_drawable_geo, [])
    del circle
    radius_drawable_params = { "color1": hou.Color(1, 0.9, 0.3), "style": hou.drawableGeometryLineStyle.Plain, "line_width": hou.ui.scaledSize(1) }

    @staticmethod
    def tool():
        scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if scene_viewer.currentState() != "brush":
            sop = None
            cur_node = scene_viewer.currentNode()

            if cur_node.type().category() == hou.sopNodeTypeCategory():
                sop = cur_node.parent().displayNode()
                
            else:
                sel = hou.selectedNodes()
                if sel and sel[0].type().childTypeCategory() == hou.sopNodeTypeCategory():
                    sop = sel[0].displayNode()

            if sop is not None:
                with hou.undos.group("Brush Tool"):
                    if not sop.isSelected():
                        sop.setCurrent(True, True)

                    with hou.RedrawBlock() as rb:
                        scene_viewer.constructionPlane().setIsVisible(False)
                        state = scene_viewer.currentState()

                        if scene_viewer.curViewport().type() == hou.geometryViewportType.UV:
                            if state != "uvbrush":
                                if sop.type().name() == "uvbrush":
                                    sop.parm("flood").pressButton()
                                    sop.parm("group").set("")
                                    scene_viewer.enterCurrentNodeState()
                                else:
                                    sop = sop.createOutputNode("uvbrush")
                                    sop.setCurrent(True, True)
                                    sop.setDisplayFlag(True)
                                    sop.setRenderFlag(True)
                                    scene_viewer.enterCurrentNodeState()

                        elif state != "brush":
                            edit_sop = None
                            if sop.type().name() == "edit":
                                scene_viewer.enterViewState()
                                hou.ui.waitUntil(lambda: True)
                                sop = scene_viewer.pwd().displayNode()
                                if sop.type().name() == "edit":
                                    edit_sop = sop
                                    edit_sop.parm("apply").pressButton()
                                    edit_sop.setParms({ "grouptype": 3, "xformspace": 0, "slideonsurface": False, "switcher1": 0, "modeswitcher1": 0, "rad": Brush._radius, "distmetric": Brush._separate_move })
                                    edit_sop.setHighlightFlag(False)

                            if edit_sop is None:
                                edit_sop = sop.createOutputNode("edit")
                                edit_sop.setParms({ "grouptype": 3, "rad": Brush._radius, "distmetric": Brush._separate_move })
                                edit_sop.setDisplayFlag(True)
                                edit_sop.setCurrent(True, True)

                            # SYM
                            edit_sop.parm("doreflect").set(Brush._doreflect)
                            edit_sop.parmTuple("symaxis").set(Brush._symaxis)
                            edit_sop.parmTuple("symorig").set(Brush._symorig)
                            edit_sop.parm("symthreshold").set(Brush._symthreshold)

                            Brush.geo = edit_sop.geometry()
                            edit_sop.setDisplayFlag(True)
                            Brush.sop = edit_sop
                            hou.ui.waitUntil(lambda: True)
                            scene_viewer.setCurrentState("brush")


    def __init__(self, scene_viewer, state_name):
        self.scene_viewer = scene_viewer
        self.radius_drawable = hou.SimpleDrawable(self.scene_viewer, self.radius_drawable_geo, "mb_radius_circle")
        self.radius_drawable.enable(True)
        self.mode = 0
        self._initial_clickdeadzone = hou.getPreference("general.clickdeadzone.val")


    def onGenerate(self, kwargs):
        self.xform = self.sop.creator().worldTransform()
        self.xform_inverted = self.xform.inverted()
        self.xform_transposed = self.xform.transposed()
        self.viewport = self.scene_viewer.curViewport()

        hud_template = {
            "title": "Brush", "icon": "Brush_icon",
            "rows" : [
                        {"id": "op", "label": ""},

                        {"label": "Move Points", "key": "LMB"},
                        {"label": "Smooth Points", "key": "Shift+LMB"},
                        {"label": "Change Radius", "key": "MMB / mousewheel"},
                     ]
                    }

        self.scene_viewer.hudInfo(show=True, template=hud_template, panel=hou.hudPanel.ToolInfo)
        self.disable_clickdeadzone()
        


    def intersect_plane(self, plane_point, plane_normal, line_origin, line_dir):
        try:
            return hou.hmath.intersectPlane(plane_point, plane_normal, line_origin, line_dir)
        except TypeError:
            return line_origin - line_dir * (line_origin - plane_point).dot(line_dir)


    def enable_clickdeadzone(self):
        hou.setPreference("general.clickdeadzone.val", self._initial_clickdeadzone)


    def disable_clickdeadzone(self):
        hou.setPreference("general.clickdeadzone.val", "0")


    def onExit(self, kwargs):
        try:
            if self.sop.cookCount() < 4:
                self.sop.destroy()
            else:
                self.sop.setHighlightFlag(True)

                Brush._doreflect = self.sop.evalParm("doreflect")
                Brush._symaxis = self.sop.evalParmTuple("symaxis")
                Brush._symorig = self.sop.evalParmTuple("symorig")
                Brush._symthreshold = self.sop.evalParm("symthreshold")

        except hou.ObjectWasDeleted:
            pass

        self.radius_drawable.enable(False)
        Brush.geo = None
        self.enable_clickdeadzone()


    def onInterrupt(self, kwargs):
        self.radius_drawable.show(False)
        self.enable_clickdeadzone()


    def onResume(self, kwargs):
        self.viewport = self.scene_viewer.curViewport()
        self.disable_clickdeadzone()


    def hit(self):
        xform_inverted_transposed = self.viewport.viewTransform().inverted().transposed()
        self._view_normal = hou.Vector3(0.0, 0.0, 1.0) * xform_inverted_transposed
        self._view_normal_local = self._view_normal * self.xform_transposed
        self._view_right = hou.Vector3(1.0, 0.0, 0.0) * xform_inverted_transposed 
        self._view_right_local = self._view_right * self.xform_transposed
        self.hit_point = self.hit_point_string = self.hit_edge = self.hit_prim = None
        self._cursor_origin, self._cursor_dir = self.event.ray()
        self.hit_normal = hou.Vector3()
        self.hit_uvw = hou.Vector3()
        self._start_intersection = hou.Vector3()
        intersected = self.geo.intersect(self._cursor_origin, self._cursor_dir, self._start_intersection, self.hit_normal, self.hit_uvw)

        if intersected > -1:
            self.hit_prim_int = intersected
            self.hit_pos = self._start_intersection
            self.hit_prim = self.geo.prim(intersected)
            prim_points = self.hit_prim.points()
            points_count = len(prim_points)
            d = 999999.0
            nearest_id = -1
            for i in range(points_count):
                pos = prim_points[i].position()
                d1 = self._start_intersection.distanceTo(pos)
                if d1 < d:
                    d = d1
                    nearest_id = i

            self.hit_point = prim_points[nearest_id]
            last_id = points_count - 1
            
            if nearest_id == 0:
                nb1 = last_id
                nb2 = 1
            elif nearest_id == last_id:
                nb1 = nearest_id - 1
                nb2 = 0
            else:
                nb1 = nearest_id - 1
                nb2 = nearest_id + 1

            hit_point_pos = self.hit_point.position()
            self.hit_point_string = str(self.hit_point.number())

            if self.hit_prim.isClosed():
                nb1 = prim_points[nb1]
                nb2 = prim_points[nb2]
                nb1_pos = nb1.position()
                nb2_pos = nb2.position()
                d1 = self._start_intersection.distanceToSegment(hit_point_pos, nb1_pos)
                d2 = self._start_intersection.distanceToSegment(hit_point_pos, nb2_pos)
                if d1 < d2:
                    self.hit_edge = self.geo.findEdge(self.hit_point, nb1)
                else:
                    self.hit_edge = self.geo.findEdge(self.hit_point, nb2)

            if self.sop.evalParm("doreflect"):
                sym_origin = hou.Vector3(self.sop.evalParmTuple("symorig"))
                self._sym_dir = hou.Vector3(self.sop.evalParmTuple("symaxis"))
                
                i = self.intersect_plane(sym_origin, self._sym_dir, hit_point_pos, -self._sym_dir)
                d = i.distanceTo(hit_point_pos)

                dot = self._view_normal_local.dot(self._sym_dir)

                if d < 0.0001 or ( dot > 0.8 and (d < self.sop.evalParm("rad")) ):
                    self._is_sym =  True
                else:
                    self._is_sym =  False

            else:
                self._is_sym = False
        else:
            self.hit_point = None

        self._update_radius()
        self.mode = 0


    def onMouseEvent(self, kwargs):
        self.event = kwargs["ui_event"]
        reason = self.event.reason()

        if reason == hou.uiEventReason.Located:
            if self.event.device().mouseX() != self.last_mouse_move_x or self.event.device().mouseY() != self.last_mouse_move_y: 
                self.last_mouse_move_x = self.event.device().mouseX()
                self.last_mouse_move_y = self.event.device().mouseY()
                self.hit()

        elif reason == hou.uiEventReason.Active:
            if self.mode == 1:
                o, d = self.event.ray()
                intersection = self.intersect_plane(self._start_intersection, self._view_normal_local, o, d)
                if self._is_sym:
                    intersection = self.intersect_plane(self._start_intersection, self._sym_dir, intersection, self._sym_dir)                    
                self.sop.parmTuple("t").set( (intersection - self._start_intersection) * self.__class__._brush_opacity )

            elif self.mode == 2:
                hit_normal = hou.Vector3()
                hit_uvw = hou.Vector3()
                hit_pos = hou.Vector3()
                prim_int = self.geo.intersect(*self.event.ray(), hit_pos, hit_normal, hit_uvw)
                if prim_int > -1:
                    self.sop.parmTuple("dir").set(hit_normal)
                    self.sop.parmTuple("hitpos").set(hit_pos)
                    self.sop.parm("hitprim").set(prim_int)
                    self.sop.parmTuple("hituvw").set(hit_uvw)

            elif self.mode == 3:
                o, d = self.event.ray()
                intersection = self.intersect_plane(self._start_intersection, self._view_normal_local, o, d)
                offset = intersection - self._start_intersection
                self.__class__._radius = max(self._pre_radius + offset.dot(self._view_right_local), 0.0001)
                self._update_radius()

        elif reason == hou.uiEventReason.Start and self.hit_point is not None:
            device = self.event.device()

            if device.isLeftButton():
                self.scene_viewer.beginStateUndo("Brush Operation")

                if device.isShiftKey():
                    tablet_pressure = device.tabletPressure()
                    opacity = tablet_pressure * self.__class__._smooth_opacity * (4 if tablet_pressure < 1 else 1)
                    
                    self.sop.setParms({ "modeswitcher1": 1, "group": "", "op": 1, "sculptrad": self.__class__._radius })
                    self.sop.parm("opacity").set(opacity)
                    self.sop.parmTuple("dir").set(self.hit_normal)
                    self.sop.parmTuple("hitpos").set(self._start_intersection)
                    self.sop.parm("hitprim").set(self.hit_prim_int)
                    self.sop.parmTuple("hituvw").set(self.hit_uvw)
                    self.sop.parm("event").set(1)
                    self.mode = 2
                else:
                    self.sop.setParms({ "group": self.hit_point_string, "rad": self.__class__._radius })
                    self.mode = 1

                self.radius_drawable.show(False)

            elif device.isMiddleButton():
                self._pre_radius = self.__class__._radius
                self.mode = 3

            else:
                self.mode = 0

        elif reason == hou.uiEventReason.Changed:
            if self.mode == 1:
                self.sop.parm("apply").pressButton()
                self.sop.setParms({ "grouptype": 3, "switcher1": 0, "slideonsurface": False })
                self.scene_viewer.endStateUndo()
            
            elif self.mode == 2:
                self.sop.setParms({ "event": 2, "event": 4, "modeswitcher1": 0 })
                self.scene_viewer.endStateUndo()

            self.mode = 0

            self.hit()


    def onMouseWheelEvent(self, kwargs):
        if self.hit_point is not None:
            with hou.undos.disabler():
                self.__class__._radius = self.__class__._radius + hou.hmath.sign( kwargs["ui_event"].device().mouseWheel() ) * self.__class__._radius / 10.0
                self._update_radius()


    def _update_radius(self):
        if self.hit_point is not None:
            x, y = self.viewport.mapToScreen(self._start_intersection * self.xform + self._view_right * self.__class__._radius)
            cpos = (self._cursor_origin * self.xform + self._cursor_dir * self.xform_inverted.transposed() * 0.01)
            rot = hou.Vector3(0, 0, 1).matrixToRotateTo(self._view_normal_local * self.xform_inverted.transposed())
            viewport_rot_xform = hou.Matrix4(self.viewport.viewTransform().extractRotationMatrix3())
            d_, o_ = self.viewport.mapToWorld(x, y)
            scale = cpos.distanceTo(o_ + d_ * 0.01)
            xform = hou.hmath.identityTransform() * rot * viewport_rot_xform.inverted() * hou.hmath.buildScale(scale, scale, 0.0001) * viewport_rot_xform * hou.hmath.buildTranslate(cpos)
            self.radius_drawable.setTransform(xform)
            self.radius_drawable.show(True)
        else:
            self.radius_drawable.show(False)

    def _fix_symmetry(self):
        cur_node = self.scene_viewer.currentNode()
        if cur_node.type().name() == "edit":
            with hou.RedrawBlock() as rb:
                orig = cur_node.evalParmTuple("symorig")
                axis = cur_node.evalParmTuple("symaxis")
                clip = cur_node.createOutputNode("clip")
                clip.parmTuple("origin").set(orig)
                clip.parmTuple("dir").set(axis)
                mirror = clip.createOutputNode("mirror")
                mirror.parmTuple("origin").set(orig)
                mirror.parmTuple("dir").set(axis)
                mirror.setCurrent(True, True)
                mirror.setDisplayFlag(True)
                Brush.tool()

    def _symmetry_set_origin(self):
        try:
            gs = self.scene_viewer.selectGeometry(prompt="Select points. Their center will be used as symmetry origin.", geometry_types=(hou.geometryType.Points,), quick_select=False, use_existing_selection=False)
            origin = gs.boundingBox().center()
            Brush._symorig = origin
        except:
            Brush._symorig = (0, 0, 0)

        Brush.tool()


    def onParmChangeEvent(self, kwargs):
        parm_name = kwargs['parm_name']
        state_parms = kwargs['state_parms']

        if parm_name == "move_intensity_0_25":
            state_parms["move_intensity"]["value"] = 0.25
            self.__class__._brush_opacity = 0.25

        elif parm_name == "move_intensity_0_5":
            state_parms["move_intensity"]["value"] = 0.5
            self.__class__._brush_opacity = 0.5

        elif parm_name == "move_intensity_0_75":
            state_parms["move_intensity"]["value"] = 0.75
            self.__class__._brush_opacity = 0.75

        elif parm_name == "move_intensity_1":
            state_parms["move_intensity"]["value"] = 1.0
            self.__class__._brush_opacity = 1.0

        elif parm_name == "smooth_intensity_0_25":
            state_parms["smooth_intensity"]["value"] = 0.25
            self.__class__._smooth_opacity = 0.25

        elif parm_name == "smooth_intensity_0_5":
            state_parms["smooth_intensity"]["value"] = 0.5
            self.__class__._smooth_opacity = 0.5

        elif parm_name == "smooth_intensity_0_75":
            state_parms["smooth_intensity"]["value"] = 0.75
            self.__class__._smooth_opacity = 0.75

        elif parm_name == "smooth_intensity_1":
            state_parms["smooth_intensity"]["value"] = 1.0
            self.__class__._smooth_opacity = 1.0

        elif parm_name == "move_intensity":
            self.__class__._brush_opacity = kwargs['parm_value']

        elif parm_name == "smooth_intensity":
            self.__class__._smooth_opacity = kwargs['parm_value']

        elif parm_name == "separate_move":
            if kwargs["parm_value"]:
                self.__class__._separate_move = 4
            else:
                self.__class__._separate_move = 2

            self.sop.parm("distmetric").set(self.__class__._separate_move)

        elif parm_name == "x_symmetry":
            self.sop.parm("doreflect").set(True)
            self.sop.parmTuple("symaxis").set((1, 0, 0))
        
        elif parm_name == "y_symmetry":
            self.sop.parm("doreflect").set(True)
            self.sop.parmTuple("symaxis").set((0, 1, 0))

        elif parm_name == "z_symmetry":
            self.sop.parm("doreflect").set(True)
            self.sop.parmTuple("symaxis").set((0, 0, 1))

        elif parm_name == "symmetry_set_origin":
            if self.sop.evalParm("doreflect"):
                hou.ui.postEventCallback(self._symmetry_get_origin)

        elif parm_name == "symmetry_off":
            self.sop.parm("doreflect").set(False)
        
        elif parm_name == "fix_symmetry":
            if self.sop.evalParm("doreflect"):
                self.scene_viewer.setCurrentState("select")
                hou.ui.postEventCallback(self._fix_symmetry)

template = hou.ViewerStateTemplate("brush", "Brush", hou.sopNodeTypeCategory())
template.bindFactory(Brush)
template.bindIcon("BRUSH_icon")
template.bindParameter( hou.parmTemplateType.Toggle, name="separate_move", label="Move Separately", default_value=Brush._separate_move )
template.bindParameter( hou.parmTemplateType.Float, name="move_intensity", label="Intensity", min_limit=0.0, max_limit=1.0, default_value=Brush._brush_opacity )
template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_0_25", label="0.25", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_0_5", label="0.5", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_0_75", label="0.75", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_1", label="1.0", align=True )
template.bindParameter( hou.parmTemplateType.Float, name="smooth_intensity", label="Smooth Intensity", min_limit=0.0, max_limit=1.0, default_value=Brush._smooth_opacity )
template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_0_25", label="0.25", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_0_5", label="0.5", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_0_75", label="0.75", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_1", label="1.0" )

template.bindParameter( hou.parmTemplateType.Button, name="x_symmetry", label="X Sym", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="y_symmetry", label="Y Sym", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="z_symmetry", label="Z Sym", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="symmetry_set_origin", label="Set Origin", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="symmetry_off", label="Sym Off", align=True )
template.bindParameter( hou.parmTemplateType.Button, name="fix_symmetry", label="Fix Sym", align=True )

hou.ui.registerViewerState(template)
