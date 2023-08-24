"""Collection of Noodles Objects

Follows the specification in the cddl document, and
implements strict validation
"""

from enum import Enum
from math import pi
from queue import Queue
from typing import Callable, Optional, Any, List, Tuple, Dict, NamedTuple

from pydantic import ConfigDict, BaseModel, model_validator

""" =============================== ID's ============================= """


class ID(NamedTuple):
    """Base class for all ID's

    Each ID is composed of a slot and a generation, resulting in a tuple like id ex. (0, 0). Both are positive
    integers that are filled in increasing order. Slots are taken first, but once the slot is freed, it can be used
    with a new generation. For example, a method is created -> (0, 0), then another is created -> (1, 0), then method
    (0, 0) is deleted. Now, the next method created will be (0, 1).

    Attributes:
        slot (int): Slot of the ID
        gen (int): Generation of the ID
    """

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
    """ID specifically for methods"""
    pass


class SignalID(ID):
    """ID specifically for signals"""
    pass


class EntityID(ID):
    """ID specifically for entities"""
    pass


class PlotID(ID):
    """ID specifically for plots"""
    pass


class BufferID(ID):
    """ID specifically for buffers"""
    pass


class BufferViewID(ID):
    """ID specifically for buffer views"""
    pass


class MaterialID(ID):
    """ID specifically for materials"""
    pass


class ImageID(ID):
    """ID specifically for images"""
    pass


class TextureID(ID):
    """ID specifically for textures"""
    pass


class SamplerID(ID):
    """ID specifically for samplers"""
    pass


class LightID(ID):
    """ID specifically for lights"""
    pass


class GeometryID(ID):
    """ID specifically for geometries"""
    pass


class TableID(ID):
    """ID specifically for tables"""
    pass


""" ====================== Generic Parent Class ====================== """


class NoodleObject(BaseModel):
    """Parent Class for all noodle objects"""
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)


class Delegate(NoodleObject):
    """Parent class for all delegates

    Defines general methods that should be available for all delegates. In this context, a delegate refers to an
    object in a NOODLES scene that can be subclassed and extended by the user. For example, a user can create an
    implementation for a table that specifically suits their needs. The server's job is essentially to manage the
    state of all delegates, and to call the appropriate methods on them when necessary. Most methods defined by
    the user will also be to manipulate the state of the delegates.

    Attributes:
        server (Server): server delegate is attached to
        id: (ID): Unique identifier for delegate
        name (Optional[str]): Name of delegate
        signals (Optional[dict]): Signals that can be called on delegate, method name to callable
    """

    server: object  # Better way to annotate this without introducing circular imports?
    id: ID
    name: Optional[str] = "No-Name"
    signals: Optional[dict] = {}

    def __str__(self):
        return f"{self.name} - {type(self).__name__} - {self.id.compact_str()}"


""" ====================== Common Definitions ====================== """

Vec3 = List[float]  # Length 3
Vec4 = List[float]  # Length 4
Mat3 = List[float]  # Length 9
Mat4 = List[float]  # Length 16

RGB = Vec3
RGBA = Vec4


class AttributeSemantic(Enum):
    """String indicating type of attribute, used in Attribute inside of geometry patch

    Takes value of either POSITION, NORMAL, TANGENT, TEXTURE, or COLOR
    """

    position = "POSITION"
    normal = "NORMAL"
    tangent = "TANGENT"
    texture = "TEXTURE"
    color = "COLOR"


class Format(Enum):
    """String indicating format of byte data for an attribute

    Used in Attribute inside of geometry patch. Takes value of either U8, U16, U32, U8VEC4, U16VEC2,
    VEC2, VEC3, VEC4, MAT3, or MAT4
    """

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
    """String indicating format of byte data for an index

    Used in Index inside of geometry patch. Takes value of either U8, U16, or U32
    """
    u8 = "U8"
    u16 = "U16"
    u32 = "U32"


class PrimitiveType(Enum):
    """String indicating type of primitive used in a geometry patch

    Takes value of either POINTS, LINES, LINE_LOOP, LINE_STRIP, TRIANGLES, or TRIANGLE_STRIP
    """
    points = "POINTS"
    lines = "LINES"
    line_loop = "LINE_LOOP"
    line_strip = "LINE_STRIP"
    triangles = "TRIANGLES"
    triangle_strip = "TRIANGLE_STRIP"


