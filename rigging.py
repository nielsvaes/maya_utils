import pymel.core as pm
import maya.cmds as cmds

from . import general
from ..utils import lists
from .constants import jk


def label_joints(joints=None, force=False):
    """
    Tries to automatically label joints based on either the Maya naming convention or the name of the joint itself.
    Tries to get the side from the name

    :param joints: <list> string or PyNodes
    :param force: <bool>
    :return: None
    """
    if joints is None:
        joints = pm.ls(type="joint")

    label_dict = {}
    label_dict["none"] = 0
    label_dict["root"] = 1
    label_dict["hip"] = 2
    label_dict["knee"] = 3
    label_dict["foot"] = 4
    label_dict["toe"] = 5
    label_dict["spine"] = 6
    label_dict["neck"] = 7
    label_dict["head"] = 8
    label_dict["collar"] = 9
    label_dict["shoulder"] = 10
    label_dict["elbow"] = 11
    label_dict["hand"] = 12
    label_dict["finger"] = 13
    label_dict["thumb"] = 14
    label_dict["propA"] = 15
    label_dict["propB"] = 16
    label_dict["propC"] = 17
    label_dict["other"] = 18
    label_dict["index_finger"] = 19
    label_dict["middle_finger"] = 20
    label_dict["ring_finger"] = 21
    label_dict["pinky_finger"] = 22
    label_dict["extra_finger"] = 23
    label_dict["big_toe"] = 24
    label_dict["index_toe"] = 25
    label_dict["middle_toe"] = 26
    label_dict["middle_toe"] = 27
    label_dict["pinky_toe"] = 28
    label_dict["foot_thumb"] = 29

    for joint in [pm.PyNode(node) for node in joints if general.is_joint(node)]:
        if not force:
            # early out if someone has already decorated/labeled this joint
            if joint.getAttr("type") == label_dict["other"]:
                continue

        x_pos = joint.getTranslation(space="world")[0]
        if x_pos > 0.01:
            joint.setAttr("side", 1)
        elif x_pos < -0.01:
            joint.setAttr("side", 2)

        found_name = False
        for name, value in label_dict.items():
            if name in joint.name():
                joint.setAttr("type", value)
                found_name = True

        if not found_name:
            label_name = joint.nodeName(stripNamespace=True)

            left_names = lists.get_name_variant(["l_", "left_", "_l", "_left", "lft_", "lft_"])
            right_names = lists.get_name_variant(["r_", "right_", "_r", "_right", "rght_", "_rght"])

            for variant in left_names + right_names:
                if label_name.startswith(variant):
                    label_name = label_name[len(variant):]

                if label_name.endswith(variant):
                    label_name = label_name[:-len(variant)]

            joint.setAttr("type", label_dict.get("other"))
            joint.setAttr("otherType", label_name)

def get_pole_vector_position(joint_1, joint_2, joint_3, multiplier=1.0):
    """
    Returns the correct position for a pole vector for a 3 joint setup

    :param joint_1: <pynode> joint
    :param joint_2: <pynode> joint
    :param joint_3: <pynode> joint
    :param multiplier: <float> offsets the return location to be closer or nearer to the joint chain
    :return: <vector> location of the pole vector
    """
    # http://lesterbanks.com/2013/05/calculating-the-position-of-a-pole-vector-in-maya-using-python/

    a = joint_1.getTranslation(space="world")
    b = joint_2.getTranslation(space="world")
    c = joint_3.getTranslation(space="world")

    start_to_end = c - a
    start_to_mid = b - a

    dot = start_to_mid * start_to_end

    projection = float(dot) / float(start_to_end.length())

    start_to_end_normalized = start_to_end.normal()

    projection_vector = start_to_end_normalized * projection

    arrow_vector = start_to_mid - projection_vector
    arrow_vector *= multiplier

    pole_vector_position = arrow_vector + b

    return pole_vector_position

def set_joint_draw_style(joints, none=False, bone=False):
    """
    Easy one line to set the draw style of joints to bone or invisible

    :param joints: <list> of joints
    :param none: <bool> if true, joints won't be shown in the viewport
    :param bone: <bool> if True, joints will be drawn with bones in between them
    :return: None
    """
    none_style = 2
    bone_style = 0

    if not type(joints) == list:
        joints = [joints]

    for joint in joints:
        if general.is_joint(joint):
            if none:
                joint.setAttr("drawStyle", none_style)
            if bone:
                joint.setAttr("drawStyle", bone_style)

