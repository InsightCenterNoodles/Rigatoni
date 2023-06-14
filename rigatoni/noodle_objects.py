"""Collection of Noodles Objects

Follows the specification in the cddl document, and
implements strict validation
"""

from enum import Enum
from math import pi
from queue import Queue
from typing import Callable, Optional, Any, List, Tuple, Dict, NamedTuple

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

    Defines general methods that should be available for all delegates.

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

    @root_validator(allow_reuse=True)
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
    data: List[List[Any]]  # Originally tried union, but currently order is used to coerce by pydantic
    selections: Optional[List[Selection]] = None

    # too much overhead? - strict mode
    @root_validator(allow_reuse=True)
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
    """A method that clients can request the server to call.

    Attributes:
        id: ID for the method
        name: Name of the method
        doc: Documentation for the method
        return_doc: Documentation for the return value
        arg_doc: Documentation for the arguments
    """

    id: MethodID
    name: str
    doc: Optional[str] = None
    return_doc: Optional[str] = None
    arg_doc: List[MethodArg] = []


class Signal(Delegate):
    """A signal that the server can send to update clients.

    Attributes:
        id: ID for the signal
        name: Name of the signal
        doc: Documentation for the signal
        arg_doc: Documentation for the arguments
    """

    id: SignalID
    name: str
    doc: Optional[str] = None
    arg_doc: List[MethodArg] = None