class ColumnType(str, Enum):
    """String indicating type of data stored in a column in a table

    Used in TableColumnInfo inside TableInitData. Takes value of either TEXT, REAL, or INTEGER
    """
    text = "TEXT"
    real = "REAL"
    integer = "INTEGER"


class BufferType(str, Enum):
    """String indicating type of data stored in a buffer

    Used in BufferView. Takes value of either UNK, GEOMETRY, or IMAGE
    """
    unknown = "UNK"
    geometry = "GEOMETRY"
    image = "IMAGE"


class SamplerMode(Enum):
    """String options for sampler mode

    Used in Sampler. Takes value of either CLAMP_TO_EDGE, MIRRORED_REPEAT, or REPEAT
    """
    clamp_to_edge = "CLAMP_TO_EDGE"
    mirrored_repeat = "MIRRORED_REPEAT"
    repeat = "REPEAT"


class MagFilterTypes(Enum):
    """Options for magnification filter type

    Used in Sampler. Takes value of either NEAREST or LINEAR
    """
    nearest = "NEAREST"
    linear = "LINEAR"


class MinFilterTypes(Enum):
    """Options for minification filter type

    Used in Sampler. Takes value of either NEAREST, LINEAR, or LINEAR_MIPMAP_LINEAR
    """
    nearest = "NEAREST"
    linear = "LINEAR"
    linear_mipmap_linear = "LINEAR_MIPMAP_LINEAR"


class SelectionRange(NoodleObject):
    """Range of rows to select in a table

    Attributes:
        key_from_inclusive (int): First row to select
        key_to_exclusive (int): Where to end selection, exclusive
    """
    key_from_inclusive: int
    key_to_exclusive: int


class Selection(NoodleObject):
    """Selection of rows in a table

    Attributes:
        name (str): Name of selection
        rows (List[int]): List of rows to select
        row_ranges (List[SelectionRange]): List of ranges of rows to select
    """
    name: str
    rows: Optional[List[int]] = None
    row_ranges: Optional[List[SelectionRange]] = None


class MethodArg(NoodleObject):
    """Argument for a method

    Attributes:
        name (str): Name of argument
        doc (str): Documentation for argument
        editor_hint (str): Hint for editor, refer to message spec for hint options
    """
    name: str
    doc: Optional[str] = None
    editor_hint: Optional[str] = None


class BoundingBox(NoodleObject):
    """Axis-aligned bounding box

    Attributes:
        min (Vec3): Minimum point of bounding box
        max (Vec3): Maximum point of bounding box
    """
    min: Vec3
    max: Vec3


class TextRepresentation(NoodleObject):
    """Text representation for an entity

    Attributes:
        txt (str): Text to display
        font (str): Font to use
        height (Optional[float]): Height of text
        width (Optional[float]): Width of text
    """
    txt: str
    font: Optional[str] = "Arial"
    height: Optional[float] = .25
    width: Optional[float] = -1.0


class WebRepresentation(NoodleObject):
    """Web page with a given URL rendered as a plane

    Attributes:
        source (str): URL for entity
        height (Optional[float]): Height of plane
        width (Optional[float]): Width of plane
    """
    source: str
    height: Optional[float] = .5
    width: Optional[float] = .5


class InstanceSource(NoodleObject):
    """Source of instances for a geometry patch

    Attributes:
        view (BufferViewID): View of mat4
        stride (int): Stride for buffer, defaults to tightly packed
        bb (BoundingBox): Bounding box of instances
    """
    view: BufferViewID
    stride: Optional[int] = 0  # Default is tightly packed
    bb: Optional[BoundingBox] = None


class RenderRepresentation(NoodleObject):
    """Render representation for an entity

    Attributes:
        mesh (GeometryID): Mesh to render
        instances (Optional[InstanceSource]): Source of instances for mesh
    """
    mesh: GeometryID
    instances: Optional[InstanceSource] = None


