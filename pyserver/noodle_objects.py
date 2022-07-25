from collections import namedtuple
from dataclasses import  dataclass, field
from math import pi
from queue import Queue
import queue
from typing import Optional

""" ====================== Common Definitions ====================== """

Vec3 = [float] * 3
Vec4 = [float] * 4
Mat3 = [float] * 9
Mat4 = [float] * 16

RGB = [float] * 3
RGBA = [float] * 4

IDGroup = namedtuple("IDGroup", ["slot", "gen"])


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
class TextureRef(object):
    texture : IDGroup
    transform : Mat3 = field(default_factory = [1, 0, 0,
                                                0, 1, 0,
                                                0, 0, 1,])
    texture_coord_slot : int = 0

@dataclass
class PBRInfo(object):
    base_color : RGBA = field(default_factory = [255, 255, 255, 1]) # white as default
    base_color_texture : TextureRef = None # assume SRGB, no premult alpha

    metallic : float = 1
    roughness : float = 1
    metal_rough_texture : TextureRef = None # assume linear, ONLY RG used

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
class InvokeIDType(object):
    entity : Optional[IDGroup] = None
    table : IDGroup = None
    plot : IDGroup = None

@dataclass
class MethodException(Exception):
    code : int
    message : str = None
    data : any = None


""" ====================== NOOODLE COMPONENTS ====================== """

@dataclass
class Method(object):
    id : IDGroup
    name : str
    doc : str = None
    return_doc : str = None
    arg_doc : list[MethodArg] = None


@dataclass
class Signal(object):
    id : IDGroup
    name : str
    doc : str = None
    arg_doc : list[MethodArg] = None

@dataclass
class Entity(object):
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
class Plot(object):
    id : IDGroup
    name : str = None

    table : IDGroup = None

    simple_plot : str = None
    url_plot : str = None

    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None


@dataclass
class Buffer(object):
    id : IDGroup
    name : str = None
    size : int = None

    inline_bytes : bytes = None
    uri_bytes : str = None

@dataclass
class BufferView(object):
    id : IDGroup
    source_buffer : IDGroup

    type : str
    offset : int
    length : int

    name : str = None

@dataclass
class Material(object):
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
class Image(object):
    id : IDGroup
    name : str = None

    buffer_source : IDGroup = None
    uri_source : str = None

@dataclass
class Texture(object):
    id : IDGroup
    image : IDGroup
    name : str = None
    sampler : IDGroup = None # Revist default sampler

@dataclass
class Sampler(object):
    id : IDGroup
    name : str = None

    mag_filter: str = "LINEAR" # NEAREST or LINEAR
    min_filter : str = "LINEAR_MIPMAP_LINEAR" # NEAREST or LINEAR or LINEAR_MIPMAP_LINEAR

    wrap_s : str = "REPEAT" # CLAMP_TO_EDGE or MIRRORED_REPEAT or REPEAT
    wrap_t : str = "REPEAT" # CLAMP_TO_EDGE or MIRRORED_REPEAT or REPEAT

@dataclass
class Light(object):
    id : IDGroup
    name : str = None

    color : RGB = field(default_factory =[255, 255, 255])
    intensity : float = 1

    point : PointLight = None
    spot : SpotLight = None
    directional : DirectionalLight = None

@dataclass
class Geometry(object):
    id : IDGroup
    patches : list[GeometryPatch]
    name : str = None


@dataclass
class Table(object):
    id : IDGroup
    name : str = None

    meta : str = None
    methods_list : list[IDGroup] = None
    signals_list : list[IDGroup] = None 
 

""" ====================== Communication Objects ====================== """

@dataclass
class Invoke(object):
    id : IDGroup
    signal_data : list[any]
    context : InvokeIDType = None # if empty it is on document

@dataclass
class Reply(object):
    invoke_id : str
    result : any = None
    method_exception : MethodException = None


""" ====================== Miscellaneous Objects ====================== """

class InjectedMethod(object):

    def __init__(self, server, method) -> None:
        self.server = server
        self.method = method

    def __call__(self, *args, **kwds):
        return self.method(self.server, *args, **kwds)


class SlotTracker(object):

    def __init__(self):
        self.next_slot = 0
        self.on_deck = Queue()