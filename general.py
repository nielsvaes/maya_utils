import pymel.core as pm
import maya.cmds as cmds

from ..utils import lists
from ..utils import io_utils
from . import shader
from .constants import ComponentSelectionType

import os
import re
import tempfile

from maya import OpenMayaUI as omui
from maya import OpenMaya as old_OM
import maya.api.OpenMaya as om

from PySide2.QtWidgets import *
from shiboken2 import wrapInstance

import sys
if sys.version_info.major > 2:
    long = int

def maya_useNewAPI():
    """
    So that we can use the Python API 2.0

    :return:
    """
    pass

def get_shape_nodes(node, intermediate=False):
    """
    Gets the shape node of node

    :param node: *string* or *pynode*
    :param intermediate: *bool* returns in the intermediate nodes as well. Generally you don't want this
    :return: *list* of all the shape nodes of node
    """
    if pm.nodeType(node) == "transform":
        shape_nodes = pm.listRelatives(node, shapes=True, path=True)

        found_shape_nodes = []

        if shape_nodes is None:
            return None

        for shape_node in shape_nodes:
            is_intermediate = pm.getAttr("%s.intermediateObject" % shape_node)

            if intermediate == True and is_intermediate and pm.listConnections(shape_node, source=False):
                return shape_node

            elif intermediate == False and not is_intermediate:
                found_shape_nodes.append(shape_node)

        if len(found_shape_nodes) > 0:
            return found_shape_nodes

    elif pm.nodeType(node) in ["mesh", "nurbsCurve", "nurbsSurface"]:
        return [pm.PyNode(node)]

    return None

def get_transform_from_shape(shape_node):
    """
    Get the transform from a shape node. Easier to understand for new people than doing .getParent() on a shape node

    :param shape_node: *pynode* of a shape
    :return: *pynode*
    """
    return shape_node.getParent()

def get_all_meshes(as_transforms=False, as_shape_nodes=False):
    """
    Convenience one-liner to find all the meshes in a scene

    :param as_transforms: *bool* get the transform nodes
    :param as_shape_nodes: *bool* get the shape nodes
    :return: *list* of transforms or shape nodes
    """
    if not as_transforms and not as_shape_nodes:
        as_transforms = True

    if as_transforms:
        return list(set([node.getTransform() for node in pm.ls(type="mesh")]))
    if as_shape_nodes:
        return list(set([node for node in pm.ls(type="mesh")]))

def get_all_visibile_meshes(as_transforms=False, as_shape_nodes=False):
    """
    Returns all the current visible meshes for the active viewport. This takes isolate select
    also into account

    :param as_transforms: *bool* get the transform nodes
    :param as_shape_nodes: *bool* get the shape nodes
    :return: *list* of transforms or shape nodes
    """
    active_panel = cmds.getPanel(withFocus=True)

    if pm.isolateSelect(active_panel, query=True, state=True):
        iso_select_objects = pynode(pm.isolateSelect(active_panel, query=True, viewObjects=True)).flattened()
        iso_select_meshes = get_from_list(iso_select_objects, meshes=True)
        visible_meshes = [mesh for mesh in iso_select_meshes if mesh.visibility.get() == True]
    else:
        visible_meshes = pm.ls(get_all_meshes(as_transforms=True), visible=True)

    if as_transforms:
        return list(set([node.getTransform() for node in visible_meshes]))
    if as_shape_nodes:
        return list(set([get_shape_nodes(node)[0] for node in visible_meshes]))

def get_shortest_name(node, strip_namespace=True):
    """
    For a given node, return the shortest possible name. Strips the full dag path and any existing namespace.

    :param node: *pynode*
    :return: <str>
    """
    node = pynode(node)
    return node.name(long=None, stripNamespace=strip_namespace)

def replace_shape_nodes(source_transform, target_transform, delete_source_transform=True):
    """
    Replaces the shape nodes of the source_transform with those of target_transform

    :param source_transform: *string* or *pynode*
    :param target_transform: *string* or *pynode*
    :param delete_source_transform: *bool* whether or not the source node should be deleted
    :return: None
    """

    target_shape_nodes = get_shape_nodes(target_transform)
    source_shape_nodes = get_shape_nodes(source_transform)

    pm.delete(target_shape_nodes)
    pm.parent(source_shape_nodes, target_transform, relative=True, shape=True)

    if delete_source_transform:
        pm.delete(source_transform)

def add_to_shape_nodes(source_transform, target_transform, delete_source_transform=True):
    """
    Adds the shape nodes of source_transform to those of target_transform

    :param source_transform: *string* or *pynode*
    :param target_transform: *string* or *pynode*
    :param delete_source_transform: *bool* whether or not the source node should be deleted
    :return: None
    """

    source_shape_nodes = get_shape_nodes(source_transform)

    pm.parent(source_shape_nodes, target_transform, relative=True, shape=True)

    if delete_source_transform:
        pm.delete(source_transform)

