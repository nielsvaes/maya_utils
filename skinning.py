import traceback

import pymel.core as pm
import maya.OpenMaya as om
from maya import OpenMayaUI as omui

import maya.api.OpenMaya as newOM
import maya.api.OpenMayaUI as newOMUI

from ..utils import io_utils
from ..utils import decorators
from . import general
from . import ui as mui
# import general

import os
import tempfile
from functools import partial
from collections import OrderedDict

import sys
PY3 = sys.version_info.major > 2


def hard_skin_to_single_joint(mesh, joint, remove_unused_influences=True):
    """
    Sets the influence of the specified joint

    :param mesh: <string> or <pynode> mesh you want hard skinned
    :param joint: <string> or <pynode> joint you want as the only influence
    :param remove_unused_influences: <bool> what is says on the box
    :return: <pynode> the skin_cluster that was used or created
    """
    # add a skin_cluster if it doesn't already exist
    skin_cluster = get_skin_cluster_from_mesh(mesh)
    if skin_cluster is None:
        skin_cluster_name = pm.skinCluster(joint, mesh, toSelectedBones=True)
        return general.pynode(skin_cluster_name)

    add_joint_to_skin_cluster(joint, skin_cluster)
    pm.skinPercent(skin_cluster, mesh, transformValue=[joint, 1], normalize=True)

    if remove_unused_influences:
        influences = pm.skinCluster(skin_cluster, query=True, influence=True)
        for influence in influences:
            if influence.name() != joint.name():
                pm.skinCluster(skin_cluster, edit=True, removeInfluence=influence.name())

    return skin_cluster

def copy_skin(source_mesh, target_mesh, method=["label", "oneToOne", "closestJoint"], smooth=True):
    """
    Copies the skinning from the source mesh to the target mesh. Makes a skin cluster if the target mesh doesn't have one

    :param source_mesh: <string> or <pynode> of where you want to copy from
    :param target_mesh: <string> or <pynode> of where you want to copy to
    :param method: <list> of strings. Options:["label", "closestBone", "closestJoint"]
    :param smooth: <bool> smooth the weights after copying them over. Default is True
    :return: None
    """
    source_mesh = general.pynode(source_mesh)
    target_mesh = general.pynode(target_mesh)

    source_skin = get_skin_cluster_from_mesh(source_mesh)
    target_skin = get_skin_cluster_from_mesh(target_mesh)

    if target_skin is None:
        source_skin = get_skin_cluster_from_mesh(source_mesh)
        target_skin = general.pynode(pm.skinCluster(source_skin.influenceObjects(), target_mesh, toSelectedBones=True))

    influencing_joints = source_skin.getInfluence()

    for joint in influencing_joints:
        add_joint_to_skin_cluster(joint, target_skin)

    pm.copySkinWeights(source_mesh, target_mesh, noMirror=True, influenceAssociation=method, smooth=smooth)

def add_joint_to_skin_cluster(joint, skin_cluster):
    """
    Add an extra joint to a skinCluster in a save way

    :param joint: <string> or <pynode> joint you want to add
    :param skin_cluster: name of the skinCluster, you can use getSkinClusterFromMesh or getSkinClusterFromComponent for this
    :return: None
    """
    if not joint in pm.skinCluster(skin_cluster, query=True, influence=True):
        pm.skinCluster(skin_cluster, edit=True, addInfluence=joint, weight=0, lockWeights=True)
        pm.setAttr("%s.liw" % joint, False)

def get_skin_cluster_from_mesh(mesh):
    """
    Gives you the skinCluster attached to this mesh.

    :param mesh: <string> or <pynode> of the mesh
    :return: the skinCluster or None, if it doesn't have one
    """
    node = pm.PyNode(mesh)
    try:
        skinCluster = node.listHistory(type="skinCluster")[0]
        return skinCluster
    except:
        return None

