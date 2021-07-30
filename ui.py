import pymel.core as pm
import maya.api.OpenMaya as newOM
import maya.api.OpenMayaUI as newOMUI

from PySide2.QtCore import *
from PySide2.QtUiTools import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from shiboken2 import wrapInstance

def maya_useNewAPI():
    """
    So that we can use the Python API 2.0

    :return:
    """
    pass

def get_active_viewport(as_qt_object=False):
    """
    Returns the currently active viewport, or None

    :return:
    """
    if as_qt_object:
        active_view = newOMUI.M3dView.active3dView()
        view_widget = wrapInstance(long(active_view.widget()), QWidget)
        return view_widget
    try:
        return pm.modelPanel(pm.getPanel(withFocus=True), query=True)
    except:
        return None

def get_status_line():
    """
    Returns the end of the status line as a Qt Object

    :return:
    """
    status_line = pm.windows.toQtObject("StatusLine|MainStatusLineLayout|formLayout4|flowLayout1")
    return status_line
