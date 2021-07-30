class GeneralConstans():
    """
    Constants that hold true for any node

    """
    name = "name"
    long_name = "long_name"


gk = GeneralConstans

class TransformConstants(GeneralConstans):
    """
    Constants that hold true for any transform node

    """
    translate = "translate"
    tx = "tx"
    ty = "ty"
    tz = "tz"
    rotate = "rotate"
    rx = "rx"
    ry = "ry"
    rz = "rz"
    scale = "scale"
    sx = "sx"
    sy = "sy"
    sz = "sz"
    world_matrix = "world_matrix"
    local_matrix = "local_matrix"
    parent = "parent"
    visibility = "visibility"

tk = TransformConstants

class JointConstants(TransformConstants):
    """
    Constants that hold true for any joint node

    """
    joint_orient = "jointOrient"
    rotate_order = "rotateOrder"
    radius = "radius"

jk = JointConstants

class ComponentSelectionType():
    """
    Component types to be used in pm.filterExpand()

    """
    nurbs_curve = 9
    nurbs_surface = 10
    isoparm = 45
    cv = 28
    poly_vert = 31
    poly_edge = 32
    poly_face = 34
    all_poly_components = [31, 32, 34]
    poly_vert_face = 70
    poly_uv = 35