def get_skin_cluster_from_component(component):
    """
    Gives you the skinCluster that this component is part of

    :param component: <string> of the component, like "pCube.vtx[1]"
    :return: the skinCluster or None, it it doesn't have one
    """
    mesh = component.split(".")[0]
    skinCluster = get_skin_cluster_from_mesh(mesh)
    return skinCluster

def get_transform_from_skin_cluster(skin_cluster):
    """
    Gets the transform associated with the skinCluster

    :param skin_cluster: <string> or <pynode> of the skinCluster
    :return: <pynode> transform
    """
    return pm.listHistory(skin_cluster, type="shape")[0].getParent()

def get_shape_from_skin_cluster(skin_cluster):
    """
    Gets the shape node associated with the given skinCluster

    :param skin_cluster: <string> or <pynode> of the skinCluster
    :return: <pynode> shape node
    """
    return get_transform_from_skin_cluster(skin_cluster).getShape()

def is_skinned(mesh):
    """
    True if mesh is skinned, false is mesh it not.

    :param mesh: <string> or <pynode> of the mesh you want to check
    :return: <bool>
    """
    if get_skin_cluster_from_mesh(mesh) is None:
        return False
    else:
        return True


def get_skin_dictionary_from_scene():
    """
    Returns a dictionary where the key is a skinCluster and its values are the transform and shape node associated with it
    Can't remember why I ever need this, but here it is :)

    :return: <dict>>
    """
    skin_dict = {}
    for skinCluster in pm.ls(type="skinCluster"):
        transform = get_transform_from_skin_cluster(skinCluster)
        shapeNode = general.get_shape_nodes(transform)

        skin_dict[skinCluster] = {}
        skin_dict[skinCluster]["transform"] = transform
        skin_dict[skinCluster]["shape"] = shapeNode

    return skin_dict


def get_soft_selection_weights():
    """
    # https://groups.google.com/forum/#!topic/python_inside_maya/q1JlddKybyM

    Have a soft selection active before running this.
    Returns the node of which you have the soft selection active, a list of the vertex numbers of every vertex active
    in your soft select and the weights for all of those vertices

    :return: <pynode>, <list>, <list>
    """
    # Grab the soft selection
    selection = om.MSelectionList()
    softSelection = om.MRichSelection()
    om.MGlobal.getRichSelection(softSelection)
    softSelection.getSelection(selection)

    print(selection)

    dagPath = om.MDagPath()
    component = om.MObject()

    # Filter Defeats the purpose of the else statement
    iterator = om.MItSelectionList(selection, om.MFn.kMeshVertComponent)
    elements = []
    weights = []
    while not iterator.isDone():
        iterator.getDagPath(dagPath, component)
        dagPath.pop()  # Grab the parent of the shape node
        node = pm.PyNode(dagPath.fullPathName())
        fnComp = om.MFnSingleIndexedComponent(component)
        getWeight = lambda i: fnComp.weight(i).influence() if fnComp.hasWeights() else 1.0

        for i in range(fnComp.elementCount()):
            elements.append(fnComp.element(i))
            weights.append(getWeight(i))
        iterator.next()

    return pm.PyNode(node), elements, weights

@decorators.timeit
def set_soft_select_weights():
    """
    With a selection of softselected vertices and a single joint, this function will morph the soft selection weights to
    skinweights for the selected joint.

    :return: None
    """

    with pm.UndoChunk():
        selection = pm.selected()
        if len(selection) < 2:
            return

        joint = pm.selected()[-1]

        node, vertex_numbers, soft_select_weights = get_soft_selection_weights()
        add_joint_to_skin_cluster(joint, get_skin_cluster_from_mesh(node))

        skin_info = SkinInfo(node)
        new_joint_index = skin_info.get_index_of_joint(joint)

        print("Replacing weights for %i vertices" % len(vertex_numbers))

        for index, vertex_number in enumerate(vertex_numbers):
            # get the list of weights for this particular vertex
            weights_list_for_this_vertex = skin_info.get_weight_list_of_vertex(vertex_number)
            # replace the value in the list of weights at the location of the joint we have selected
            # with the value that we found using get_soft_selection_weights()
            weights_list_for_this_vertex[new_joint_index] = soft_select_weights[index]
            weights_list_for_this_vertex = normalize(weights_list_for_this_vertex, new_joint_index)

            # replace the weights list for this particular vertex with the normalized weights
            skin_info.set_weights_list_of_vertex(vertex_number, weights_list_for_this_vertex)
            # skin_info.skin_info_dict.get("weight_dict")[str(vertex_number)] = normalized_weights_list

        # grab the complete weightlist from our SkinInfo class and dump it into the selected mesh's skinCluster
        complete_weights_list = skin_info.get_complete_weights_list()
        # skin_info.set_weights(complete_weights_list, normalize=True)
        skin_info.set_weights(complete_weights_list)

        pm.select(None)

