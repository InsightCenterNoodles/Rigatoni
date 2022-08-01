from collections import namedtuple
from enum import Enum
from math import pi
from queue import Queue
from typing import ClassVar, Literal, Optional, Any, Union
import weakref

import cbor2
import websockets
from pydantic import BaseModel, root_validator

""" ====================== Generic Parent Class ====================== """
IDGroup = namedtuple("IDGroup", ["slot", "gen"])

class Component(BaseModel):

    host_server: ClassVar = None
    __slots__ = ['__weakref__']
    id: IDGroup = None

    class Config:
        """Validation Configuration"""
        
        arbitrary_types_allowed = True
        #smart_union = True - used to avoid coercion of unions

    def broadcast(self, message: list):
        """Broadcast message to all connected clients"""
        
        print(f"Broadcasting Message: {message}")
        encoded = cbor2.dumps(message)
        websockets.broadcast(Component.host_server.clients, encoded)


    def __del__(self):

        # Update ID's available
        available_id = IDGroup(self.id.slot, self.id.gen + 1)
        self.host_server.ids[type(self)].on_deck.put(available_id)

        # Broadcast
        message = Component.host_server.prepare_message("delete", self)
        self.broadcast(message)

        print(f"OFFICIALLY DELETED COMPONENT '{self}'")


class Model(BaseModel):
    """Parent Class for Non-Components"""

    class Config:
        arbitrary_types_allowed = True



""" ====================== Common Definitions ====================== """

Vec3 = tuple[float, float, float]
Vec4 = tuple[float, float, float, float]
Mat3 = tuple[float, float, float, 
             float, float, float, 
             float, float, float]
Mat4 = tuple[float, float, float, float,
             float, float, float, float,
             float, float, float, float,
             float, float, float, float]

RGB = Vec3
RGBA = Vec4

class AttributeSemantic(Enum):
    position = "POSITION"
    normal = "NORMAL"
    tangent = "TANGENT"
    texture = "TEXTURE"
    color = "COLOR"

class Format(Enum):
    u8 = "U8"
    u16 = "U16"
    u32 = "U32"
    u8vec4 = "U8VEC4"
    u16vec2 = "U16VEC2"
    vec2 = "VEC2"
    vec3 = "VEC3"
    vec4 = "VEC4"
    mat3 = "MAT3"
    mat4 = "MAT4"

class PrimitiveType(Enum):
    points = "POINTS"
    lines = "LINES"
    line_loop = "LINE_LOOP"
    line_strip = "LINE_STRIP"
    triangles = "TRIANGLES"
    triangle_strip = "TRIANGLE_STRIP"

class SamplerMode(Enum):
    clamp_to_edge = "CLAMP_TO_EDGE"
    mirrored_repeat = "MIRRORED_REPEAT"
    repeat = "REPEAT"

class SelectionRange(BaseModel):
    key_from_inclusive: int
    key_to_exclusive: int

class Selection(Model):
    name: str
    rows: Optional[list[int]] = None
    row_ranges: Optional[list[SelectionRange]] = None

class MethodArg(Model): 
    name: str
    doc: Optional[str] = None 
    editor_hint: Optional[str] = None

class BoundingBox(Model):
    min: Vec3
    max: Vec3

class TextRepresentation(Model):
    txt: str
    font: Optional[str] = "Arial"
    height: Optional[float] = .25
    width: Optional[float] = -1

class WebRepresentation(Model):
    source: str
    height: Optional[float] = .5
    width: Optional[float] = .5

class InstanceSource(Model):
    view: IDGroup # Buffer View ID, view of mat4
    stride: int 
    bb: Optional[BoundingBox] = None

class RenderRepresentation(Model):
    mesh: IDGroup # Entity ID
    instances: Optional[InstanceSource] = None

class TextureRef(Model):
    texture: IDGroup
    transform: Optional[Mat3] = [1, 0, 0,
                       0, 1, 0,
                       0, 0, 1,]
    texture_coord_slot: Optional[int] = 0

