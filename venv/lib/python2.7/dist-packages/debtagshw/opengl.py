# debtagshw: lib to detect what hardware tags apply to the current system
#
# Copyright (C) 2012  Canonical
#
# Author:
#  Michael Vogt <mvo@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import print_function

import logging
import multiprocessing
import os
import sys

LOG=logging.getLogger(__name__)

class OpenGLError(Exception):
    pass

class OpenGL(object):

    # 3d driver detection data, map render/vendor string to driver
    RENDERER_TO_DRIVER = [
        # from tools/unity_support_test.c in the nux-tools pkg
        ("Software Rasterizer", "sw"),
        ("Mesa X11", "sw"),
        ("on softpipe", "sw"),
        ("on llvmpipe", "sw"),
        # real drivers
        ("AMD", "amd"),
        ("Intel(R)", "intel"),
    ]

    VENDOR_TO_DRIVER = [
        ("nouveau", "nouveau"),
        ("NVIDIA Corporation", "nvidia"),
        # this is strange, fglrxinfo returns this vendor
        ("Advanced Micro Devices, Inc.", "fglrx"),
        # but glxinfo/the ctypes based code this one, so we support both
        ("ATI Technologies Inc.", "fglrx"),
    ]

    # from /usr/include/GL/glx.h
    GLX_VENDOR=1
    GLX_VERSION=2
    GLX_EXTENSIONS=3

    # for the visinfo
    GLX_RGBA = 4
    GLX_RED_SIZE = 8
    GLX_GREEN_SIZE = 9
    GLX_BLUE_SIZE = 10
    GLX_DOUBLEBUFFER = 5

    # GL, from /usr/include/GL/gl.h
    GL_VENDOR = 0x1F00
    GL_RENDERER = 0x1F01
    GL_VERSION = 0x1F02
    GL_EXTENSIONS = 0x1F03

    def __init__(self, direct_rendering=True):
        self.direct = direct_rendering

    def _find_opengl_lib_path(self):
        """ This is a helper for the fglrx case """
        # fglrx puts its own libGL.so under a private directory and plays
        # tricks with  /etc/ld.so.conf.d/x86_64-linux-gnu_GL.conf to
        # make it the default libGL.so but apparently the cdll.LoadLibrary
        # does not support the ld.so.conf.d directory (yet?)
        if os.path.exists("/usr/lib/fglrx/libGL.so.1"):
            return "/usr/lib/fglrx/libGL.so.1"
        return "libGL.so.1"

    def _get_opengl_vendor_renderer_version_tuple(self):
        """ returns a vendor, renderer, version tuple """
        from ctypes import cdll, c_char, c_char_p, c_int, byref
        # load stuff
        x11 = cdll.LoadLibrary("libX11.so.6")
        glx = cdll.LoadLibrary(self._find_opengl_lib_path())
        # get display
        display = x11.XOpenDisplay("")
        if not display:
            return None, None, None
        # get extenstion
        dummy1 = c_char()
        dummy2 = c_char()
        res = glx.glXQueryExtension(display, byref(dummy1), byref(dummy2) )
        if not res:
            return None, None, None
        # get screen and window
        screen = x11.XDefaultScreen(display)
        root = x11.XRootWindow(display, screen)
        # create a window to make glGetString work
        attribSingleType = c_int * 8
        attribSingle = attribSingleType(
            self.GLX_RGBA,
            self.GLX_RED_SIZE, 1,
            self.GLX_GREEN_SIZE, 1,
            self.GLX_BLUE_SIZE, 1,
            0)
        visinfo = glx.glXChooseVisual(display, 0, attribSingle)
        if not visinfo:
            attribDoubleType = c_int * 9
            attribDouble = attribDoubleType(
                self.GLX_RGBA,
                self.GLX_RED_SIZE, 1,
                self.GLX_GREEN_SIZE, 1,
                self.GLX_BLUE_SIZE, 1,
                self.GLX_DOUBLEBUFFER,
                0)
            visinfo = glx.glXChooseVisual(display, 0, attribDouble)
        if not visinfo:
            raise OpenGLError("Can not get visinfo")
        # create context etc
        context = glx.glXCreateContext (display, visinfo, None, self.direct)
        if not context:
            raise OpenGLError("Can not create glx context")
        # make root current
        glx.glXMakeCurrent(display, root, context)
        # and get the actual useful gl data
        glx.glGetString.restype = c_char_p

        opengl_tuple = []
        for gl_item in ["vendor", "renderer", "version", "extensions"]:
            gl_hex = getattr(self, "GL_%s" % gl_item.upper())
            gl_string = glx.glGetString(gl_hex)
            if sys.version > '3':
                gl_string = gl_string.decode()
            if gl_item == "extensions":
                LOG.debug("gl %s: %s" % (gl_item, gl_string))
            else:
                LOG.info("gl %s: %s" % (gl_item, gl_string))
            opengl_tuple.append(gl_string)
        return opengl_tuple[:3]

    def opengl_driver(self):
        vendor, renderer, version = self._get_opengl_vendor_renderer_version_tuple()
        if not renderer:
            return "sw"
        # check the vendor string
        for search_str, driver in self.VENDOR_TO_DRIVER:
            if search_str in vendor:
                return driver
        # and the renderer too
        for search_str, driver in self.RENDERER_TO_DRIVER:
            if search_str in renderer:
                return driver
        return "unknown"

    def opengl_version(self):
        vendor, renderer, version = self._get_opengl_vendor_renderer_version_tuple()
        if not version:
            return "unknown"
        opengl_version = version.split(" ")[0]
        return opengl_version

    def opengl_supported(self):
        driver = self.opengl_driver()
        # sw driver is not good enough
        if driver == "sw":
            return False
        # stuff looks ok
        return True