def assign_weight_to_joint(weight, components, joint):
    """
    Let's just use Maya's built-in functionality for this

    :param weight: *float* weight that will be assigned to the verts
    :param components: *list* of components that will receive the weights
    :param joint: *pynode* or *string* joint that will be the influence
    :return: None
    """
    components = general.flatten_component_list(components)
    skin = get_skin_cluster_from_component(components[0])
    add_joint_to_skin_cluster(joint, skin)

    pm.select(components)
    pm.skinPercent(skin, transformValue=[joint, weight])

def normalize(values, unchanged_index=0):
    """
    Normalizes the weights of all the values in the list, except the one of unchanged_index.
    # https://stackoverflow.com/questions/63765605/how-to-normalize-a-list-of-floats-when-one-value-has-to-stay-the-same

    :param values: *list* of floats
    :param unchanged_index: *int* index of the value you don't want to change when normalizing
    :return: *list* of floats that all add up to 1
    """
    remaining = 1 - values[unchanged_index]
    total_except_remaining = sum(values) - values[unchanged_index]
    if not total_except_remaining == 0:
        return [(value * remaining / total_except_remaining if idx != unchanged_index else value)
                for idx, value in enumerate(values)]
    else:
        return [(value * remaining if idx != unchanged_index else value) for idx, value in enumerate(values)]

def user_is_skinning():
    """
    Returns True if the skinpaint tool is active

    :return:
    """
    contex = pm.currentCtx()
    if contex == "manipMoveContext" or contex == "dragAttrContext":
        return False
    if pm.contextInfo(contex, query=True, c=True) == "artAttrSkin":
        return True
    return False

def copy_weights():
    """
    Saves a json file with name of all the joints influencing the mesh that is active. Then runs the mel command
    "CopyVertexWeights".

    Bind this to a hotkey to easily copy and paste weights between components and meshes

    :return:
    """
    temp_file = os.path.join(tempfile.gettempdir(), "weights")
    skincluster = get_skin_cluster_from_component(pm.selected()[0])
    influencing_joints = skincluster.getInfluence()

    io_utils.write_json([joint.name() for joint in influencing_joints], temp_file)

    selection = pm.selected()
    flat_list = general.flatten_component_list(pm.polyListComponentConversion(pm.selected(), toVertex=True))
    vertex = general.get_from_list(flat_list, vertices=True)[0]
    pm.select(vertex)
    pm.mel.eval("CopyVertexWeights;")

    pm.select(selection)

def paste_weights():
    """
    Tries to read the save json file from copy_weights. Adds the joints it finds in that file to the mesh you're currently
    working on. Then runs the mel command "PasteVertexWeights".

    Bind this to a hotkey to easily copy and paste weights between components and meshes

    :return:
    """
    selection = pm.selected()
    temp_file = os.path.join(tempfile.gettempdir(), "weights")
    saved_joints = io_utils.read_json(temp_file)
    mesh = general.get_transform_from_shape(general.pynode(pm.selected()[0].name().split(".")[0]))

    skin_cluster = get_skin_cluster_from_component(general.flatten_component_list(pm.selected())[0])

    if skin_cluster is None:
        skin_cluster = pm.skinCluster(saved_joints, mesh, toSelectedBones=True)

    for joint in saved_joints:
        add_joint_to_skin_cluster(general.pynode(joint), skin_cluster)

    pm.select(selection)
    pm.polyListComponentConversion(pm.selected(), toVertex=True)
    try:
        pm.mel.eval("PasteVertexWeights;")
    except:
        pass
    pm.select(selection)

