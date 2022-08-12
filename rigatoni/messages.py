from dataclasses import  dataclass, field
from math import pi
from typing import Optional


"""
Common Definitions
"""

Vec3 = [float] * 3
Vec4 = [float] * 4
Mat4 = [float] * 16

RGB = [float] * 3
RGBA = [float] * 4

@dataclass
class IDGroup(object):

    slot : int
    gen : int
    id : list[int] = field(init=False)

    def __post_init__(self):
        self.id = [self.slot, self.gen]

    # redefined hash function, so IDGroup object is hashable as key in state
    def __hash__(self):
        places = len(str(abs(self.gen)))
        hash_val = self.slot + (self.gen >> places)
        return hash_val

@dataclass
class SelectionRange(object):
    key_from_inclusive : int
    key_to_exclusive : int

@dataclass
class MethodArg(object):
    name : str
    rows : list[int] = None
    row_ranges : list[SelectionRange] = None

@dataclass
class BoundingBox(object):
    min : Vec3
    max : Vec3


"""
Server Messages
"""

# Method Messages ================================================================================
@dataclass
class MethodCreateMessage(object):
    id : IDGroup
    name : str
    doc : str = None
    return_doc : str = None
    arg_doc : list[MethodArg] = None

@dataclass
class MethodDeleteMessage(object):
    id : IDGroup


# Signal Messages ================================================================================
@dataclass
class SignalCreateMessage(object):
    id : IDGroup
    name : str
    doc : str = None
    arg_doc : list[MethodArg] = None

@dataclass
class SignalDeleteMessage(object):
    id : IDGroup


# Entity Messages ================================================================================
@dataclass
class TextRepresentation(object):
    txt : str
    font : str = "Arial"
    height : float = .25
    width : float = -1

@dataclass
class WebRepresentation(object):
    source : str
    height : float = .5
    width : float = .5

@dataclass
class InstanceSource(object):
    view : IDGroup
    stride : int
    bb : BoundingBox = None

@dataclass
class RenderRepresentation(object):
    mesh : IDGroup
    instances : InstanceSource = None

@dataclass
class EntityCreateMessage(object):
    id : IDGroup
    name : str = None

    parent : IDGroup = None
    transform : Mat4 = None

    null_rep : any = None
    text_rep : TextRepresentation = None
    web_rep : WebRepresentation = None
    render_rep : RenderRepresentation = None

    lights : list[IDGroup] = None
    tables : list[IDGroup] = None
    plots : list[IDGroup] = None
    tags : list[str] = None
    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None

    influence : BoundingBox = None


@dataclass
class EntityUpdateMessage(object):
    id : IDGroup
    parent : IDGroup = None
    transform : Mat4 = None

    null_rep : any = None
    text_rep : TextRepresentation = None
    web_rep : WebRepresentation = None
    render_rep : RenderRepresentation = None

    lights : list[IDGroup] = None
    tables : list[IDGroup] = None
    plots : list[IDGroup] = None
    tags : list[str] = None
    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None

    influence : BoundingBox = None

@dataclass
class EntityDeleteMessage(object):
    id : IDGroup


# Plot Messages ================================================================================ 
@dataclass
class PlotCreateMessage(object):
    id : IDGroup
    name : str = None

    table : IDGroup = None

    simple_plot : str = None
    url_plot : str = None

    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None

@dataclass
class PlotUpdateMessage(object):
    id : IDGroup
    table : IDGroup = None

    simple_plot : str = None
    url_plot : str = None

    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None

@dataclass
class PlotDeleteMessage(object):
    id : IDGroup


# Buffer Messages ================================================================================
@dataclass
class BufferCreateMessage(object):
    id : IDGroup
    name : str = None
    size : int = None

    inline_bytes : bytes = None
    uri_bytes : str = None

@dataclass
class BufferDeleteMessage(object):
    id : IDGroup

@dataclass
class BufferViewCreateMessage(object):
    id : IDGroup
    source_buffer : IDGroup

    type : str
    offset : int
    length : int

    name : str = None

@dataclass
class BufferViewDeleteMessage(object):
    id : IDGroup


# Material Messages ================================================================================
@dataclass
class TextureRef(object):
    texture : IDGroup
    transform : Mat4 = field(default_factory = [1, 0, 0, 0,
                        0, 1, 0, 0,
                        0, 0, 1, 0,
                        0, 0, 0, 1]) # cddl says mat3, not defined - typo?
    texture_coord_slot : int = 0

@dataclass
class PBRInfo(object):
    base_color : RGBA = field(default_factory = [255, 255, 255, 1]) # white as default
    base_color_texture : TextureRef = None # assume SRGB, no premult alpha

    metallic : float = 1
    roughness : float = 1
    metal_rough_texture : TextureRef = None # assume linear, ONLY RG used

