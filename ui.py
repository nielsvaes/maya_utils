import pymel.core as pm
import maya.api.OpenMayaUI as newOMUI

from PySide2.QtWidgets import *
from shiboken2 import wrapInstance

import sys
if sys.version_info.major > 2:
    long = int


def get_active_viewport(as_qt_object=False):
    """
    Returns the currently active viewport, or None

    :return:
    """
    active_view = newOMUI.M3dView.active3dView()
    view_widget = wrapInstance(long(active_view.widget()), QWidget)
    if as_qt_object:
        return view_widget

    pw = view_widget.parentWidget()
    return pm.ui.ModelPanel(pw.objectName())


def get_status_line():
    """
    Returns the end of the status line as a Qt Object

    :return:
    """
    status_line = pm.windows.toQtObject("StatusLine|MainStatusLineLayout|formLayout4|flowLayout1")
    return status_line