class TextureRef(NoodleObject):
    """Reference to a texture

    Attributes:
        texture (TextureID): Texture to reference
        transform (Optional[Mat3]): Transform to apply to texture
        texture_coord_slot (Optional[int]): Texture coordinate slot to use
    """
    texture: TextureID
    transform: Optional[Mat3] = [1.0, 0.0, 0.0,
                                 0.0, 1.0, 0.0,
                                 0.0, 0.0, 1.0, ]
    texture_coord_slot: Optional[int] = 0.0


class PBRInfo(NoodleObject):
    """Physically based rendering information for a material

    Attributes:
        base_color (Optional[RGBA]): Base color of material
        base_color_texture (Optional[TextureRef]): Texture to use for base color
        metallic (Optional[float]): Metallic value of material
        roughness (Optional[float]): Roughness value of material
        metal_rough_texture (Optional[TextureRef]): Texture to use for metallic and roughness
    """
    base_color: Optional[RGBA] = [1.0, 1.0, 1.0, 1.0]
    base_color_texture: Optional[TextureRef] = None  # assume SRGB, no premult alpha

    metallic: Optional[float] = 1.0
    roughness: Optional[float] = 1.0
    metal_rough_texture: Optional[TextureRef] = None  # assume linear, ONLY RG used


class PointLight(NoodleObject):
    """Point light information for a light delegate

    Attributes:
        range (float): Range of light, -1 defaults to infinite
    """
    range: float = -1.0


class SpotLight(NoodleObject):
    """Spotlight information for a light delegate

    Attributes:
        range (float): Range of light, -1 defaults to infinite
        inner_cone_angle_rad (float): Inner cone angle of light
        outer_cone_angle_rad (float): Outer cone angle of light
    """
    range: float = -1.0
    inner_cone_angle_rad: float = 0.0
    outer_cone_angle_rad: float = pi / 4


class DirectionalLight(NoodleObject):
    """Directional light information for a light delegate

    Attributes:
        range (float): Range of light, -1 defaults to infinite
    """
    range: float = -1.0


class Attribute(NoodleObject):
    """Attribute for a geometry patch

    Each attribute is a view into a buffer that corresponds to a specific element of the mesh
    (e.g. position, normal, etc.). Attributes allow information for the vertices to be extracted from buffers

    Attributes:
        view (BufferViewID): View of the buffer storing the data
        semantic (AttributeSemantic): String describing the type of attribute
        channel (Optional[int]): Channel of attribute, if applicable
        offset (Optional[int]): Offset into buffer
        stride (Optional[int]): Distance, in bytes, between data for two vertices in the buffer
        format (Format): How many bytes per element, how to decode the bytes
        minimum_value (Optional[List[float]]): Minimum value for attribute data
        maximum_value (Optional[List[float]]): Maximum value for attribute data
        normalized (Optional[bool]): Whether to normalize the attribute data
    """
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
    """Index for a geometry patch

    The index is a view into a buffer that corresponds to the indices of the mesh. The index allows the mesh to
    connect vertices and render triangles, lines, or points.

    Attributes:
        view (BufferViewID): View of the buffer storing the data
        count (int): Number of indices
        offset (Optional[int]): Offset into buffer
        stride (Optional[int]): Distance, in bytes, between data for two elements in the buffer
        format (IndexFormat): How many bytes per element, how to decode the bytes
    """
    view: BufferViewID
    count: int
    offset: Optional[int] = 0
    stride: Optional[int] = 0
    format: IndexFormat


class GeometryPatch(NoodleObject):
    """Geometry patch for a mesh

    Principle object used in geometry delegates. A geometry patch combines vertex data from attributes and index data
    from indices.

    Attributes:
        attributes (List[Attribute]): List of attributes storing vertex data for the mesh
        vertex_count (int): Number of vertices in the mesh
        indices (Optional[Index]): Indices for the mesh
        type (PrimitiveType): Type of primitive to render
        material (MaterialID): Material to use for rendering
    """
    attributes: List[Attribute]
    vertex_count: int
    indices: Optional[Index] = None
    type: PrimitiveType
    material: MaterialID