class PBRInfo(Model):
    base_color: RGBA = [255, 255, 255, 1]
    base_color_texture: Optional[TextureRef] = None # assume SRGB, no premult alpha

    metallic: Optional[float] = 1
    roughness: Optional[float] = 1
    metal_rough_texture: Optional[TextureRef] = None # assume linear, ONLY RG used

class PointLight(Model):
    range: float = -1

class SpotLight(Model):
    range: float = -1
    inner_cone_angle_rad: float = 0
    outer_cone_angle_rad: float = pi/4

class DirectionalLight(Model):
    range: float = -1

class Attribute(Model):
    view: IDGroup
    semantic: AttributeSemantic
    channel: Optional[int] = None
    offset: Optional[int] = 0
    stride: Optional[int] = 0
    format: Format
    minimum_value: Optional[list[float]] = None
    maximum_value: Optional[list[float]] = None
    normalized: Optional[bool] = False

class Index(Model):
    view: IDGroup # Buffer View ID
    count: int
    offset: Optional[int] = 0
    stride: Optional[int] = 0
    format: Literal["U8", "U16", "U32"]

class GeometryPatch(Model):
    attributes: list[Attribute]
    vertex_count: int
    indices: Optional[Index] = None
    type: PrimitiveType
    material: IDGroup # Material ID

class InvokeIDType(Model):
    entity: Optional[IDGroup] = None
    table: Optional[IDGroup] = None
    plot: Optional[IDGroup] = None

    @root_validator
    def one_of_three(cls, values):
        already_found  = False
        for field in values:
            if values[field] and already_found:
                raise ValueError("More than one field entered")
            elif values[field]:
                already_found = True
        
        if not already_found:
            raise ValueError("No field provided")
        else:
            return values

class TableColumnInfo(Model):
    name: str
    type: Literal["TEXT", "REAL", "INTEGER"]

class TableInitData(Model):
    columns: list[TableColumnInfo]
    keys: list[int]
    data: list[list[Union[float, int, str]]]
    selections: Optional[list[Selection]] = None

    # too much overhead? - strict mode
    @root_validator
    def types_match(cls, values):
        for row in values['data']:
            for col, i in zip(values['columns'], range(len(row))):
                text_mismatch = isinstance(row[i], str) and col.type != "TEXT"
                real_mismatch = isinstance(row[i], float) and col.type != "REAL"
                int_mismatch = isinstance(row[i], int) and col.type != "INTEGER"
                if text_mismatch or real_mismatch or int_mismatch:
                    raise ValueError(f"Column Info doesn't match type in data: {col, row[i]}")
        return values
        


""" ====================== NOOODLE COMPONENTS ====================== """


class Method(Component):
    id: IDGroup
    name: str
    doc: Optional[str] = None
    return_doc: Optional[str] = None
    arg_doc: list[MethodArg] = None


class Signal(Component):
    id: IDGroup
    name: str
    doc: Optional[str] = None
    arg_doc: list[MethodArg] = None


class Entity(Component):
    id: IDGroup
    name: Optional[str] = None

    parent: Optional[IDGroup] = None
    transform: Optional[Mat4] = None

    null_rep: Optional[Any] = None
    text_rep: Optional[TextRepresentation] = None
    web_rep: Optional[WebRepresentation] = None
    render_rep: Optional[RenderRepresentation] = None

    lights: Optional[list[IDGroup]] = None
    tables: Optional[list[IDGroup]] = None
    plots: Optional[list[IDGroup]] = None
    tags: Optional[list[str]] = None
    methods_list: Optional[list[IDGroup]] = None
    signals_list: Optional[list[IDGroup]] = None

    influence: Optional[BoundingBox] = None

    @root_validator
    def one_of(cls, values):
        already_found  = False
        for field in ['null_rep', 'text_rep', 'web_rep', 'render_rep']:
            if values[field] and already_found:
                raise ValueError("More than one field entered")
            elif values[field]:
                already_found = True
        
        if not already_found:
            raise ValueError("No field provided")
        else:
            return values