def skeleton_as_dictionary(root_joint, strip_namespace=True):
    """
    Returns a list with joint info dictionaries. The list looks like:
    [
        {
            "rotateOrder": 0,
            "radius": 1.091586120866983,
            "name": "root",
            "parent": null,
            "local_matrix": [
                1.0,
                0.0,
                -0.0,
                0.0,
                -0.0,
                0.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                1.3552527156068805e-20,
                9.769962616701378e-15,
                2.696055049133599e-16,
                1.0
            ],
            "visibility": true,
            "long_name": "|root",
            "jointOrient": [
                -90.0,
                -0.0,
                0.0
            ],
            "world_matrix": [
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                1.3552527156068805e-20,
                9.769962616701378e-15,
                2.696055049133599e-16,
                1.0
            ]
        },
    ...
    ]

    This function was use to dump the skeleton info in Characters/Skeleton

    Use skeleton_from_dictionary() with this dictionary to rebuild the skeleton

    :param root_joint: <string> or <PyNode> of the root joint of the skeleton
    :return: <list> of dictionaries
    """
    from . import general

    root_joint = pm.PyNode(root_joint)
    skeleton_dict_list = []

    joint_hierarchy = general.get_from_list([root_joint] + root_joint.getChildren(allDescendents=True), joints=True)
    joint_hierarchy.sort(key=lambda j: len(j.name(long=True)))

    for joint in joint_hierarchy:
        skeleton_dict = {}
        try:
            parent = joint.getParent()
            if general.is_joint(parent):
                skeleton_dict[jk.parent] = joint.getParent().name(long=False, stripNamespace=strip_namespace)
            else:
                skeleton_dict[jk.parent] = None
        except:
            skeleton_dict[jk.parent] = None
        skeleton_dict[jk.name] = joint.name(long=False, stripNamespace=strip_namespace)
        skeleton_dict[jk.long_name] = joint.name(long=True, stripNamespace=strip_namespace)
        skeleton_dict[jk.world_matrix] = lists.flatten(joint.getMatrix(worldSpace=True))
        skeleton_dict[jk.local_matrix] = lists.flatten(joint.getMatrix(objectSpace=True))
        skeleton_dict[jk.joint_orient] = list(joint.jointOrient.get())
        skeleton_dict[jk.rotate_order] = joint.rotateOrder.get()
        skeleton_dict[jk.radius] = joint.radius.get()
        skeleton_dict[jk.visibility] = joint.visibility.get()

        skeleton_dict_list.append(skeleton_dict)

    return skeleton_dict_list

def skeleton_from_dictionary(dictionary_list, adjust_existing_joints=True, node_remap=None):
    """
    Builds the skeleton based on the dictionaries in dictionary_list

    :param dictionary_list: <list>
    :param adjust_existing_joints: <bool> if turned off, will always create a new joint for every joint dictionary in
    dictionary_list, even it already exists. If turned on, will load the attributes on the existing joints in the scene.
    :return:
    """
    for i, joint_dictionary in enumerate(dictionary_list):
        try:
            long_name = joint_dictionary.get(jk.long_name)
            short_name = joint_dictionary.get(jk.name)
            jnt_parent = joint_dictionary.get(jk.parent)

            # remap node names to new targets
            if node_remap:
                if jnt_parent in list(node_remap.keys()):
                    jnt_parent = node_remap.get(jnt_parent)

            if adjust_existing_joints:
                if pm.objExists(long_name):
                    joint = general.pynode(long_name)
                else:
                    found_matches = pm.ls(short_name)
                    if len(found_matches) == 1:
                        joint = found_matches[0]
                    elif len(found_matches) > 1:
                        raise Exception("Found multiple matches for joint : {}. \n Aborting! \n Found matches : {}"
                                        .format(short_name, [n.name() for n in found_matches]))
                    else:
                        raise Exception("Found no match for joint : {}. \n Aborting!".format(short_name))
            else:
                joint = pm.createNode(pm.nt.Joint, name=short_name)

            if not adjust_existing_joints:
                pm.parent(joint, jnt_parent)

            joint.rotateOrder.set(joint_dictionary.get(jk.rotate_order))
            joint.radius.set(joint_dictionary.get(jk.radius))
            joint.jointOrient.set(joint_dictionary.get(jk.joint_orient))
            if jnt_parent is None:
                joint.setMatrix(joint_dictionary.get(jk.world_matrix))
            else:
                joint.setMatrix(joint_dictionary.get(jk.local_matrix), objectSpace=True)
            joint.visibility.set(joint_dictionary.get(jk.visibility))
        except Exception as err:
            print(err)
            pass

    pm.select(None)
    label_joints(pm.ls(type=pm.nt.Joint))