class InvokeIDType(NoodleObject):
    """Context for invoking a signal

    Attributes:
        entity (Optional[EntityID]): Entity to invoke signal on
        table (Optional[TableID]): Table to invoke signal on
        plot (Optional[PlotID]): Plot to invoke signal on
    """
    entity: Optional[EntityID] = None
    table: Optional[TableID] = None
    plot: Optional[PlotID] = None

    @model_validator(mode="after")
    def one_of_three(cls, model):
        """Ensure only one of the three attributes is set"""
        selected = bool(model.entity) + bool(model.table) + bool(model.plot)
        if selected != 1:
            raise ValueError("Must select exactly one of entity, table, or plot")
        return model


class TableColumnInfo(NoodleObject):
    """Information about a column in a table

    Attributes:
        name (str): Name of column
        type (ColumnType): Type data in the column
    """
    name: str
    type: ColumnType


class TableInitData(NoodleObject):
    """Init data to create a table

    Attributes:
        columns (List[TableColumnInfo]): List of column information
        keys (List[int]): List of column indices that are keys
        data (List[List[Any]]): List of rows of data
        selections (Optional[List[Selection]]): List of selections to apply to table
    """
    columns: List[TableColumnInfo]
    keys: List[int]
    data: List[List[Any]]  # Originally tried union, but currently order is used to coerce by pydantic
    selections: Optional[List[Selection]] = None

    # too much overhead? - strict mode
    @model_validator(mode="after")
    def types_match(cls, model):
        for row in model.data:
            for col, i in zip(model.columns, range(len(row))):
                text_mismatch = isinstance(row[i], str) and col.type != "TEXT"
                real_mismatch = isinstance(row[i], float) and col.type != "REAL"
                int_mismatch = isinstance(row[i], int) and col.type != "INTEGER"
                if text_mismatch or real_mismatch or int_mismatch:
                    raise ValueError(f"Column Info doesn't match type in data: {col, row[i]}")
        return model


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
    arg_doc: List[MethodArg] = []


class Entity(Delegate):
    """A generic container

    Can reference other entities, geometry, plots, and lights. It can be rendered, if it has a render rep.
    It may have associated methods and signals. The transform is relative to the parent entity. In other contexts
    it may be called a node.

    Attributes:
        id: ID for the entity
        name: Name of the entity
        parent: Parent entity
        transform: Local transform for the entity, ie. positional information
        text_rep: Text representation for the entity
        web_rep: Web representation for the entity
        render_rep: Render representation for the entity, points to geometry and instances
        lights: List of lights attached to the entity
        tables: List of tables attached to the entity
        plots: List of plots attached to the entity
        tags: List of tags for the entity
        methods_list: List of methods attached to the entity
        signals_list: List of signals attached to the entity
        influence: Bounding box for the entity
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

    @model_validator(mode="after")
    def one_of(cls, model):
        if bool(model.simple_plot) != bool(model.url_plot):
            return model
        else:
            raise ValueError("One plot type must be specified")


class Buffer(Delegate):
    """A buffer of bytes containing data for an image or a mesh.

    Bytes can be stored directly in the buffer with inline_bytes, or they can be stored in a URI with uri_bytes.
    The server should create a separate server to host the bytes, and there is support for this in the ByteServer
    class. To obtain these bytes, clients would have to make an HTTP request to the URI.

    A buffer could store a single attribute, or it could store multiple attributes interleaved together. This is
    where buffer views specify how to interpret the buffer.

    Attributes:
        id: ID for the buffer
        name: Name of the buffer
        size: Size of the buffer in bytes
        inline_bytes: Bytes of the buffer
        uri_bytes: URI for the bytes
    """
    id: BufferID
    name: Optional[str] = None
    size: int

    inline_bytes: Optional[bytes] = None
    uri_bytes: Optional[str] = None

    @model_validator(mode="after")
    def one_of(cls, model):
        if bool(model.inline_bytes) != bool(model.uri_bytes):
            return model
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

    The material is a collection of textures and factors that are used to render the mesh.

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

    Like a buffer, an image can be stored in a URI to reduce the size of messages. To obtain the bytes, you would
    have to make an HTTP request to the URI.

    Attributes:
        id: ID for the image
        name: Name of the image
        buffer_source: Buffer that the image is stored in
        uri_source: URI for the bytes if they are hosted externally
    """
    id: ImageID
    name: Optional[str] = None

    buffer_source: Optional[BufferID] = None
    uri_source: Optional[str] = None

    @model_validator(mode="after")
    def one_of(cls, model):
        if bool(model.buffer_source) != bool(model.uri_source):
            return model
        else:
            raise ValueError("One plot type must be specified")


