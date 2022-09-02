import pymel.core as pm
import maya.cmds as cmds
import sys

def x_ray_joints():
    active_panel = cmds.getPanel(withFocus=True)

    if "modelPanel" in active_panel:
        new_value = not pm.modelEditor(active_panel, query=True, jointXray=True)
        pm.modelEditor(active_panel, edit=True, jointXray=new_value)
        # if new_value:
        #     pm.modelEditor(active_panel, edit=True, joints=new_value)


def toggle_viewport_joints():
    active_panel = cmds.getPanel(withFocus=True)
    if "modelPanel" in active_panel:
        value = not pm.modelEditor(active_panel, query=True, joints=True)
        pm.modelEditor(active_panel, e=True, joints=value)