def create_wrap(*args, **kwargs):
    """
    # Python way to create a damn wrap deformer. You'd expect this to be easier using normal
    # cmds or pymel
    # https://gist.github.com/mclavan/276a2b26cab5bc22d882

    :param args: *string* source object, *string* or *list* of targets objects
    :param kwargs: weightThreshold, maxDistance, autoWeightThreshold, falloffMode
    :return: *PyNode* of the wrap deformer
    """

    influence = args[0]
    surface = args[1]

    shapes = cmds.listRelatives(influence, shapes=True)
    influenceShape = shapes[0]

    shapes = cmds.listRelatives(surface, shapes=True)
    surfaceShape = shapes[0]

    # create wrap deformer
    weightThreshold = kwargs.get('weightThreshold', 0.0)
    maxDistance = kwargs.get('maxDistance', 1.0)
    exclusiveBind = kwargs.get('exclusiveBind', False)
    autoWeightThreshold = kwargs.get('autoWeightThreshold', True)
    falloffMode = kwargs.get('falloffMode', 0)

    wrapData = cmds.deformer(surface, type='wrap')
    wrapNode = wrapData[0]

    cmds.setAttr(wrapNode + '.weightThreshold', weightThreshold)
    cmds.setAttr(wrapNode + '.maxDistance', maxDistance)
    cmds.setAttr(wrapNode + '.exclusiveBind', exclusiveBind)
    cmds.setAttr(wrapNode + '.autoWeightThreshold', autoWeightThreshold)
    cmds.setAttr(wrapNode + '.falloffMode', falloffMode)

    cmds.connectAttr(surface + '.worldMatrix[0]', wrapNode + '.geomMatrix')

    # add influence
    duplicateData = cmds.duplicate(influence, name=influence + 'Base')
    base = duplicateData[0]
    shapes = cmds.listRelatives(base, shapes=True)
    baseShape = shapes[0]
    cmds.hide(base)

    # create dropoff attr if it doesn't exist
    if not cmds.attributeQuery('dropoff', n=influence, exists=True):
        cmds.addAttr(influence, sn='dr', ln='dropoff', dv=4.0, min=0.0, max=20.0)
        cmds.setAttr(influence + '.dr', k=True)

    # if type mesh
    if cmds.nodeType(influenceShape) == 'mesh':
        # create smoothness attr if it doesn't exist
        if not cmds.attributeQuery('smoothness', n=influence, exists=True):
            cmds.addAttr(influence, sn='smt', ln='smoothness', dv=0.0, min=0.0)
            cmds.setAttr(influence + '.smt', k=True)

        # create the inflType attr if it doesn't exist
        if not cmds.attributeQuery('inflType', n=influence, exists=True):
            cmds.addAttr(influence, at='short', sn='ift', ln='inflType', dv=2, min=1, max=2)

        cmds.connectAttr(influenceShape + '.worldMesh', wrapNode + '.driverPoints[0]')
        cmds.connectAttr(baseShape + '.worldMesh', wrapNode + '.basePoints[0]')
        cmds.connectAttr(influence + '.inflType', wrapNode + '.inflType[0]')
        cmds.connectAttr(influence + '.smoothness', wrapNode + '.smoothness[0]')

    # if type nurbsCurve or nurbsSurface
    if cmds.nodeType(influenceShape) == 'nurbsCurve' or cmds.nodeType(influenceShape) == 'nurbsSurface':
        # create the wrapSamples attr if it doesn't exist
        if not cmds.attributeQuery('wrapSamples', n=influence, exists=True):
            cmds.addAttr(influence, at='short', sn='wsm', ln='wrapSamples', dv=10, min=1)
            cmds.setAttr(influence + '.wsm', k=True)

        cmds.connectAttr(influenceShape + '.ws', wrapNode + '.driverPoints[0]')
        cmds.connectAttr(baseShape + '.ws', wrapNode + '.basePoints[0]')
        cmds.connectAttr(influence + '.wsm', wrapNode + '.nurbsSamples[0]')

    cmds.connectAttr(influence + '.dropoff', wrapNode + '.dropoff[0]')
    # I want to return a pyNode object for the wrap deformer.
    # I do not see the reason to rewrite the code here into pymel.
    # return wrapNode
    return pm.nt.Wrap(wrapNode)