class Entity(Delegate):
    """Container for other entities, possibly renderable, has associated methods and signals

    Args:
        id (EntityID): ID for the entity
        name (str): Name of the entity
        parent (EntityID): Parent entity
        transform (Mat4): Local transform for the entity
        text_rep (TextRepresentation): Text representation for the entity
        web_rep (WebRepresentation): Web representation for the entity
        render_rep (RenderRepresentation): Render representation for the entity
        lights (List[LightID]): List of lights attached to the entity
        tables (List[TableID]): List of tables attached to the entity
        plots (List[PlotID]): List of plots attached to the entity
        tags (List[str]): List of tags for the entity
        methods_list (List[MethodID]): List of methods attached to the entity
        signals_list (List[SignalID]): List of signals attached to the entity
        influence (Optional[BoundingBox]): Bounding box for the entity
    """

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
    """An abstract plot object.

    Attributes:
        id: ID for the plot
        name: Name of the plot
        table: Table to plot
        simple_plot: Simple plot to render
        url_plot: URL for plot to render
        methods_list: List of methods attached to the plot
        signals_list: List of signals attached to the plot
    """

    id: PlotID
    name: Optional[str] = None

    table: Optional[TableID] = None

    simple_plot: Optional[str] = None
    url_plot: Optional[str] = None

    methods_list: Optional[List[MethodID]] = None
    signals_list: Optional[List[SignalID]] = None

    @root_validator(allow_reuse=True)
    def one_of(cls, values):
        if bool(values['simple_plot']) != bool(values['url_plot']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class Buffer(Delegate):
    """A buffer of bytes containing data for an image or a mesh.

    Attributes:
        id: ID for the buffer
        name: Name of the buffer
        size: Size of the buffer in bytes
        inline_bytes: Bytes of the buffer
        uri_bytes: URI for the bytes
    """
    id: BufferID
    name: Optional[str] = None
    size: int = None

    inline_bytes: bytes = None
    uri_bytes: str = None

    @root_validator(allow_reuse=True)
    def one_of(cls, values):
        if bool(values['inline_bytes']) != bool(values['uri_bytes']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class BufferView(Delegate):
    """A view into a buffer, specifying a subset of the buffer and how to interpret it.

    Attributes:
        id: ID for the buffer view
        name: Name of the buffer view
        source_buffer: Buffer that the view is referring to
        type: Type of the buffer view
        offset: Offset into the buffer in bytes
        length: Length of the buffer view in bytes
    """
    id: BufferViewID
    name: Optional[str] = None
    source_buffer: BufferID

    type: BufferType = BufferType.unknown
    offset: int
    length: int


class Material(Delegate):
    """A material that can be applied to a mesh.

    Attributes:
        id: ID for the material
        name: Name of the material
        pbr_info: Information for physically based rendering
        normal_texture: Texture for normals
        occlusion_texture: Texture for occlusion
        occlusion_texture_factor: Factor for occlusion
        emissive_texture: Texture for emissive
        emissive_factor: Factor for emissive
        use_alpha: Whether to use alpha
        alpha_cutoff: Alpha cutoff
        double_sided: Whether the material is double-sided
    """
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
    """An image, can be used for a texture

    Attributes:
        id: ID for the image
        name: Name of the image
        buffer_source: Buffer that the image is stored in
        uri_source: URI for the bytes if they are hosted externally
    """
    id: ImageID
    name: Optional[str] = None

    buffer_source: BufferID = None
    uri_source: str = None

    @root_validator(allow_reuse=True)
    def one_of(cls, values):
        if bool(values['buffer_source']) != bool(values['uri_source']):
            return values
        else:
            raise ValueError("One plot type must be specified")


class Texture(Delegate):
    """A texture, can be used for a material

    Attributes:
        id: ID for the texture
        name: Name of the texture
        image: Image to use for the texture
        sampler: Sampler to use for the texture
    """
    id: TextureID
    name: Optional[str] = None
    image: ImageID  # Image ID
    sampler: Optional[SamplerID] = None


class Sampler(Delegate):
    """A sampler to use for a texture

    Attributes:
        id: ID for the sampler
        name: Name of the sampler
        mag_filter: Magnification filter
        min_filter: Minification filter
        wrap_s: Wrap mode for S
        wrap_t: Wrap mode for T
    """
    id: SamplerID
    name: Optional[str] = None

    mag_filter: Optional[MagFilterTypes] = MagFilterTypes.linear
    min_filter: Optional[MinFilterTypes] = MinFilterTypes.linear_mipmap_linear

    wrap_s: Optional[SamplerMode] = "REPEAT"
    wrap_t: Optional[SamplerMode] = "REPEAT"


class Light(Delegate):
    """Represents a light in the scene

    Attributes:
        id: ID for the light
        name: Name of the light
        color: Color of the light
        intensity: Intensity of the light
        point: Point light information
        spot: Spotlight information
        directional: Directional light information
    """
    id: LightID
    name: Optional[str] = None

    color: Optional[RGB] = [1.0, 1.0, 1.0]
    intensity: Optional[float] = 1.0

    point: PointLight = None
    spot: SpotLight = None
    directional: DirectionalLight = None

    @root_validator(allow_reuse=True)
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
    """Represents geometry in the scene and can be used for meshes

    Attributes:
        id: ID for the geometry
        name: Name of the geometry
        patches: Patches that make up the geometry
    """
    id: GeometryID
    name: Optional[str] = None
    patches: List[GeometryPatch]


class Table(Delegate):
    """Object to store tabular data.

    Attributes:
        id: ID for the table
        name: Name of the table
        meta: Metadata for the table
        methods_list: List of methods for the table
        signals_list: List of signals for the table
    """
    id: TableID
    name: Optional[str] = None

    meta: Optional[str] = None
    methods_list: Optional[List[MethodID]] = None
    signals_list: Optional[List[SignalID]] = None

    def handle_insert(self, new_rows: List[List[int]]):
        """Method to handle inserting into the table"""
        pass

    def handle_update(self, keys: List[int], rows: List[List[int]]):
        """Method to handle updating the table"""
        pass

    def handle_delete(self, keys: List[int]):
        """Method to handle deleting from the table"""
        pass

    def handle_clear(self):
        """Method to handle clearing the table"""
        pass

    def handle_set_selection(self, selection: Selection):
        """Method to handle setting a selection"""
        pass

    # Signals ---------------------------------------------------
    def table_reset(self, tbl_init: TableInitData):
        """Invoke table reset signal"""
        pass

    def table_updated(self, keys: List[int], rows: List[List[int]]):
        """Invoke table updated signal"""
        pass

    def table_rows_removed(self, keys: List[int]):
        """Invoke table rows removed signal"""
        pass

    def table_selection_updated(self, selection: Selection):
        """Invoke table selection updated signal"""
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


def get_context(delegate):
    """Helper to get context from delegate"""

    if isinstance(delegate, Entity):
        return {"entity": delegate.id}
    elif isinstance(delegate, Table):
        return {"table": delegate.id}
    elif isinstance(delegate, Plot):
        return {"plot": delegate.id}
    else:
        return None