class Texture(Delegate):
    """A texture, can be used for a material

    This is like a wrapping paper that is applied to a mesh. The image specifies the pattern, and
    the sampler specifies which part of the image should be applied to each part of the mesh.

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

    A sampler specifies how to take portions of an image and apply them to a mesh.

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

    For these purposes, a light is just a couple of properties like color, intensity, and light type. The entity
    that stores the light will dictate position and direction with its transform. The client application is then
    responsible for using this information to render the light. The light is either a point light, a spotlight, or
    a directional light.

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

    point: Optional[PointLight] = None
    spot: Optional[SpotLight] = None
    directional: Optional[DirectionalLight] = None

    @model_validator(mode="after")
    def one_of(cls, model):
        num_selected = bool(model.point) + bool(model.spot) + bool(model.directional)
        if num_selected > 1:
            raise ValueError("Only one light type can be selected")
        elif num_selected == 0:
            raise ValueError("No light type selected")
        else:
            return model


class Geometry(Delegate):
    """Represents geometry in the scene and can be used for meshes

    This is more of a collection of patches, but each patch will contain the geometry information to render a mesh.
    The patch references buffer views and buffers for each attribute, and a material to use for rendering. Instances
    are stored in a separate buffer that is referenced at the entity level.

    Attributes:
        id: ID for the geometry
        name: Name of the geometry
        patches: Patches that make up the geometry
    """
    id: GeometryID
    name: Optional[str] = None
    patches: List[GeometryPatch]


class Table(Delegate):
    """Data table

    Note that this delegate doesn't store any actual data. Delegates are meant to subclass and add functionality to
    this class. For the client to receive the actual data, they must subscribe to the table. The client will have
    access to certain injected methods that allow them to insert, update, delete, and clear the table. This class
    provides some abstract methods that can be overridden to handle these events.

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


class Document(Delegate):
    """Represents the scope of the whole session

    Attributes:
        name (str): name will be "Document"
        methods_list (list[MethodID]): list of methods available on the document
        signals_list (list[SignalID]): list of signals available on the document
    """

    name: Optional[str] = "Document"

    methods_list: List[MethodID] = []  # Server usually sends as an update
    signals_list: List[SignalID] = []


""" ====================== Communication Objects ====================== """


class Invoke(NoodleObject):
    id: SignalID
    context: Optional[InvokeIDType] = None  # if empty - document
    signal_data: List[Any]


class MethodException(Exception):
    """Custom exception specifically for methods defined on the server

    User defined methods injected on the server should raise this exception, and it will be sent
    to clients in a method reply message. Exception codes are defined in the table below.

    | Code   | Message            | Description                                                                                           |
    | ------ | ------------------ | ----------------------------------------------------------------------------------------------------- |
    | -32700 | Parse Error        | Given invocation object is malformed and failed to be validated                                       |
    | -32600 | Invalid Request    | Given invocation object does not fulfill required semantics                                           |
    | -32601 | Method Not Found   | Given invocation object tries to call a method that does not exist                                    |
    | -32602 | Invalid Parameters | Given invocation tries to call a method with invalid parameters                                       |
    | -32603 | Internal Error     | The invocation fulfills all requirements, but an internal error prevents the server from executing it |

    Attributes:
        code (int): Code for the exception
        message (Optional[message]): Message for the exception
        data (Optional[data]): Data for the exception
    """
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
    """User input object for setting starting components on server

    Attributes:
        type (Type[Delegate]): Type of component
        component_attrs (dict): Attributes for component
        method (Callable): Optional method to call on component
        document (bool): Whether method is attached to and can be called on document
    """

    def __init__(self, kind, component_attrs: Dict[str, Any], method: Optional[Callable] = None, document: bool = False):
        self.type = kind
        self.component_attrs = component_attrs
        self.method = method
        self.document = document


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