# private helpers

def _apply_in_multiprocessing_pool(func):
    """ private helper to run the given func in a multiprocessing env
        to protect against segfaults in the ctypes code """
    # Launch in a seperate subprocess, since the ctypes opengl stuff might
    # be fragile (segfault happy). A multiprocessing.Pool would be easier,
    # but for me it caused "hangs" when the child segfaults, so use this
    # (rather more cumbersome) approach
    # multiprocessing is python 2.6+
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=func, args=(queue,))
    p.start()
    p.join()
    if p.exitcode < 0:
        LOG.warn("function: '%s' return exitcode '%s" % (func, p.exitcode))
    if queue.empty():
        return None
    return queue.get()
def _do_run_check(queue):
    """ private helper run inside the "Process" context for extra robustness
        against segfaults """
    oh = OpenGL()
    queue.put(oh.opengl_supported())
def _do_get_version(queue):
    """ private helper run inside the "Process" context for extra robustness
        against segfaults """
    oh = OpenGL()
    queue.put(oh.opengl_version())
def _do_get_driver(queue):
    """ private helper run inside the "Process" context for extra robustness
        against segfaults """
    oh = OpenGL()
    queue.put(oh.opengl_driver())

# public API
def run_check():
    """ get the current 3d driver or "unknown" """
    try:
        return _apply_in_multiprocessing_pool(_do_run_check)
    except OSError:
        return None

def get_driver():
    """ get the current 3d driver or "unknown" """
    try:
        return _apply_in_multiprocessing_pool(_do_get_driver)
    except OSError:
        return None

def get_version():
    """ Get the maximum opengl version supported or "unknown"

        Note that this is not a float number because values like
        4.2.2 are supported. It should probably be compared using
        something like apt_pkg.version_compare()
    """
    try:
        return _apply_in_multiprocessing_pool(_do_get_version)
    except OSError:
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    supported = run_check()
    driver = get_driver()
    version = get_version()
    print("opengl_supported: ", supported)
    print("opengl_driver: ", driver)
    print("opengl_version: ", version)
