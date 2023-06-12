"""Collection of Noodles Objects

Follows the specification in the cddl document, and
implements strict validation
"""

from enum import Enum
from math import pi
from queue import Queue
from typing import Callable, Optional, Any, Union, List, Tuple, Dict, NamedTuple

from pydantic import BaseModel, root_validator

""" =============================== ID's ============================= """


class ID(NamedTuple):
    slot: int
    gen: int

    def compact_str(self):
        return f"|{self.slot}/{self.gen}|"

    def __str__(self):
        return f"{type(self).__name__}{self.compact_str()}"

    def __key(self):
        return type(self), self.slot, self.gen

    def __eq__(self, other: object) -> bool:
        if type(other) is type(self):
            return self.__key() == other.__key()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


class MethodID(ID):
    pass


class SignalID(ID):
    pass


class EntityID(ID):
    pass


class PlotID(ID):
    pass


class BufferID(ID):
    pass


class BufferViewID(ID):
    pass


class MaterialID(ID):
    pass


class ImageID(ID):
    pass


class TextureID(ID):
    pass


class SamplerID(ID):
    pass


class LightID(ID):
    pass


class GeometryID(ID):
    pass


class TableID(ID):
    pass


""" ====================== Generic Parent Class ====================== """


class NoodleObject(BaseModel):
    """Parent Class for all noodle objects"""

    class Config:
        """Configuration for Validation"""

        arbitrary_types_allowed = True
        use_enum_values = True


class Delegate(NoodleObject):
    """Parent class for all delegates

    Defines general methods that should be available for all delegates

    Attributes:
        server (Server): server delegate is attached to
        id: (ID): Unique identifier for delegate
        name (str): Name of delegate
        signals (dict): Signals that can be called on delegate, method name to callable
    """

    server: object  # Better way to annotate this without introducing circular imports?
    id: ID = None
    name: Optional[str] = "No-Name"
    signals: Optional[dict] = {}

    def __str__(self):
        return f"{self.name} - {type(self).__name__} - {self.id.compact_str()}"


""" ====================== Common Definitions ====================== """

Vec3 = Tuple[float, float, float]
Vec4 = Tuple[float, float, float, float]
Mat3 = Tuple[float, float, float,
             float, float, float,
             float, float, float]