class Plot(Component):
    id: IDGroup
    name: Optional[str] = None

    table: Optional[IDGroup] = None

    simple_plot: Optional[str] = None
    url_plot: Optional[str] = None

    methods_list: Optional[list[IDGroup]] = None
    signals_list: Optional[list[IDGroup]] = None

    @root_validator
    def one_of(cls, values):
        if bool(values['simple_plot']) != bool(values['url_plot']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class Buffer(Component):
    id: IDGroup
    name: Optional[str] = None
    size: int = None

    inline_bytes: bytes = None
    uri_bytes: str = None

    @root_validator
    def one_of(cls, values):
        if bool(values['inline_bytes']) != bool(values['uri_bytes']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class BufferView(Component):
    id: IDGroup
    name: Optional[str] = None    
    source_buffer: IDGroup # Buffer ID

    type: Literal["UNK", "GEOMETRY", "IMAGE"]
    offset: int
    length: int

    
class Material(Component):
    id: IDGroup
    name: Optional[str] = None

    pbr_info: Optional[PBRInfo] = PBRInfo()
    normal_texture: Optional[TextureRef] = None

    occlusion_texture: Optional[TextureRef] = None # assumed to be linear, ONLY R used
    occlusion_texture_factor: Optional[float] = 1

    emissive_texture: Optional[TextureRef] = None # assumed to be SRGB, ignore A
    emissive_factor: Optional[Vec3] = [1, 1, 1]

    use_alpha: Optional[bool] = False
    alpha_cutoff: Optional[float] = .5

    double_sided: Optional[bool] = False


class Image(Component):
    id: IDGroup
    name: Optional[str] = None

    buffer_source: IDGroup = None
    uri_source: str = None

    @root_validator
    def one_of(cls, values):
        if bool(values['buffer_source']) != bool(values['uri_source']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class Texture(Component):
    id: IDGroup
    name: Optional[str] = None
    image: IDGroup # Image ID
    sampler: Optional[IDGroup] = None


class Sampler(Component):
    id: IDGroup
    name: Optional[str] = None

    mag_filter: Optional[Literal["NEAREST", "LINEAR"]] = "LINEAR"
    min_filter: Optional[Literal["NEAREST", "LINEAR", "LINEAR_MIPMAP_LINEAR"]] = "LINEAR_MIPMAP_LINEAR"

    wrap_s: Optional[SamplerMode] = "REPEAT" 
    wrap_t: Optional[SamplerMode] = "REPEAT" 


class Light(Component):
    id: IDGroup
    name: Optional[str] = None

    color: Optional[RGB] = [255, 255, 255]
    intensity: Optional[float] = 1

    point: PointLight = None
    spot: SpotLight = None
    directional: DirectionalLight = None

    @root_validator
    def one_of(cls, values):
        already_found  = False
        for field in ['point', 'spot', 'directional']:
            if values[field] and already_found:
                raise ValueError("More than one field entered")
            elif values[field]:
                already_found = True
        
        if not already_found:
            raise ValueError("No field provided")
        else:
            return values


class Geometry(Component):
    id: IDGroup
    name: Optional[str] = None
    patches: list[GeometryPatch]


class Table(Component):
    id: IDGroup
    name: Optional[str] = None

    meta: Optional[str] = None
    methods_list: Optional[list[IDGroup]] = None
    signals_list: Optional[list[IDGroup]] = None 
 

""" ====================== Communication Objects ====================== """


class Invoke(Model):
    id: IDGroup # Signal ID
    context: Optional[InvokeIDType] = None # if empty - document
    signal_data: list[Any]


# Note: this isn't technically an exception
# for now this uses a model so that it can be validated / sent as message easier
class MethodException(Model):
    code: int
    message: Optional[str] = None
    data: Optional[Any] = None

class Reply(Model):
    invoke_id: str
    result: Optional[Any] = None
    method_exception: Optional[MethodException] = None


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