def delete_namespace(namespace):
    """
    Removes all objects from the given namespace and then removes it

    :param namespace: *string*
    :return:
    """
    try:
        pm.namespace(force=True, rm=namespace, mergeNamespaceWithRoot=True)
        pm.namespace (set=':')
    except:
        pass

def remove_namespace(object_name):
    """
    Removes the namespace from a string

    :param object_name: *string*
    :return:
    """

    return pynode(object_name).stripNamespace()

def get_namespace(object_name):
    """
    Returns the namespace from a string

    :param object_name: *string*
    :return:
    """

    parts = object_name.split("|")
    result = ""

    for index, part in enumerate(parts):
        if index > 0:
            result += "|"
        result += part.split(":")[0]

    return result

def set_node_namespace(nodes, namespace):
    """
    Puts objects into a namespace, creates it when it doesn't exist

    :param nodes: *list*
    :param namespace: *string*
    :return: None
    """
    if not isinstance(nodes, list):
        nodes = [nodes]

    if not pm.namespace(exists=namespace):
        pm.namespace(addNamespace=namespace)

    for node in nodes:
        node = pynode(node)
        node.rename("{}:{}".format(namespace, node.nodeName()))

def add_to_display_layer(objects, display_layer_name):
    """
    Adds objects to display_layer_name. Creates a new display layer if it doesn't exist.

    :param objects:
    :param display_layer_name:
    :return: a pynode of the display layer
    """
    if not isinstance(objects, list):
        objects = [objects]

    if not pm.objExists(display_layer_name):
        pm.createDisplayLayer(empty=True, name=display_layer_name)

    pm.editDisplayLayerMembers(display_layer_name, *objects)

    return pynode(display_layer_name)

def remove_from_any_display_layer(objects):
    """
    Removes objects from whatever display layer they were in

    :param objects: *list* of nodes
    :return:
    """
    add_to_display_layer(objects, "defaultLayer")

def nuke_display_layer(display_layer_name):
    """
    Deletes the display layer and all the nodes in it

    :param display_layer_name: *string* name of the display_layer
    :return: *bool*
    """
    if pm.objExists(display_layer_name):
        pm.delete(pm.editDisplayLayerMembers(display_layer_name, query=True))
        pm.delete(display_layer_name)
        success("Nuked %s" % display_layer_name)
        return True
    else:
        warning("Display layer: %s doesn't exist" % display_layer_name)
        return False

def get_empty_display_layers():
    """
    Returns a list of all empty display layers in the scene
    :return: *list*
    """
    empty_layers = []
    for layer in pm.ls(type="displayLayer"):
        if pm.editDisplayLayerMembers(layer, query=True) is None:
            empty_layers.append(layer)

    return empty_layers

def get_non_empty_display_layers():
    """
    Returns all display layers that have at least one thing in it
    :return:
    """
    dilledaddles = []
    for layer in pm.ls(type="displayLayer"):
        if pm.editDisplayLayerMembers(layer, query=True):
            dilledaddles.append(layer)

    return dilledaddles

def to_pynodes(input_list):
    """
    One liner to convert a list of nodes to PyNodes

    :param input_list: *list* of node names
    :return: *list* of PyNodes
    """
    if not isinstance(input_list, list):
        input_list = [input_list]

    pynode_list = []
    for node in input_list:
        pynode_list.append(pynode(node))
    return pynode_list

def mpoint_to_vector(mpoint):
    """
    Converts a MPoint to a PyMel vector

    :param mpoint: Maya MPoint
    :return: pm.dt.Vector
    """
    return pm.dt.Vector([mpoint.x, mpoint.y, mpoint.z])