def reinitialize_skinning(mesh):
    """
    Save the current skinning, deletes the skincluster and loads the skinning back on

    :param mesh: *string* or *pynode* of mesh with skinning
    :return: None
    """
    mesh = general.pynode(mesh)
    temp_file = os.path.join(tempfile.gettempdir(), "temp_skinning")

    skin_info = SkinInfo(mesh)
    skin_info.save_skin_to_file(temp_file, binary=True)
    pm.select(mesh)
    pm.mel.DetachSkin()

    skin_info.load_skin_from_file(temp_file, binary=True)


placed_joints = []
def enter_joint_placement(post_creation_func=None):
    global placed_joints
    placed_joints.clear()
    pm.optionVar["JointPlacer_FirstClickedMesh"] = ""

    target_meshes = general.get_from_list(pm.ls(), meshes=True)
    target_meshes = [m for m in target_meshes if m.isVisible()]

    active_panel = mui.get_active_viewport()

    if pm.isolateSelect(active_panel, query=True, state=True):
        target_meshes = general.pynode(pm.isolateSelect(active_panel, query=True, viewObjects=True)).flattened()

    dragger_context = "placer_ctx"
    if pm.draggerContext(dragger_context, exists=True):
        pm.deleteUI(dragger_context)
    pm.draggerContext(dragger_context, name=dragger_context, cursor='crossHair',
                      releaseCommand=partial(place_joint, dragger_context, target_meshes, post_creation_func),
                      drawString="Middle mouse to end placing")
    pm.setToolTo(dragger_context)


