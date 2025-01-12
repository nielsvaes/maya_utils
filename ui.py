import os
import base64

import pymel.core as pm
import maya.api.OpenMaya as newOM
import maya.api.OpenMayaUI as newOMUI
import tempfile

from PySide6.QtWidgets import *
from PySide6 import QtCore, QtGui
from shiboken6 import wrapInstance

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


def get_thumbnail_data(image_size=256):
    """
    Capture the current viewport as a jpeg image, and return the raw data from it.

    """
    view = newOMUI.M3dView.active3dView()

    image = newOM.MImage()
    image.create(view.portWidth(), view.portHeight())
    view.pushViewport(
        0, 0,
        view.portWidth(), view.portHeight()
    )
    view.refresh()

    view.readColorBuffer(image, True)
    view.popViewport()

    temp_file_cls = tempfile.NamedTemporaryFile()
    temp_file_path = "{}.jpeg".format(temp_file_cls.name)
    image.writeToFile(temp_file_path, outputFormat="jpeg")

    # crop to square
    q_img = QtGui.QImage(temp_file_path)
    crop_size = min(q_img.width(), q_img.height())
    cropped_rect = QtCore.QRect(
        (q_img.width() - crop_size) / 2,
        (q_img.height() - crop_size) / 2,
        crop_size,
        crop_size
    )
    cropped_qimg = q_img.copy(cropped_rect)  # type: QtGui.QImage
    cropped_qimg.scaled(image_size, image_size)
    cropped_qimg.save(temp_file_path)

    # read image data
    with open(temp_file_path, "rb") as fp:
        thumbnail_data = fp.read()

    os.remove(temp_file_path)

    thumbnail_data = encode_thumbnail_data(thumbnail_data)

    return thumbnail_data


def encode_thumbnail_data(thumbnail_data):
    return base64.b64encode(thumbnail_data).decode('utf-8')


def decode_thumbnail_data(raw_data):
    return base64.b64decode(raw_data)