def isclose(a, b, rel_tol=1e-09, abs_tol=0.0001):
    """
    Compare 2 floats with floating point error

    :param a:
    :param b:
    :param rel_tol:
    :param abs_tol:
    :return:
    """
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def pynode(object_name, specific_on_multiple=False, pick_most_root=False, pick_most_leaf=False, pick_index=None):
    """
    Returns a PyNode of the given object name with better error messages and additional options

    :param object_name: name of the object you want to make a PyNode
    :param specific_on_multiple: *bool* When set to True, allows you set the next flags to return a specific object when there are multiple objects with the same name
    :param pick_most_root: *bool* returns the most root object if there are multiple objects with the same name
    :param pick_most_leaf: *bool* returns the most leaf object if there are multiple objects with the same name
    :param pick_index: *int* returns this index of object if there are multiple objects with the same name
    :return: a PyNode
    """
    if object_name is None:
        warning("Can't make a PyNode when object_name type is None")
    if type(object_name) == om.MFnDependencyNode:
        object_name = object_name.name()

    if pm.objExists(object_name):
        try:
            return pm.PyNode(object_name)
        except:
            if not type(object_name) == str:
                node_name = object_name.nodeName()
            else:
                node_name = object_name
            multiple_nodes = sorted([str(node) for node in pm.ls(node_name)], key=len)

            if len(multiple_nodes) > 1:
                if specific_on_multiple is False:
                    error_message = "There are multiple nodes with this name:"
                    for node in multiple_nodes:
                        error_message += "\n%s" % node
                    raise RuntimeError(error_message)
                else:
                    if pick_most_root is True:
                        return pm.PyNode(multiple_nodes[0])
                    elif pick_most_leaf is True:
                        return pm.PyNode(multiple_nodes[-1])
                    elif pick_index is not None:
                        try:
                            selected_node = multiple_nodes[pick_index]
                        except IndexError:
                            raise IndexError("%s is not a valid index, valid indices are 0 to %s"
                                             % (pick_index, len(multiple_nodes) - 1))
                        return pm.PyNode(selected_node)

                    error("When custom_on_multiple is set to True, either pick_most_root or pick_most_leaf "
                          "should be set to True as well")
    else:
        error("Can't make a PyNode. Object (%s) doesn't exist" % object)

def success(message):
    """
    Shorter way to show a viewport message with a green background

    :param message: *string* message you want to show
    :return:
    """
    show_viewport_message(message, color="green")

def warning(message):
    """
    Shorter way to show a viewport message with a yello background

    :param message: *string* message you want to show
    :return:
    """
    show_viewport_message(message, color="yellow", echo=False, visible_time=5000)
    pm.warning(message)

def error(message):
    """
    Shorter way to show a viewport message with a red background

    :param message: *string* message you want to show
    :return:
    """
    show_viewport_message(message, color="red", echo=False, visible_time=5000)
    message = "->\n\n" + " " * 50 + message
    pm.error(message)

def show_viewport_message(message, color, echo=True, visible_time=1500):
    """
    Shows a viewport message with a chosen color

    :param message: *string* message you want to show
    :param color: hexadecimal color code
    :param echo: *bool* if True, will also just print the message in the script editor
    :return:
    """
    try:
        if color.lower() == "red":
            back_color = 0x00FF0000
        elif color.lower() == "grey" or color.lower() == "gray":
            back_color = 0x00585858
        elif color.lower() == "green":
            back_color = 0x0021610B
        elif color.lower() == "yellow":
            back_color = 0x00666600
    except:
        pass

    pm.inViewMessage(statusMessage=message, backColor=back_color, fadeStayTime=visible_time, fade=True,
                     position="topCenter")
    if echo:
        print(message)

def set_matrix(source, target):
    """
    Sets the transform matrix of target to that of source

    :param source: *pynode* or *string* of the transform with t
    :param target:
    :return:
    """
    source = pynode(source)
    target = pynode(target)
    target.setMatrix(source.getMatrix(worldSpace=True))

def lock_and_hide_selected(node, attribute_list=[], translate=False, rotate=False, scale=False, lock=True, visible=False):
    """
    Locks and hides attributes

    :param node: *string* | *pynode* node you want to lock and hide things on
    :param attribute_list: *list* of strings with attribute names you want to lock
    :param translate: *bool* add all translation channels to the list
    :param rotate: *bool* add all rotation channels to the list
    :param scale: *bool* add all scale channels to the list
    :param lock: *bool*
    :param visible: *bool*
    :return: None
    """
    node = pynode(node)

    if translate:
        attribute_list.extend(["translateX", "translateY", "translateZ"])
    if rotate:
        attribute_list.extend(["rotateX", "rotateY", "rotateZ"])
    if scale:
        attribute_list.extend(["scaleX", "scaleY", "scaleZ"])
    for attribute in attribute_list:
        node.setAttr(attribute, lock=lock)
        node.setAttr(attribute, keyable=visible)

def lock_and_hide_default_attributes(node):
    lock_and_hide_selected(node, translate=True, rotate=True, scale=True, attribute_list=["visibility"])

def get_point_list_from_curve(curve):
    """
    Returns a list with the position CVs of a curve as 3-tuples. Ideal for saving those quirky controller shapes!

    :param curve: *string* or *pynode* of the curve
    :return:
    """
    curve = pynode(curve)

    pos_list = []

    for point in curve.getCVs():
        x = float("%.3f" % point[0])
        y = float("%.3f" % point[1])
        z = float("%.3f" % point[2])

        pos_list.append((x, y, z))

    return pos_list

