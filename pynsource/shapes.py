#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import wx
import wx.lib.ogl as ogl
from pynsource import config

class DiamondShape(ogl.PolygonShape):
    def __init__(self, w=0.0, h=0.0):
        ogl.PolygonShape.__init__(self)
        if w == 0.0:
            w = 60.0
        if h == 0.0:
            h = 60.0

        points = [ (0.0,    -h/2.0),
                   (w/2.0,  0.0),
                   (0.0,    h/2.0),
                   (-w/2.0, 0.0),
                   ]

        self.Create(points)


#----------------------------------------------------------------------

class RoundedRectangleShape(ogl.RectangleShape):
    def __init__(self, w=0.0, h=0.0):
        ogl.RectangleShape.__init__(self, w, h)
        self.SetCornerRadius(-0.3)


#----------------------------------------------------------------------

class CompositeDivisionShape(ogl.CompositeShape):
    def __init__(self, canvas):
        ogl.CompositeShape.__init__(self)

        self.SetCanvas(canvas)

        # create a division in the composite
        self.MakeContainer()

        # add a shape to the original division
        shape2 = ogl.RectangleShape(40, 60)
        self.GetDivisions()[0].AddChild(shape2)

        # now divide the division so we get 2
        self.GetDivisions()[0].Divide(wx.HORIZONTAL)

        # and add a shape to the second division (and move it to the
        # centre of the division)
        shape3 = ogl.CircleShape(40)
        shape3.SetBrush(wx.CYAN_BRUSH)
        self.GetDivisions()[1].AddChild(shape3)
        shape3.SetX(self.GetDivisions()[1].GetX())

        for division in self.GetDivisions():
            division.SetSensitivityFilter(0)
        
#----------------------------------------------------------------------

class CompositeShape(ogl.CompositeShape):
    def __init__(self, canvas):
        ogl.CompositeShape.__init__(self)

        self.SetCanvas(canvas)

        constraining_shape = ogl.RectangleShape(120, 100)
        constrained_shape1 = ogl.CircleShape(50)
        constrained_shape2 = ogl.RectangleShape(80, 20)

        constraining_shape.SetBrush(wx.BLUE_BRUSH)
        constrained_shape2.SetBrush(wx.RED_BRUSH)
        
        self.AddChild(constraining_shape)
        self.AddChild(constrained_shape1)
        self.AddChild(constrained_shape2)

        constraint = ogl.Constraint(ogl.CONSTRAINT_MIDALIGNED_BOTTOM, constraining_shape, [constrained_shape1, constrained_shape2])
        self.AddConstraint(constraint)
        self.Recompute()

        # If we don't do this, the shapes will be able to move on their
        # own, instead of moving the composite
        constraining_shape.SetDraggable(False)
        constrained_shape1.SetDraggable(False)
        constrained_shape2.SetDraggable(False)

        # If we don't do this the shape will take all left-clicks for itself
        constraining_shape.SetSensitivityFilter(0)

        
#----------------------------------------------------------------------

class DividedShape(ogl.DividedShape):
    def __init__(self, width, height, canvas):
        ogl.DividedShape.__init__(self, width, height)
        if config.UML_STYLE_1:
            self.BuildRegions(canvas)

    def BuildRegions(self, canvas):
        region1 = ogl.ShapeRegion()
        region1.SetText('DividedShape')
        region1.SetProportions(0.0, 0.2)
        region1.SetFormatMode(ogl.FORMAT_CENTRE_HORIZ)
        self.AddRegion(region1)

        region2 = ogl.ShapeRegion()
        region2.SetText('This is Region number two.')
        region2.SetProportions(0.0, 0.3)
        region2.SetFormatMode(ogl.FORMAT_NONE)
        #region2.SetFormatMode(ogl.FORMAT_CENTRE_HORIZ|ogl.FORMAT_CENTRE_VERT)
        self.AddRegion(region2)

        region3 = ogl.ShapeRegion()

        region3.SetText("blah\nblah\nblah blah")
        region3.SetProportions(0.0, 0.5)
        region3.SetFormatMode(ogl.FORMAT_NONE)
        self.AddRegion(region3)

        # Andy Added
        self.region1 = region1   # for external access...
        self.region2 = region2   # for external access...
        self.region3 = region3   # for external access...

        self.SetRegionSizes()
        self.ReformatRegions(canvas)


    def FlushText(self):
        # Taken from Boa
        """This method retrieves the text from the shape
        regions and draws it. There seems to be a problem that
        the text is not normally drawn. """
        canvas = self.GetCanvas()
        dc = wx.ClientDC(canvas)
        canvas.PrepareDC(dc)
        count = 0
        for region in self.GetRegions():
            region.SetFormatMode(4)
            self.FormatText(dc, region.GetText(), count)
            count = count + 1

    def ReformatRegions(self, canvas=None):
        rnum = 0
        if canvas is None:
            canvas = self.GetCanvas()
        dc = wx.ClientDC(canvas)  # used for measuring
        for region in self.GetRegions():
            text = region.GetText()
            self.FormatText(dc, text, rnum)
            rnum += 1


    def OnSizingEndDragLeft(self, pt, x, y, keys, attch):
        ogl.DividedShape.OnSizingEndDragLeft(self, pt, x, y, keys, attch)
        self.SetRegionSizes()
        self.ReformatRegions()
        self.GetCanvas().Refresh()


class DividedShapeSmall(DividedShape):
    def __init__(self, width, height, canvas):
        DividedShape.__init__(self, width, height, canvas)

    def BuildRegions(self, canvas):
        region1 = ogl.ShapeRegion()
        region1.SetText('wxDividedShapeSmall')
        region1.SetProportions(0.0, 0.9)
        region1.SetFormatMode(ogl.FORMAT_CENTRE_HORIZ)
        self.AddRegion(region1)

        self.region1 = region1   # for external access...

        self.SetRegionSizes()
        self.ReformatRegions(canvas)

    def ReformatRegions(self, canvas=None):
        rnum = 0
        if canvas is None:
            canvas = self.GetCanvas()
        dc = wx.ClientDC(canvas)  # used for measuring
        for region in self.GetRegions():
            text = region.GetText()
            self.FormatText(dc, text, rnum)
            rnum += 1

    def OnSizingEndDragLeft(self, pt, x, y, keys, attch):
        #self.base_OnSizingEndDragLeft(pt, x, y, keys, attch)
        ogl.DividedShape.OnSizingEndDragLeft(self, pt, x, y, keys, attch)
        self.SetRegionSizes()
        self.ReformatRegions()
        self.GetCanvas().Refresh()


if __name__ == '__main__':
    pass