Mat4 = Tuple[float, float, float, float,
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


class IndexFormat(str, Enum):
    u8 = "U8"
    u16 = "U16"
    u32 = "U32"


class PrimitiveType(Enum):
    points = "POINTS"
    lines = "LINES"
    line_loop = "LINE_LOOP"
    line_strip = "LINE_STRIP"
    triangles = "TRIANGLES"
    triangle_strip = "TRIANGLE_STRIP"


class ColumnType(str, Enum):
    text = "TEXT"
    real = "REAL"
    integer = "INTEGER"


class BufferType(str, Enum):
    unknown = "UNK"
    geometry = "GEOMETRY"
    image = "IMAGE"


class SamplerMode(Enum):
    clamp_to_edge = "CLAMP_TO_EDGE"
    mirrored_repeat = "MIRRORED_REPEAT"
    repeat = "REPEAT"


class MagFilterTypes(Enum):
    nearest = "NEAREST"
    linear = "LINEAR"


class MinFilterTypes(Enum):
    nearest = "NEAREST"
    linear = "LINEAR"
    linear_mipmap_linear = "LINEAR_MIPMAP_LINEAR"


class SelectionRange(NoodleObject):
    key_from_inclusive: int
    key_to_exclusive: int


class Selection(NoodleObject):
    name: str
    rows: Optional[List[int]] = None
    row_ranges: Optional[List[SelectionRange]] = None


class MethodArg(NoodleObject):
    name: str
    doc: Optional[str] = None
    editor_hint: Optional[str] = None


class BoundingBox(NoodleObject):
    min: Vec3
    max: Vec3


class TextRepresentation(NoodleObject):
    txt: str
    font: Optional[str] = "Arial"
    height: Optional[float] = .25
    width: Optional[float] = -1.0


class WebRepresentation(NoodleObject):
    source: str
    height: Optional[float] = .5
    width: Optional[float] = .5


class InstanceSource(NoodleObject):
    view: BufferViewID  # view of mat4
    stride: int
    bb: Optional[BoundingBox] = None


class RenderRepresentation(NoodleObject):
    mesh: GeometryID
    instances: Optional[InstanceSource] = None


class TextureRef(NoodleObject):
    texture: TextureID
    transform: Optional[Mat3] = [1.0, 0.0, 0.0,
                                 0.0, 1.0, 0.0,
                                 0.0, 0.0, 1.0, ]
    texture_coord_slot: Optional[int] = 0.0


class PBRInfo(NoodleObject):
    base_color: RGBA = [1.0, 1.0, 1.0, 1.0]
    base_color_texture: Optional[TextureRef] = None  # assume SRGB, no premult alpha

    metallic: Optional[float] = 1.0
    roughness: Optional[float] = 1.0
    metal_rough_texture: Optional[TextureRef] = None  # assume linear, ONLY RG used


class PointLight(NoodleObject):
    range: float = -1.0


class SpotLight(NoodleObject):
    range: float = -1.0
    inner_cone_angle_rad: float = 0.0
    outer_cone_angle_rad: float = pi / 4


class DirectionalLight(NoodleObject):
    range: float = -1.0


class Attribute(NoodleObject):
    view: BufferViewID
    semantic: AttributeSemantic
    channel: Optional[int] = None
    offset: Optional[int] = 0
    stride: Optional[int] = 0
    format: Format
    minimum_value: Optional[List[float]] = None
    maximum_value: Optional[List[float]] = None
    normalized: Optional[bool] = False


class Index(NoodleObject):
    view: BufferViewID
    count: int
    offset: Optional[int] = 0
    stride: Optional[int] = 0
    format: IndexFormat


class GeometryPatch(NoodleObject):
    attributes: List[Attribute]
    vertex_count: int
    indices: Optional[Index] = None
    type: PrimitiveType
    material: MaterialID  # Material ID


class InvokeIDType(NoodleObject):
    entity: Optional[EntityID] = None
    table: Optional[TableID] = None
    plot: Optional[PlotID] = None

    @root_validator
    def one_of_three(cls, values):
        already_found = False
        for field in values:
            if values[field] and already_found:
                raise ValueError("More than one field entered")
            elif values[field]:
                already_found = True

        if not already_found:
            raise ValueError("No field provided")
        else:
            return values


class TableColumnInfo(NoodleObject):
    name: str
    type: ColumnType


class TableInitData(NoodleObject):
    columns: List[TableColumnInfo]
    keys: List[int]
    data: List[List[Union[float, int, str]]]
    selections: Optional[List[Selection]] = None

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


""" ====================== NOODLE COMPONENTS / DELEGATES ====================== """


class Method(Delegate):
    id: MethodID
    name: str
    doc: Optional[str] = None
    return_doc: Optional[str] = None
    arg_doc: List[MethodArg] = []


class Signal(Delegate):
    id: SignalID
    name: str
    doc: Optional[str] = None
    arg_doc: List[MethodArg] = None


class Entity(Delegate):
    id: EntityID
    name: Optional[str] = None

    parent: Optional[EntityID] = None
    transform: Optional[Mat4] = None

    text_rep: Optional[TextRepresentation] = None
    web_rep: Optional[WebRepresentation] = None
    render_rep: Optional[RenderRepresentation] = None

    lights: Optional[List[LightID]] = None
    tables: Optional[List[TableID]] = None
    plots: Optional[List[PlotID]] = None
    tags: Optional[List[str]] = None
    methods_list: Optional[List[MethodID]] = None
    signals_list: Optional[List[SignalID]] = None

    influence: Optional[BoundingBox] = None


class Plot(Delegate):
    id: PlotID
    name: Optional[str] = None

    table: Optional[TableID] = None

    simple_plot: Optional[str] = None
    url_plot: Optional[str] = None

    methods_list: Optional[List[MethodID]] = None
    signals_list: Optional[List[SignalID]] = None

    @root_validator
    def one_of(cls, values):
        if bool(values['simple_plot']) != bool(values['url_plot']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class Buffer(Delegate):
    id: BufferID
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


class BufferView(Delegate):
    id: BufferViewID
    name: Optional[str] = None
    source_buffer: BufferID

    type: BufferType = BufferType.unknown
    offset: int
    length: int


class Material(Delegate):
    id: MaterialID
    name: Optional[str] = None

    pbr_info: Optional[PBRInfo] = PBRInfo()
    normal_texture: Optional[TextureRef] = None

    occlusion_texture: Optional[TextureRef] = None  # assumed to be linear, ONLY R used
    occlusion_texture_factor: Optional[float] = 1.0

    emissive_texture: Optional[TextureRef] = None  # assumed to be SRGB, ignore A
    emissive_factor: Optional[Vec3] = [1.0, 1.0, 1.0]

    use_alpha: Optional[bool] = False
    alpha_cutoff: Optional[float] = .5

    double_sided: Optional[bool] = False


class Image(Delegate):
    id: ImageID
    name: Optional[str] = None

    buffer_source: BufferID = None
    uri_source: str = None

    @root_validator
    def one_of(cls, values):
        if bool(values['buffer_source']) != bool(values['uri_source']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class Texture(Delegate):
    id: TextureID
    name: Optional[str] = None
    image: ImageID  # Image ID
    sampler: Optional[SamplerID] = None


class Sampler(Delegate):
    id: SamplerID
    name: Optional[str] = None

    mag_filter: Optional[MagFilterTypes] = MagFilterTypes.linear
    min_filter: Optional[MinFilterTypes] = MinFilterTypes.linear_mipmap_linear

    wrap_s: Optional[SamplerMode] = "REPEAT"
    wrap_t: Optional[SamplerMode] = "REPEAT"


class Light(Delegate):
    id: LightID
    name: Optional[str] = None

    color: Optional[RGB] = [1.0, 1.0, 1.0]
    intensity: Optional[float] = 1.0

    point: PointLight = None
    spot: SpotLight = None
    directional: DirectionalLight = None

    @root_validator
    def one_of(cls, values):
        already_found = False
        for field in ['point', 'spot', 'directional']:
            if values[field] and already_found:
                raise ValueError("More than one field entered")
            elif values[field]:
                already_found = True

        if not already_found:
            raise ValueError("No field provided")
        else:
            return values


class Geometry(Delegate):
    id: GeometryID
    name: Optional[str] = None
    patches: List[GeometryPatch]


class Table(Delegate):
    id: TableID
    name: Optional[str] = None

    meta: Optional[str] = None
    methods_list: Optional[List[MethodID]] = None
    signals_list: Optional[List[SignalID]] = None

    def handle_insert(self, new_rows: list[list[int]]):
        pass

    def handle_update(self, keys: list[int], rows: list[list[int]]):
        pass

    def handle_delete(self, keys: list[int]):
        pass

    def handle_clear(self):
        pass

    def handle_set_selection(self, selection: Selection):
        pass

    # Signals ---------------------------------------------------
    def table_reset(self, tbl_init: TableInitData):
        """Invoke table reset signal"""
        pass

    def table_updated(self, keys: list[int], rows: list[list[int]]):
        pass

    def table_rows_removed(self, keys: list[int]):
        pass

    def table_selection_updated(self, selection: Selection):
        pass


""" ====================== Communication Objects ====================== """


class Invoke(NoodleObject):
    id: SignalID
    context: Optional[InvokeIDType] = None  # if empty - document
    signal_data: List[Any]


# Note: this isn't technically an exception
# for now this uses a model so that it can be validated / sent as message easier
# Fix to inherit from Exception, maybe use separate model for sending
# class MethodException(NoodleObject):
#     code: int
#     message: Optional[str] = None
#     data: Optional[Any] = None
class MethodException(Exception):
    def __init__(self, code: int, message: Optional[str] = None, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data


class Reply(NoodleObject):
    invoke_id: str
    result: Optional[Any] = None
    method_exception: Optional[MethodException] = None


""" ====================== Miscellaneous Objects ====================== """

id_map = {
    Method: MethodID,
    Signal: SignalID,
    Table: TableID,
    Plot: PlotID,
    Entity: EntityID,
    Material: MaterialID,
    Geometry: GeometryID,
    Light: LightID,
    Image: ImageID,
    Texture: TextureID,
    Sampler: SamplerID,
    Buffer: BufferID,
    BufferView: BufferViewID
}


class InjectedMethod(object):
    """Representation of user Injected Method
    
    Note that the call method automatically inserts a server
    reference as an argument to all user defined functions
    """

    def __init__(self, server, method) -> None:
        self.server = server
        self.method = method

    def __call__(self, *args, **kwargs):
        return self.method(self.server, *args, **kwargs)


class SlotTracker(object):
    """Object to keep track of next available slot
    
    Next slot is next unused slot while on_deck
    keeps track of slots that have opened up
    """

    def __init__(self):
        self.next_slot = 0
        self.on_deck = Queue()


class StartingComponent(object):
    """User input object for setting starting components on server"""

    def __init__(self, kind, component_attrs: Dict[str, Any], method: Optional[Callable] = None):
        self.type = kind
        self.component_attrs = component_attrs
        self.method = method