def invert_point_list_along_axis(axis, point_list):
    """
    Given a point list as a list of a 3-tuple, inverts the shape along the selected axis. Ideal for flipping controllers
    around

    :param axis: *string* x, y or z
    :param point_list: *list* of tuples or lists representing a point in 3D space. [0, -0.4, 4]
    :return: *list* of inverted points
    """
    axis = axis.lower()
    new_point_list = []

    for point in point_list:
        new_x = point[0]
        new_y = point[1]
        new_z = point[2]

        if axis == "x":
            new_x = new_x * -1
        if axis == "y":
            new_y = new_y * -1
        if axis == "z":
            new_z = new_z * -1

        new_point = (new_x, new_y, new_z)
        new_point_list.append(new_point)

    return new_point_list

def is_joint(node):
    """
    Returns true if node is a joint

    :param node: *string* or *pynode*
    :return:
    """
    try:
        node = pynode(node)

        if type(node) == pm.nodetypes.Joint:
            return True
    except Exception as err:
        print(err)
        return False

def get_maya_main_window():
    """
    Returns the Maya main window to use with Qt

    :return: Maya main window
    """
    maya_main_window_ptr = omui.MQtUtil.mainWindow()
    maya_main_window = wrapInstance(long(maya_main_window_ptr), QWidget)

    return maya_main_window

def get_scene_path(full_path=True, name_only=False, folder_only=False, extension=True):
    """
    Extension of the normal pm.sceneName() with a bit more options

    :param full_path: *bool* returns the full path (D:/Game/scenes/enemy.ma)
    :param name_only: *bool* returns the name of the file only (enemy.ma)
    :param folder_only: *bool* returns the folder of the file only (D:/Game/scenes)
    :param extension: *bool* whether or not to return the name with the extension
    :return: *string*
    """
    if name_only:
        name = os.path.basename(pm.sceneName())
        if extension:
            return name
        return os.path.splitext(name)[0]
    if folder_only:
        return os.path.dirname(pm.sceneName())
    if full_path:
        if extension:
            return pm.sceneName()
        return os.path.splitext(pm.sceneName())[0]
    return ""

def get_active_camera():
    """
    Returns a the current active camera as a PyNode

    :return: *Pynode*
    """
    try:
        active_camera = pm.PyNode(cmds.modelPanel(cmds.getPanel(withFocus=True), query=True, cam=True))
        return active_camera
    except Exception as err:
        print(err)
        error("The active view doesn't have a camera")



def selection(as_strings=False, as_pynodes=False, st=False, py=False):
    """
    Convenience function to easily get your selection as a string representation or as pynodes

    :param as_strings: *bool* returns a list of strings
    :param as_pynodes: *bool* returns a list of pynodes
    :param st: *bool* same as as_strings
    :param py: *bool* same as as_pynodes
    :return:
    """
    import maya.cmds as cmds

    if as_strings or st:
        return [str(uni) for uni in cmds.ls(selection=True)]

    if as_pynodes or py:
        return pm.selected()


def flatten_component_list(component_list, as_pynodes=False):
    """
    Returns a list of components as a flattened list, as strings or as pynodes. Helpful for when your selection is something like [sphere.vtx[0:44]]

    :param component_list: *list* of components
    :param as_pynodes: *bool* return your components as pynodes
    :return: *list*
    """
    if as_pynodes:
        return [pynode(component) for component in pm.ls(component_list, flatten=True)]
    return pm.ls(component_list, flatten=True)


def get_from_list(input_list, meshes=False, all_components=False, vertices=False, edges=False, faces=False,
                  joints=False, constraints=False, nurbs_curves=False, groups=False, transforms=False):
    """
    Given an input list of mixed types, return the ones you want

    :param input_list: *list* of maya names or nodes
    :param meshes: *bool* if true, returns any selected meshes
    :param all_components: *bool* if true, returns all faces, edges and vertices
    :param vertices: *bool* returns vertices
    :param edges: *bool* returns edges
    :param faces: *bool* returns faces
    :param joints: *bool* returns joints
    :param constraints: *bool* returns all constraints
    :param nurbs_curves: *bool* returns nurbs curves
    :param groups: *bool* returns groups
    :param transforms: *bool* returns transforms

    :return: *list* of PyNodes
    """
    if not input_list or len(input_list) == 0:
        return

    return_list = []
    input_list = pm.ls(input_list, flatten=True)

    if meshes:
        meshes = []
        for node in pm.ls(input_list, type="transform", long=True):
            try:
                if node.getShape().type() == "mesh":
                    meshes.append(node)
            except:
                pass

        return_list.extend(meshes)

    if all_components:
        return_list.extend(pm.filterExpand(input_list, selectionMask=ComponentSelectionType.all_poly_components))

    if vertices:
        return_list.extend(pm.filterExpand(input_list, selectionMask=ComponentSelectionType.poly_vert))

    if edges:
        return_list.extend(pm.filterExpand(input_list, selectionMask=ComponentSelectionType.poly_edge))

    if faces:
        return_list.extend(pm.filterExpand(input_list, selectionMask=ComponentSelectionType.poly_face))

    if joints:
        return_list.extend(pm.ls(input_list, type="joint"))

    if constraints:
        return_list.extend(pm.ls(input_list, type="constraint"))

    if nurbs_curves:
        return_list.extend([node.getParent() for node in pm.ls(type="nurbsCurve")])

    if groups:
        return_list.extend([node for node in pm.ls(input_list, type="transform") if is_group(node)])

    if transforms:
        return_list.extend([node for node in pm.ls(input_list, type="transform")])
    return [pm.PyNode(each) for each in lists.remove_duplicates(return_list)]