def place_joint(dragger_context, target_meshes, post_creation_func=None):
    global placed_joints

    modifier = pm.draggerContext(dragger_context, query=True, modifier=True)

    screen_x, screen_Y, _ = pm.draggerContext(dragger_context, query=True, anchorPoint=True)
    position = om.MPoint()
    direction = om.MVector()
    hitpoint = om.MFloatPoint()

    omui.M3dView().active3dView().viewToWorld(int(screen_x), int(screen_Y), position, direction)

    active_camera = general.pynode(pm.modelPanel(mui.get_active_viewport(), query=True, cam=True))
    camera_position = active_camera.getTranslation(worldSpace=True)
    mouse_button = pm.draggerContext(dragger_context, query=True, button=True)
    hit_positions = []

    if mouse_button == 1:
        clicked_meshes = {}
        for mesh in target_meshes:
            selectionList = om.MSelectionList()
            selectionList.add(mesh.name())
            dagPath = om.MDagPath()
            selectionList.getDagPath(0, dagPath)

            fn_mesh = om.MFnMesh(dagPath)

            clicked_on_mesh = fn_mesh.closestIntersection(
                om.MFloatPoint(position), om.MFloatVector(direction),
                None, None, False, om.MSpace.kWorld, 9999, False, None, hitpoint,
                None, None, None, None, None)

            if clicked_on_mesh is not False:
                hit_pos = (hitpoint.x, hitpoint.y, hitpoint.z)
                hit_positions.append(hit_pos)
                clicked_meshes[hit_pos] = mesh.name()

        hit_positions.sort(key=lambda p: camera_position.distanceTo(pm.datatypes.Vector(p)))
        hit_pos = hit_positions[0]
        if not pm.optionVar.get("JointPlacer_FirstClickedMesh"):
            pm.optionVar["JointPlacer_FirstClickedMesh"] = clicked_meshes.get(hit_pos)
            print(f"Setting JointPlacement mesh to: {clicked_meshes.get(hit_pos)}")

        joint = pm.createNode("joint")

        if modifier == "shift":
            if len(placed_joints) > 0:
                previous_joint = placed_joints[-1]

                x = previous_joint.translateX.get()
                y = hit_pos[1]
                z = previous_joint.translateZ.get()
                joint.setTranslation([x, y, z])
        else:
            joint.setTranslation(hit_pos)

        joint.overrideEnabled.set(True)
        joint.overrideRGBColors.set(True)
        joint.overrideColorR.set(0)
        joint.overrideColorG.set(1)
        joint.overrideColorB.set(1)
        joint.radius.set(3)
        placed_joints.append(joint)

    elif mouse_button == 2:
        placed_joints.reverse()

        for index, joint in enumerate(placed_joints):
            if index < len(placed_joints) - 1:
                child_joint = placed_joints[index]
                parent_joint = placed_joints[index + 1]

                pm.parent(child_joint, parent_joint)
        # pm.select(None)
        # constraint = pm.aimConstraint("pelvis", placed_joints[-1], maintainOffset=False, weight=1,
        #                               aimVector=[0, 0, -1], upVector=[-1, 0, 0], skip=["y", "z"])
        # pm.delete(constraint)

        pm.joint(placed_joints[-1], edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
        pm.makeIdentity(placed_joints[-1], rotate=True)
        placed_joints[0].rotate.set(0, 0, 0)
        placed_joints[0].jointOrient.set(0, 0, 0)
        pm.select(placed_joints[-1])
        # move joint inside the mesh a little bit
        # pm.move(placed_joints[-1], 0, -1, 0, relative=True, objectSpace=True)
        if post_creation_func:
            try:
                post_creation_func(placed_joints, pm.optionVar.get("JointPlacer_FirstClickedMesh"))
            except Exception as e:
                traceback.print_exc()
        placed_joints = []
        pm.optionVar["JointPlacer_FirstClickedMesh"] = ""


def enter_hammer_tool():
    """
    Calling this function will active a tool that allows you to drag over faces to weight hammer them. Much easier
    than them one by one.

    Holding down shift while painting influnences just vertices


    :return:
    """
    def hammer(dragger_context, target_meshes):
        with pm.UndoChunk():
            screen_x, screen_Y, _ = pm.draggerContext(dragger_context, query=True, dragPoint=True)
            modifier = pm.draggerContext(dragger_context, query=True, modifier=True)

            position = newOM.MPoint()
            direction = newOM.MVector()
            newOMUI.M3dView().active3dView().viewToWorld(int(screen_x), int(screen_Y), position, direction)

            active_panel = mui.get_active_viewport()
            active_camera = general.pynode(pm.modelPanel(active_panel, query=True, cam=True))

            camera_position = active_camera.getTranslation(worldSpace=True)

            # list that holds the hitpoint, reference to the mesh and reference to closest face to the point
            point_mesh_face_list = []

            for mesh in target_meshes:
                selection_list = newOM.MSelectionList()
                selection_list.add(mesh.name())
                fn_mesh = newOM.MFnMesh(selection_list.getDagPath(0))

                # hitpoint, hitrayparam, hit_face, hit_triangle, hit_bary1, hit_bar2
                hit_point, _, hit_face, _, _, _ = fn_mesh.closestIntersection(newOM.MFloatPoint(position),
                                                                              newOM.MFloatVector(direction),
                                                                              newOM.MSpace.kWorld, 9999, False)
                # if the face is not -1, we know our ray hit something
                if hit_face != -1:
                    point_mesh_face_list.append([hit_point, mesh, hit_face, fn_mesh])

            if len(point_mesh_face_list) > 0:
                point_mesh_face_list.sort(
                    key=lambda p: camera_position.distanceTo(pm.dt.Vector(p[0].x, p[0].y, p[0].z)))

                closest = point_mesh_face_list[0]
                closest_hitpoint = closest[0]
                closest_mesh = closest[1]
                closest_face = closest[2]
                closest_fn_mesh = closest[3]

                if modifier == "shift":
                    vertices = [general.pynode("%s.vtx[%s]" % (closest_mesh.name(), vtx)) for vtx in closest_fn_mesh.getPolygonVertices(closest_face)]
                    vertices.sort(key=lambda vtx: general.mpoint_to_vector(vtx.getPosition(space="world")).distanceTo(general.mpoint_to_vector(closest_hitpoint)))
                    pm.select(vertices[0])
                elif modifier == "ctrl":
                    pass
                    edges = [general.pynode("%s.e[%s]" % (closest_mesh.name(), edge)) for edge in general.pynode("%s.f[%s]" % (closest_mesh.name(), closest_face)).getEdges()]
                    edge_vertices = []
                    for edge in edges:
                        edge_vertices.extend(edge.connectedVertices())

                    edge_vertices.sort(key=lambda vtx: general.mpoint_to_vector(vtx.getPosition(space="world")).distanceTo(general.mpoint_to_vector(closest_hitpoint)))
                    pm.select(edge_vertices[0], edge_vertices[1])
                else:
                    pm.select("%s.f[%s]" % (closest_mesh.name(), closest_face))

            pm.mel.WeightHammer()
            pm.refresh(force=True)
            pm.select(None)


    target_meshes = general.get_all_visibile_meshes(as_transforms=True)

    dragger_context = "hammer_ctx"
    if pm.draggerContext(dragger_context, exists=True):
        pm.deleteUI(dragger_context)
    pm.draggerContext(dragger_context, name=dragger_context, cursor='crossHair',
                      dragCommand=partial(hammer, dragger_context, target_meshes))
    pm.setToolTo(dragger_context)




class SkinInfo(object):
    def __init__(self, mesh):
        """
        Builds a skin info object for a given mesh. This skin info object can be used to save/load skinweights, transfer
        weights between influences and set the weights for a skincluster. Saving/Loading is extremly fast.

        :param mesh: <string> or <pynode> of a mesh
        """
        super(SkinInfo, self).__init__()
        self.mesh = pm.PyNode(mesh)
        self.reinitialize()

    def __get_skin_info_dict(self):
        skin_info_dict = OrderedDict()

        if is_skinned(self.mesh):
            skin_info_dict["weight_dict"] = OrderedDict()
            for vertex_index, influence_list in enumerate(zip(self.skin_cluster.getWeights(self.mesh))):
                skin_info_dict["weight_dict"][str(vertex_index)] = list(influence_list[0]) # making the key a str because JSON needs it

            skin_info_dict["mesh_name"] = self.mesh.name()
            skin_info_dict["vertex_positions"] = general.get_vertex_pos_of_mesh(self.mesh)
            skin_info_dict["influence_list"] = self.influence_list
            skin_info_dict["influence_names"] = [joint.name() for joint in self.get_influence_objects()]

        return skin_info_dict

    def __get_influence_list(self):
        """
        Get a list of integers counting from 0 to the number of influences in the mesh's skin cluster

        :return:
        """
        influence_list = []
        if is_skinned(self.mesh):
            for x in range(len(self.skin_cluster.influenceObjects())):
                influence_list.append(x)

        return influence_list

    @decorators.timeit
    def get_complete_weights_list(self):
        """
        Returns a list of all the weights for a given skin cluster. The list is one big flat list of all the weights x
        the influences

        So if your mesh is a single triangle skinned to one joint, it would be [1.0, 1.0, 1.0]

        If it was a single triangle evenly skinned to 2 joints, it would be    [0.5, 0.5,   0.5, 0.5,  0.5, 0.5]
                                                                                |-------|   |-------|   |-------|
                                                                                  vtx 1       vtx 2       vtx 3
                                                                                jnt1,jnt2   jnt1,jnt2   jnt1,jnt2

        :return: <list> of floats
        """
        complete_weights_list = []
        for _, influence_values in self.skin_info_dict.get("weight_dict").items():
            if len(influence_values) < 2:
                influence_values = [influence_values]
            complete_weights_list.extend(influence_values)


        return complete_weights_list

    @decorators.timeit
    def set_weights(self, weights_list, normalize=True):
        self.skin_cluster.setWeights(self.mesh, self.influence_list, weights_list, normalize=normalize)
        if normalize:
            pm.skinCluster(self.skin_cluster, edit=True, forceNormalizeWeights=True)
        self.reinitialize()

    def get_index_of_joint(self, joint):
        joint = pm.PyNode(joint)
        try:
            return self.skin_cluster.influenceObjects().index(joint)
            # return self.skin_cluster.indexForInfluenceObject(joint) #this was giving me weird results...?
        except:
            add_joint_to_skin_cluster(joint, self.skin_cluster)
            self.reinitialize()
        finally:
            return self.skin_cluster.influenceObjects().index(joint)

    def reinitialize(self):
        self.skin_cluster = get_skin_cluster_from_mesh(self.mesh)

        self.influence_list = self.__get_influence_list()
        self.skin_info_dict = self.__get_skin_info_dict()

    def get_influence_objects(self):
        return self.skin_cluster.influenceObjects()

    def save_skin_to_file(self, filename, binary=False):
        if binary:
            io_utils.write_pickle(self.skin_info_dict, filename)
        else:
            io_utils.write_json(self.skin_info_dict, filename)

    @decorators.timeit
    def load_skin_from_file(self, filename, binary=False):
        if binary:
            self.skin_info_dict = io_utils.read_pickle(filename)
        else:
            self.skin_info_dict = io_utils.read_json(filename, ordered_dict=True)

        if not is_skinned(self.mesh):
            joints = self.skin_info_dict.get("influence_names")
            if joints is None:
                joints = general.get_from_list(pm.ls(), joints=True)
            skin_cluster_name = pm.skinCluster(joints, self.mesh, toSelectedBones=True, maximumInfluences=4)
            self.skin_cluster = general.pynode(skin_cluster_name)
            self.influence_list = self.__get_influence_list()

        if [joint.name() for joint in self.get_influence_objects()] != self.skin_info_dict.get("influence_names"):
            pm.skinCluster(self.mesh, unbind=True, edit=True)
            self.load_skin_from_file(filename, binary=binary)

        self.set_weights(self.get_complete_weights_list())

    def get_weight_list_of_vertex(self, vertex_number):
        return self.skin_info_dict.get("weight_dict").get(str(vertex_number))

    def set_weights_list_of_vertex(self, vertex_number, weight_list):
        self.skin_info_dict.get("weight_dict")[str(vertex_number)] = weight_list

    def get_vertices_influenced_by(self, joints, return_full_vertex_name=True, return_numbers=False):
        if not type(joints) == list:
            joints = [joints]

        joint_indices = []
        for joint in joints:
            joint_indices.append(self.get_index_of_joint(joint))

        influenced_vertices = []

        if PY3:
            iter_func = self.skin_info_dict.get("weight_dict").items
        else:
            iter_func = self.skin_info_dict.get("weight_dict").iteritems

        for vertex, weights in iter_func():
            for joint_index in joint_indices:
                if weights[joint_index] > 0:
                    influenced_vertices.append(int(vertex))

        if return_full_vertex_name:
            return ["%s.vtx[%s]" % (self.mesh.name(), number) for number in influenced_vertices]

        if return_numbers:
            return influenced_vertices

    def move_weights_to_other_joint(self, source_joint, target_joint, use_selected_components=False):
        if use_selected_components:
            influenced_vertices = general.flatten_selection_list(pm.polyListComponentConversion(pm.selected()[:-3], toVertex=True))
            print(influenced_vertices)
        else:
            influenced_vertices = self.get_vertices_influenced_by(source_joint, return_full_vertex_name=False, return_numbers=True)

        source_index = self.get_index_of_joint(source_joint)
        target_index = self.get_index_of_joint(target_joint)

        for vertex in influenced_vertices:
            weights_list_for_this_vertex = self.get_weight_list_of_vertex(vertex)
            weight_value_to_transfer = weights_list_for_this_vertex[source_index]
            weights_list_for_this_vertex[source_index] = 0.0
            weights_list_for_this_vertex[target_index] = weight_value_to_transfer

        self.set_weights(self.get_complete_weights_list())


