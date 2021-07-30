import pymel.core as pm
import general
import rigging

def get_blend_shape_nodes(source_object):
    """
    Convenience one-liner to get the blendShape nodes on an object

    :param source_object: *string* or *PyNode* of the object you want to get blendShape nodes from
    :return: *list* of blendShape nodes
    """
    source_object = pm.PyNode(source_object)
    return source_object.listHistory(type="blendShape")

def set_blend_shape_value(blend_shape_node, blend_shape_name, value, reset=True):
    """
    Sets the blend shape value of a specific blend shape name to a specific value

    :param blend_shape_node: *string* or *PyNode* of the blendShape node
    :param blend_shape_name: *string* of the blendShape weight
    :param value: *float* value you want to set
    :param reset: *bool* if True, will set all other blendShape weights to 0
    :return:
    """
    blend_shape_node = pm.PyNode(blend_shape_node)
    value = float(value)
    all_weights = get_blend_shape_target_names(blend_shape_node)

    for weight_name in all_weights:
        if weight_name == blend_shape_name:
            blend_shape_node.attr(blend_shape_name).set(value)
        else:
            if reset:
                blend_shape_node.attr(weight_name).set(0)

def turn_off_all_blend_shapes(blend_shape_node):
    """
    Sets all the blendShape weights to 0

    :param blend_shape_node: *string* or *PyNode* of the blendShape node
    :return: *list* with the names of all the blendShape weights on this node
    """
    blend_shape_node = pm.PyNode(blend_shape_node)
    all_weights = get_blend_shape_target_names(blend_shape_node)

    for weight_name in all_weights:
        blend_shape_node.attr(weight_name).set(0)

    return all_weights


def get_blend_shape_target_names(blend_shape_node):
    """
    Because who wants to type [weight.getAlias() for weight in blend_shape_node.w] or
    pm.listAttr("%s.weight" % blend_shape_node.name(), multi=True) when they could auto complete
    to get_blend_shape_target_names?

    :param blend_shape_node: *string* or *PyNode* of the blendShape node
    :return: *list* with the names of all the targets on this blendshape
    """
    blend_shape_node = pm.PyNode(blend_shape_node)
    return [weight.getAlias() for weight in blend_shape_node.w]


def transfer_blend_shapes(source, target, specific_blend_shape_nodes=None):
    """
    Transfers the blend shapes from one mesh to another.

    :param source: *string* or *PyNode* of the source object
    :param target: *string* or *PyNode* of the target object
    :param specific_blend_shape_nodes: *list* if you only want to use specific nodes to transfer
    :return: *list* with all the newly (is that a word...? it looks weird) created blendShape nodes
    """
    source = pm.PyNode(source)
    target = pm.PyNode(target)
    copied_meshes = []
    new_bs_nodes = []

    with pm.UndoChunk():
        if specific_blend_shape_nodes is None:
            blend_shape_nodes = get_blend_shape_nodes(source)
        else:
            if not isinstance(specific_blend_shape_nodes, list):
                blend_shape_nodes = [pm.PyNode(specific_blend_shape_nodes)]
            else:
                blend_shape_nodes = [pm.PyNode(node) for node in specific_blend_shape_nodes]

        wrap_node = rigging.create_wrap(source.name(long=False), target.name(long=False))

        for bs_node in blend_shape_nodes:
            new_bs_node = pm.createNode("blendShape", name="transfered_%s" % bs_node.name(long=False))
            new_bs_node.setGeometry(target)

            for index, target_name in enumerate(get_blend_shape_target_names(bs_node)):
                set_blend_shape_value(bs_node, target_name, 1)
                if not pm.objExists(target_name):
                    copied_mesh = pm.duplicate(target, name=target_name)[0]
                    pm.blendShape(new_bs_node, edit=True, target=[target, index, copied_mesh, 1.0])
                    copied_meshes.append(copied_mesh)
                else:
                    general.error("Can't duplicate blendshape target '%s' since there's already "
                                  "a mesh in the scene with that name" % target_name)
                    pm.delete(wrap_node)
                    pm.delete(new_bs_node)
                    if pm.objExists("%sBase" % source.name(long=False)):
                        pm.delete("%sBase" % source.name(long=False))
                    return

            new_bs_nodes.append(new_bs_node)
            turn_off_all_blend_shapes(bs_node)

        pm.delete(wrap_node)
        if pm.objExists("%sBase" % source.name(long=False)):
            pm.delete("%sBase" % source.name(long=False))
        pm.select(target)
        pm.delete(copied_meshes)

    return new_bs_nodes