def is_group(node):
    """
    Checks if the given node is a group node

    :param node: node or nodename
    :return: *bool*
    """
    node = pynode(node)

    if not pm.objectType(node) == "transform":
        return False

    try:
        children = node.getChildren()
    except:
        return False

    if get_shape_nodes(node):
        return False

    return True

def is_empty_group(group_node, include_empty_child_groups=True):
    """
    Checks if a group is empty

    :param group_node: *string* or *PyNode*
    :param include_empty_child_groups: *bool* if True checks the entire hierarchy to see if any child groups are also
    empty. If set to False, will return False even if the top group has empty groups inside
    :return: *bool*
    """
    is_empty = True
    group_node = pm.PyNode(group_node)

    if not is_group(group_node):
        return False

    if include_empty_child_groups:
        try:
            for child in group_node.getChildren():
                if not is_group(child):
                    is_empty = False
                    break
                else:
                    is_empty = is_empty_group(child)
        except:
            pass
        finally:
            return is_empty
    else:
        if len(group_node.getChildren()) == 0:
            return True
        return False

def get_all_empty_groups(include_empty_child_groups=True):
    """
    Gets all the empty groups in the scene

    :param include_empty_child_groups: *bool* if True checks the entire hierarchy to see if any child groups are also
    empty. If set to False, will return False even if the top group has empty groups inside
    :return: *list* of all the empty groups
    """
    return [group for group in get_from_list(pm.ls(), groups=True) if is_empty_group(group, include_empty_child_groups)]

def is_point_inside_mesh(point, mesh_name, direction=[0.0, 0.0, 1.0]):
    """
    Checks to see if any given point is inside a mesh

    https://stackoverflow.com/questions/18135614/querying-of-a-point-is-within-a-mesh-maya-python-api
    :param point: (float, float, float) of the point you want to test
    :param mesh_name: *string* mesh you want to check for
    :param direction: *list* direction you want the ray to shoot in
    :return: bool
    """
    sel = old_OM.MSelectionList()
    dag = old_OM.MDagPath()

    sel.add(mesh_name, False)
    sel.getDagPath(0, dag)

    mesh_name = old_OM.MFnMesh(dag)

    point = old_OM.MFloatPoint(*point)
    direction = old_OM.MFloatVector(*direction)
    farray = old_OM.MFloatPointArray()

    mesh_name.allIntersections(
        point, direction,
        None, None, False,
        old_OM.MSpace.kWorld,
        10000,
        False, None, False,
        farray,
        None, None, None, None, None
    )

    if farray.length() % 2 == 1:
        return True
    else:
        return False

def get_vertices_inside_mesh(source_object, volume_object):
    """
    Returns all the vertices of source_object that are inside volume_object

    :param source_object: string or PyNode of the object you want to get the vertices from
    :param volume_object: string or PyNode of the object wherein the search should happen
    :return: list with strings of vertex names that were inside volume_object
    """
    pm.select(None)
    source_object = pynode(source_object)
    volume_object = pynode(volume_object)

    found_vertices = []
    vertex_positions = get_vertex_pos_of_mesh(source_object)
    for index, point in enumerate(vertex_positions):
        if is_point_inside_mesh(point, volume_object.name()):
            found_vertices.append("%s.vtx[%s]" % (source_object.name(), index))

    return found_vertices


def component_is_selected():
    """
    Returns true if the first thing in your selection list is a component

    :return:
    """
    selection = pm.selected()
    if not selection:
        return False
    return any([face_is_selected(selection[0]), edge_is_selected(selection[0]), vertex_is_selected(selection[0])])


def face_is_selected(selection=None):
    """
    Returns true if the first thing in your selection list is a face

    :return:
    """
    if selection is None:
        selection = pm.selected()[0]

    if selection.__class__ is pm.general.MeshFace:
        return True
    return False


def edge_is_selected(selection=None):
    """
    Returns true if the first thing in your selection list is a edge

    :return:
    """
    if selection is None:
        selection = pm.selected()[0]

    if selection.__class__ is pm.general.MeshEdge:
        return True
    return False


def vertex_is_selected(selection=None):
    """
    Returns true if the first thing in your selection list is a vertex

    :return:
    """
    if selection is None:
        selection = pm.selected()[0]

    if selection.__class__ is pm.general.MeshVertex:
        return True
    return False


