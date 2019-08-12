# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2018 - Bernd Hahnebach <bernd@bimstatik.org>            *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""
# got to the directory of this script and run
python3 main.py

http://localhost:8888/

# make code formating and check pep8 Python style guide
black main.py
flake8 main.py --max-line-length=100

"""

import os

import tornado.ioloop
import tornado.web


# get temporary directory
from tempfile import gettempdir  # returns /tmp on my linux machine

global TMP_DIR
TMP_DIR = gettempdir()


# get the document name for FreeCAD, will be file name for FreeCAD and IFC
def get_doc_name():
    return "Columngrid"


# get the file path, where to save the FreeCAD file and IFC
def get_file_path(file_name, user_id, ending):
    return os.path.join(TMP_DIR, file_name + "_" + user_id + ending)


# set path to FreeCAD
def add_fc_to_path():
    import sys
    from platform import system

    if system() == "Linux":
        sys.path.append("/usr/local/lib")  # path to FreeCAD.so
    elif system() == "Windows":
        sys.path.append(
            "C:/0_BHA_privat/progr/FreeCAD_0.19.xxxxx_Py3Qt5/bin"
        )  # path to FreeCAD.pyd
        sys.path.append(
            "C:/0_BHA_privat/progr/FreeCAD_0.19.xxxxx_Py3Qt5/bin/Lib/site-packages"
        )  # path to ifcopenshell package
    else:
        print("Not supported operating system.\n")
        return


# a class to make it a bit easier to access all the input data
class ColumnGridData:
    def __init__(self, h, wx, wy, dx, dy, nx, ny):
        self.h = h
        self.wx = wx
        self.wy = wy
        self.dx = dx
        self.dy = dy
        self.nx = nx
        self.ny = ny


def run_columngrid(cgd):
    _h = cgd.h
    _w1 = cgd.wx
    _w2 = cgd.wy
    _ax = cgd.dx
    _ay = cgd.dy
    _nx = cgd.nx
    _ny = cgd.ny

    add_fc_to_path()
    import FreeCAD
    import Arch
    import exportIFC

    # get doc name and doc dir
    from uuid import uuid4

    _user_id = str(uuid4())[-12:]
    _doc_name = get_doc_name()
    _doc_path_ifc = get_file_path(_doc_name, _user_id, ".ifc")
    _doc_path_freecad = get_file_path(_doc_name, _user_id, ".FCStd")

    # create a new FreeCAD document, to have something to put the objects in
    doc_obj = FreeCAD.newDocument(_doc_name)

    # a list to put the objects in which will be exported to ifc
    obj_ifc = []

    # add some columns to the document
    for ix in range(_nx):
        for iy in range(_ny):
            col = Arch.makeStructure(None, length=_w1, width=_w2, height=_h)
            col.Placement.Base = FreeCAD.Vector(ix * _ax, iy * _ay, 0.0)
            obj_ifc.append(col)

    # recompute the document
    doc_obj.recompute()

    # export objects to ifc
    exportIFC.export(obj_ifc, _doc_path_ifc)

    # save and close document
    doc_obj.saveAs(_doc_path_freecad)
    FreeCAD.closeDocument(_doc_name)

    print("Done: run_columngrid()")
    return _user_id


# tornado event handlers
class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class FreeCADInputHandler(tornado.web.RequestHandler):
    def get(self):

        # get the input data
        cgd = ColumnGridData(
            h=self.get_argument("height"),
            wx=self.get_argument("width1"),
            wy=self.get_argument("width2"),
            dx=self.get_argument("distancex"),
            dy=self.get_argument("distancey"),
            nx=self.get_argument("countx"),
            ny=self.get_argument("county"),
        )

        cgd.h = float(cgd.h)
        cgd.wx = float(cgd.wx)
        cgd.wy = float(cgd.wy)
        cgd.dx = float(cgd.dx)
        cgd.dy = float(cgd.dy)
        cgd.nx = int(cgd.nx)
        cgd.ny = int(cgd.ny)

        print("Input values will be taken as they have been input!")
        column_count = cgd.nx * cgd.ny

        # run column grid script
        # this takes time, some other widget with saying how long to wait would be cool
        user_id = run_columngrid(cgd)

        # render output
        self.render(
            "columngrid.html",
            ncol=column_count,
            h=cgd.h,
            w1=cgd.wx,
            w2=cgd.wy,
            ax=cgd.dx,
            ay=cgd.dy,
            nx=cgd.nx,
            ny=cgd.ny,
            val_userid=user_id,
        )


class FileDownloadHandler(tornado.web.RequestHandler):
    def initialize(self, ending):
        self.ending = ending

    def get(self):

        # get user_id and _file_data
        user_id = self.get_argument("userid")
        _file_name = get_doc_name()
        _file_path = get_file_path(_file_name, user_id, self.ending)
        if not _file_name or not os.path.exists(_file_path):
            raise HTTPError(404)

        self.set_header("Content-Type", "application/force-download")
        self.set_header(
            "Content-Disposition",
            "attachment; filename={}{}".format(_file_name, self.ending),
        )

        with open(_file_path, "rb") as f:
            try:
                while True:
                    _buffer = f.read(4096)
                    if _buffer:
                        self.write(_buffer)
                    else:
                        f.close()
                        self.finish()
                        return
            except:
                raise HTTPError(404)
        raise HTTPError(500)


if __name__ == "__main__":
    app = tornado.web.Application(
        handlers=[
            (r"/", IndexHandler),
            (r"/columngrid", FreeCADInputHandler),
            (r"/download/fcstd", FileDownloadHandler, {"ending": ".FCStd"}),
            (r"/download/ifc", FileDownloadHandler, {"ending": ".ifc"}),
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # boilerplate code for tornado
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
