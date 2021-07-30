import pymel.core as pm

def delete_unused_shading_nodes():
    """
    Deletes unused nodes from the Hypershade

    :return:
    """
    pm.mel.eval(r'hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')

def get_materials(objects):
    """
    Returns a list of all the material nodes

    :param objects: a list of objects you want to get the materials from or None, to use the currently selected objects
    :return: <list> of materials
    """
    if not isinstance(objects, list):
        objects = [objects]

    all_materials = []

    for obj in objects:
        obj = pm.PyNode(obj)
        shape_node = obj.getShape()
        shading_engines = shape_node.listConnections(type="shadingEngine")
        all_materials += pm.ls(pm.listConnections(shading_engines), materials=True)

    return all_materials

def create_texture(name, file_path, place_2d_name=None):
    """
    Creates a texture file and hooks it up to a place2D node

    :param name: name the texture node will have
    :param file_path: path to the file on drive
    :param place_2d_name: name of the place2dTexture node to use. If set to None, a new place2dTexture node will be made
    :return: the newly created node
    """

    texture = pm.PyNode(pm.shadingNode("file", name=name, asTexture=True, isColorManaged=True))
    texture.fileTextureName.set(file_path)

    if place_2d_name is not None:
        place_2d = pm.PyNode(place_2d_name)
    else:
        place_2d = pm.PyNode(pm.shadingNode("place2dTexture", asUtility=True))

    texture.filterType.set(0)

    place_2d.outUV >> texture.uvCoord
    place_2d.outUvFilterSize >> texture.uvFilterSize
    place_2d.vertexCameraOne >> texture.vertexCameraOne
    place_2d.vertexUvOne >> texture.vertexUvOne
    place_2d.vertexUvThree >> texture.vertexUvThree
    place_2d.vertexUvTwo >> texture.vertexUvTwo
    place_2d.coverage >> texture.coverage
    place_2d.mirrorU >> texture.mirrorU
    place_2d.mirrorV >> texture.mirrorV
    place_2d.noiseUV >> texture.noiseUV
    place_2d.offset >> texture.offset
    place_2d.repeatUV >> texture.repeatUV
    place_2d.rotateFrame >> texture.rotateFrame
    place_2d.rotateUV >> texture.rotateUV
    place_2d.stagger >> texture.stagger
    place_2d.translateFrame >> texture.translateFrame
    place_2d.wrapU >> texture.wrapU
    place_2d.wrapV >> texture.wrapV

    return texture

def create_material(name, material_type):
    """
    Creates a material

    :param name: name of the material
    :param material_type: material type like "lambert", "blinn", "phong"
    :return: newly created material
    """
    material = pm.shadingNode(material_type, name=name, asShader=True)
    shading_group = pm.sets(name='%sSG' % material, empty=True, renderable=True, noSurfaceShader=True)

    material.outColor >> shading_group.surfaceShader

    return pm.PyNode(material)


def assign_material(mesh, material):
    """
    Easy to remember one-liner to set the material on mesh

    :param mesh:
    :param material:
    :return:
    """
    material = pm.PyNode(material)
    shading_group = pm.PyNode(material).listConnections(type="shadingEngine")[0]

    if material.name() == "lambert1":
        shading_group = pm.PyNode("initialShadingGroup")

    if pm.PyNode(mesh).__class__ == pm.nodetypes.Transform:
        mesh = mesh.getShape()

    pm.sets(shading_group, edit=True, forceElement=mesh)
    mesh.updateSurface()