def get_vertex_pos_of_mesh(mesh, as_mpoint_array=False):
    """
    Returns a list of all the vertex positions in a mesh

    :param mesh: *string* or *pynode* of the mesh you want to check
    :param as_mpoint_array: *list* of Maya MPoints instead of a normal float list
    :return:
    """
    try:
        mesh = mesh.name()
    except:
        pass

    selection_list = om.MSelectionList()
    selection_list.add(mesh)

    dag_path = selection_list.getDagPath(0)
    mpoint_array = om.MFnMesh(dag_path).getPoints(om.MSpace.kWorld)

    if as_mpoint_array:
        return mpoint_array

    else:
        point_list = []
        for mpoint in mpoint_array:
            point_list.append([mpoint[0], mpoint[1], mpoint[2]])

        return point_list

    #pymel way, much more concise but also slower:
    # pynode(mesh).getShape().getPoints()

def meshes_to_dictionary(meshes, dump_to_file=False, file_name=None):
    """
    Turns a list of meshes into one big dictionary to reconstruct it. Calls mesh_as_dictionary for every mesh in the
    list.

    :param meshes: *list* of mesh names or mesh pynodes
    :param dump_to_file: *bool*
    :param file_name: *bool* dump_to_file must be True
    :return: *dict*
    """
    data_dict = {}
    for mesh in meshes:
        mesh = pm.PyNode(mesh)
        data_dict[mesh.name()] = mesh_as_dictionary(mesh)

    if dump_to_file:
        io_utils.write_json(data_dict, file_name)

    return data_dict

def mesh_as_dictionary(mesh, name=None, include_blend_shapes=True, dump_to_file=False, file_name=None):
    """
    Returns a dictionary that describes a mesh so it's possible to later rebuild that mesh from pure data. It saves:

    :param mesh: *string* or *pynode* of the mesh you want to save
    :param dump_to_file: *bool* will save out the dict as a json
    :param file_name: *string* file path of where you want to save the json
    :return: <dict> in the form of:

        data_dict = {
            "name": mesh.name(),
            "num_vertices": num_vertices,
            "num_polygons": num_polygons,
            "vertex_position_list": vertex_position_list,
            "polygon_count_list": polygon_count_list,
            "polygon_connections_list": polygon_connections_list,
            "material_name": shader.get_materials(mesh)[0].name(),
            "material_type": shader.get_materials(mesh)[0].typeName(),
            "blend_shape": {
                "blendShape1": {
                    "female_body_proportions": [
                        [
                            61.97188186645508,
                            103.09303283691406,
                            -0.026771757751703262
                        ],
                        [
                            63.01567459106445,
                            102.21643829345703,
                            0.25466033816337585
                        ], ...
                    ]
                }
           }

    """
    from . import blend_shapes as bs
    mesh = pynode(mesh)

    selection_list = om.MSelectionList()
    selection_list.add(mesh.name())
    mfn_mesh = om.MFnMesh(selection_list.getDagPath(0))

    vertex_position_list = get_vertex_pos_of_mesh(mesh.name())
    num_vertices = len(vertex_position_list)
    num_polygons = len(mesh.faces)
    polygon_count_list = [len(face.getVertices()) for face in mesh.faces]
    polygon_connections_list = lists.flatten([face.getVertices() for face in mesh.faces])
    assigned_uvs = mfn_mesh.getAssignedUVs()
    assigned_uvs = ([value for value in assigned_uvs[0]], [value for value in assigned_uvs[1]])
    uvs = mfn_mesh.getUVs()
    uvs = ([value for value in uvs[0]], [value for value in uvs[1]])

    blend_shape_dictionary = {}
    if include_blend_shapes:
        blend_shape_nodes = bs.get_blend_shape_nodes(mesh)
        if blend_shape_nodes:
            for blend_shape_node in blend_shape_nodes:
                bs.turn_off_all_blend_shapes(blend_shape_node)
                blend_shapes = bs.get_blend_shape_target_names(blend_shape_node)
                blend_shape_dictionary[blend_shape_node.name()] = {}

                if blend_shapes:
                    for blend_shape_name in blend_shapes:
                        bs.set_blend_shape_value(blend_shape_node, blend_shape_name, 1)
                        blend_shape_dictionary[blend_shape_node.name()][blend_shape_name] = get_vertex_pos_of_mesh(mesh)

                bs.turn_off_all_blend_shapes(blend_shape_node)

    selection_list = om.MSelectionList()
    selection_list.add(mesh.name())

    dag_path = selection_list.getDagPath(0)
    edge_iterator = om.MItMeshEdge(dag_path)
    hard_edge_info = []

    while not edge_iterator.isDone():
        hard_edge_info.append([int(edge_iterator.index()), edge_iterator.isSmooth])
        edge_iterator.next()

    if name is None:
        name = mesh.name()

    data_dict = {
        "name": name,
        "num_vertices": num_vertices,
        "num_polygons": num_polygons,
        "vertex_position_list": vertex_position_list,
        "polygon_count_list": polygon_count_list,
        "polygon_connections_list": polygon_connections_list,
        "material_name": shader.get_materials(mesh)[0].name(),
        "material_type": shader.get_materials(mesh)[0].typeName(),
        "hard_edge_info": hard_edge_info,
        "blend_shape": blend_shape_dictionary,
        "assigned_uvs": assigned_uvs,
        "uvs": uvs
    }

    if dump_to_file:
        io_utils.write_json(data_dict, file_name)

    return data_dict