@dataclass
class MaterialCreateMessage(object):
    id : IDGroup
    pbr_info : PBRInfo
    name : str = None

    normal_texture : TextureRef = None

    occlusion_texture : TextureRef = None # assumed to be linear, ONLY R used
    occlusion_texture_factor : float = 1

    emissive_texture : TextureRef = None # assumed to be SRGB, ignore A
    emissive_factor : Vec3 = field(default_factory =[1, 1, 1])

    use_alpha : bool = False
    alpha_cutoff : float = .5

    double_sided : bool = False

@dataclass
class MaterialUpdateMessage(object):
    id : IDGroup
    # TBD

@dataclass
class MaterialDeleteMessage(object):
    id : IDGroup


# Image Messages ================================================================================ 
@dataclass
class ImageCreateMessage(object):
    id : IDGroup
    name : str = None

    buffer_source : IDGroup = None
    uri_source : str = None

@dataclass
class ImageDeleteMessage(object):
    id : IDGroup


# Texture Messages ================================================================================ 
@dataclass
class TextureCreateMessage(object):
    id : IDGroup
    image : IDGroup
    name : str = None
    sampler : IDGroup = None # Revist default sampler

@dataclass
class TextureDeleteMessage(object):
    id : IDGroup


# Sampler Messages ================================================================================ 
@dataclass
class SamplerCreateMessage(object):
    id : IDGroup
    name : str = None

    mag_filter: str = "LINEAR" # NEAREST or LINEAR
    min_filter : str = "LINEAR_MIPMAP_LINEAR" # NEAREST or LINEAR or LINEAR_MIPMAP_LINEAR

    wrap_s : str = "REPEAT" # CLAMP_TO_EDGE or MIRRORED_REPEAT or REPEAT
    wrap_t : str = "REPEAT" # CLAMP_TO_EDGE or MIRRORED_REPEAT or REPEAT

@dataclass
class SamplerDeleteMessage(object):
    id : IDGroup


# Light Messages ================================================================================ 
@dataclass
class PointLight(object):
    range : float = -1

@dataclass
class SpotLight(object):
    range : float = -1
    inner_cone_angle_rad : float = 0
    outer_cone_angle_rad : float = pi/4

@dataclass
class DirectionalLight(object):
    range :float = -1

@dataclass
class LightCreateMessage(object):
    id : IDGroup
    name : str = None

    color : RGB = field(default_factory =[255, 255, 255])
    intensity : float = 1

    point : PointLight = None
    spot : SpotLight = None
    directional : DirectionalLight = None

@dataclass
class LightUpdateMessage(object):
    id : IDGroup

    color : RGB
    intensity : float = 1

@dataclass
class LightDeleteMessage(object):
    id : IDGroup


# Geometry Messages ================================================================================ 
@dataclass
class Attribute(object):
    view : IDGroup
    format : str
    semantic : str # Attribute semantic - string or vec?
    channel : int = None
    offset : int = 0
    stride : int = 0
    minimum_value : list[float] = None
    maximum_value : list[float] = None
    normalized : bool = False

@dataclass
class Index(object):
    view : IDGroup
    count : int
    format : str
    offset : int = 0
    stride : int = 0
    
@dataclass
class GeometryPatch(object):
    attributes : list[Attribute]
    vertex_count : int
    type : str
    material : IDGroup
    indices : Index = None

@dataclass
class GeometryCreateMessage(object):
    id : IDGroup
    patches : list[dict]
    name : str = None

@dataclass
class GeometryDeleteMessage(object):
    id : IDGroup


# Table Messages ================================================================================ 
@dataclass
class TableCreateMessage(object):
    id : IDGroup
    name : str = None

    meta : str = None
    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None 

@dataclass
class TableUpdateMessage(object):
    id : IDGroup

    meta : str = None
    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None 

@dataclass
class TableDeleteMessage(object):
    id : IDGroup


# Document Messages ================================================================================ 
@dataclass
class DocumentUpdateMessage(object):
    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None

@dataclass
class DocumentResetMessage(object):
    name : str = "placeholder for some content"
    

# Communication Messages ================================================================================ 
@dataclass
class InvokeIDType(object):
    entity : Optional[IDGroup] = None
    table : IDGroup = None
    plot : IDGroup = None

@dataclass
class MethodException(object):
    code : int
    message : str = None
    data : any = None

@dataclass
class SignalInvokeMessage(object):
    id : IDGroup

    signal_data : list[any]
    context : InvokeIDType = None # if empty it is on document

@dataclass
class MethodReplyMessage(object):
    invoke_id : str
    result : any = None
    method_exception : MethodException = None


"""
Client Messages
"""
@dataclass
class IntroMessage(object):
    client_name: str


@dataclass
class InvokeMethodMessage(object):
    method : IDGroup
    args : list[any]
    context : InvokeIDType = None
    invoke_id : str = None