def meshes_from_dictionary(mesh_dict, assign_material=True, center_pivot=True):
    """
    Rebuilds meshes from dictionary. Calls mesh_from_dictionary for every mesh in the mesh_dict

    :param mesh_dict: *dict* of meshes that were saved with meshes_to_dictionary
    :param assign_material: *bool* assigns the saved material to the mesh
    :param center_pivot: *bool* bakes cookies and makes icecream sundaes. Also centers the pivot of the new mesh
    """
    new_meshes = []
    for mesh_name, info_dict in mesh_dict.items():
        new_mesh = mesh_from_dictionary(info_dict, assign_material=assign_material, center_pivot=center_pivot)
        new_meshes.append(new_mesh)
    return new_meshes


def mesh_from_dictionary(mesh_dict, assign_material=True, mesh_name=None, center_pivot=True, select=True):
    """
    Rebuilds a mesh from a dictionary. See use mesh_as_dictionary to structure the input dictionary

    :param mesh_dict: <dict>, get it from mesh_as_dictionary
    :param assign_material: *bool* assigns the saved material to the mesh
    :param mesh_name: *string* sets the mesh name
    :param center_pivot: *bool* bakes cookies and makes icecream sundaes. Also centers the pivot of the new mesh
    :param select: *bool* select the new mesh after creating it
    :return: *pynode* of the new mesh
    """
    from . import blend_shapes as bs
    from . import shader

    # Make saved mesh
    vertex_position_array = om.MFloatPointArray()
    for vertex_position in mesh_dict.get("vertex_position_list"):
        vertex_position_array.append(om.MFloatPoint(vertex_position[0], vertex_position[1], vertex_position[2]))

    mfn_mesh = om.MFnMesh()
    mesh_mobject = mfn_mesh.create(vertex_position_array,
                                   mesh_dict.get("polygon_count_list"),
                                   mesh_dict.get("polygon_connections_list")
                                   )
    mfn_mesh.setUVs(mesh_dict.get("uvs")[0], mesh_dict.get("uvs")[1])
    mfn_mesh.assignUVs(mesh_dict.get("assigned_uvs")[0], mesh_dict.get("assigned_uvs")[1])
    new_mesh = pynode(om.MFnDependencyNode(mesh_mobject))

    # set hard/soft edges:
    edge_numbers, edge_hardness = zip(*mesh_dict.get("hard_edge_info"))
    mfn_mesh.setEdgeSmoothings(edge_numbers, edge_hardness)
    mfn_mesh.cleanupEdgeSmoothing()
    mfn_mesh.updateSurface()

    # Add any blend shapes
    if mesh_dict.get("blend_shape"):
        for blend_shape_node_name, blend_shape_info_dict in mesh_dict.get("blend_shape").items():
            for index, (blend_shape_target_name, vertex_positions) in enumerate(blend_shape_info_dict.items()):
                vertex_position_array = om.MFloatPointArray()
                for vertex_position in vertex_positions:
                    vertex_position_array.append(
                        om.MFloatPoint(vertex_position[0], vertex_position[1], vertex_position[2]))

                mfn_mesh = om.MFnMesh()
                mesh_mobject = mfn_mesh.create(vertex_position_array,
                                               mesh_dict.get("polygon_count_list"),
                                               mesh_dict.get("polygon_connections_list")
                                               )
                temp_mesh = pynode(om.MFnDependencyNode(mesh_mobject))
                pm.rename(temp_mesh, blend_shape_target_name)

                if not blend_shape_node_name in bs.get_blend_shape_nodes(new_mesh):
                    if pm.objExists(blend_shape_node_name):
                        warning("The blendShape node %s already exists, outcome may be different than expected" % blend_shape_node_name)
                    blend_shape_node = pm.createNode("blendShape", name=blend_shape_node_name)
                    blend_shape_node.setGeometry(new_mesh)

                pm.blendShape(blend_shape_node, edit=True, target=[new_mesh, index, temp_mesh, 1.0])
                #blend_shape_node.addTarget(new_mesh, index, temp_mesh, 1.0) doesn't work...?

                pm.delete(temp_mesh)

    # assign material
    if assign_material:
        if not pm.objExists(mesh_dict.get("material_name")):
            material = shader.create_material(mesh_dict.get("material_name"), mesh_dict.get("material_type"))
        else:
            material = pynode(mesh_dict.get("material_name"))
        shader.assign_material(pm.PyNode(new_mesh), material)

    # rename
    if mesh_name is not None:
        pm.rename(new_mesh, mesh_name)
    else:
        pm.rename(new_mesh, mesh_dict.get("name"))

    # pivots
    if center_pivot:
        new_mesh.centerPivots()

    # select when done
    if select:
        pm.select(new_mesh)

    return new_mesh

def get_all_inputs(source):
    """
    Returns all inputs to a specific node or attribute on node

    :param source: *pynode* node or attribute on node
    :return: recursive list of all inputs into source
    """

    inputs = []
    for input_node in source.inputs():
        inputs.append(input_node)
        inputs += get_all_inputs(input_node)
    return list(set(inputs))

def get_all_outputs(source):
    """
    Returns all outputs to a specific node or attribute on node

    :param source: *pynode* node or attribute on node
    :return: recursive list of all outputs into source
    """

    outputs = []
    for output_node in source.outputs():
        outputs.append(output_node)
        outputs += get_all_inputs(output_node)
    return list(set(outputs))

def get_component_numbers(components):
    """
    Returns the numbers of the passed in components

    :param components: *list* of PyNodes
    :return:
    """
    if not isinstance(components, list):
        components = [components]

    try:
        return [int(re.search(r"\[([0-9]+)\]", component.name()).group(1)) for component in components]
    except:
        return []

def save_selection():
    """
    Saves the current selection to a .json file. Read this file from load_selection() to retrieve the elements

    :return:
    """
    temp_file = os.path.join(tempfile.gettempdir(), "save_selection")
    selection = [node.name() for node in pm.ls(pm.selected(), flatten=True)]
    io_utils.write_json(selection, temp_file)
    success("Saved selection!")

def load_selection(add=False, intersect=False, difference=False):
    """
    Loads the selection that was saved in save_selection

    :param add: *bool* add to the current selection if True
    :param intersect: *bool* select common items in saved selection and current selection
    :param difference: *bool* select items that are not shared between saved and current selection
    :return: None
    """
    temp_file = os.path.join(tempfile.gettempdir(), "save_selection")
    saved_selection = io_utils.read_json(temp_file)
    if add:
        pm.select(saved_selection, add=True)
        return
    if intersect:
        selection = [node.name() for node in pm.selected()]
        pm.select(lists.common(selection, saved_selection))
        return
    if difference:
        selection = [node.name() for node in pm.selected()]
        pm.select(lists.difference([selection, saved_selection]))
        return
    pm.select(saved_selection)

def set_enum_by_string(node, attribute, string):
    """
    Sets an enum attribute by passing it the string you want to set it to

    :param node: *string* or *pynode*
    :param attribute: *string* name of the enum attribute
    :param string: *string* value you want to set the enum attribute to
    :return: None
    """
    enum_string = pm.attributeQuery(attribute, node=node, listEnum=True)[0]
    enum_options = enum_string.split(":")
    index = enum_options.index(string)
    pm.setAttr("%s.%s" % (node, attribute), index)

def are_siblings(nodes):
    """
    Returns true is all the nodes in nodes have a common parent
    :param nodes: *list*
    :return: *list*
    """
    parents = []
    for joint in nodes:
        parents.append(joint.getParent())

    if len(lists.remove_duplicates(parents)) == 1:
        return True
    return False

def get_siblings(node):
    """
    Returns all the siblings of node

    :param node: *pynode*
    :return: *list&
    """
    parent = node.getParent()
    if parent is None:
        return get_top_level_nodes()
    return parent.getChildren()

def get_top_level_nodes():
    """
    Easy to remember one liner
    :return: *list* of all top level nodes
    """
    return pm.ls("|*")

def get_complete_hierarchy(root_node):
    """
    Returns the full hierarchy of a root node, including the root node. Because you don't get that from node.getChildren(allDescendents=True)

    :param root_node: node or string
    :return: *list*
    """
    root_node = pm.PyNode(root_node)
    child_nodes = root_node.getChildren(allDescendents=True)
    child_nodes.insert(0, root_node)

    return child_nodes

def serialize_matrix(matrix):
    """
    Returns a list of lists describing the matrix

    :param matrix: pm.dt.Matrix
    :return: *list*
    """
    if not type(matrix) == pm.dt.Matrix:
        error(f"{matrix} is not of data type Matrix")
        return
    return [list(arr) for arr in list(matrix)]

def make_marking_menu():
    pass
