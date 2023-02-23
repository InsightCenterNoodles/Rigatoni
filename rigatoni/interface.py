from noodle_objects import *

# Creation Wrappers for easier component creation
def create_method(self, name: str,
                  arg_doc: list[MethodArg],
                  doc: Optional[str] = None,
                  return_doc: Optional[str] = None):
    self.create_component(Method, name=name, doc=doc,
                          return_doc=return_doc, arg_doc=arg_doc)

def create_signal(self, name: str,
                  doc: Optional[str] = None,
                  arg_doc: list[MethodArg] = None):
    self.create_component(Signal, name=name, doc=doc, arg_doc=arg_doc)


def create_entity(self, name: Optional[str],
                  parent: Optional[EntityID] = None,
                  transform: Optional[Mat4] = None,
                  text_rep: Optional[TextRepresentation] = None,
                  web_rep: Optional[WebRepresentation] = None,
                  render_rep: Optional[RenderRepresentation] = None,
                  lights: Optional[list[LightID]] = None,
                  tables: Optional[list[TableID]] = None,
                  plots: Optional[list[PlotID]] = None,
                  tags: Optional[list[str]] = None,
                  methods_list: Optional[list[MethodID]] = None,
                  signals_list: Optional[list[SignalID]] = None,
                  influence: Optional[BoundingBox] = None):

    self.create_component(Method, name=name, parent=parent, transform=transform, text_rep=text_rep,
                          web_rep=web_rep, render_rep=render_rep, lights=lights, tables=tables, plots=plots,
                          tags=tags, methods_list=methods_list, signals_list=signals_list, influence=influence)

def create_plot(self, name: Optional[str] = None,
                table: Optional[TableID] = None,
                simple_plot: Optional[str] = None,
                url_plot: Optional[str] = None,
                methods_list: Optional[list[MethodID]] = None,
                signals_list: Optional[list[SignalID]] = None):

    self.create_component(Signal, name=name, table=table, simple_plot=simple_plot, url_plot=url_plot,
                          methods_list=methods_list, signals_list=signals_list)

def create_buffer(self, name: Optional[str] = None,
                  size: int = None,
                  inline_bytes: bytes = None,
                  uri_bytes: str = None):
    self.create_component(Buffer, name=name, size=size, inline_bytes=inline_bytes, uri_bytes=uri_bytes)

def create_bufferview(self,
                    source_buffer: BufferID,
                    offset: int,
                    length: int,
                    name: Optional[str] = None,
                    type: Literal["UNK", "GEOMETRY", "IMAGE"] = "UNK"):
    self.create_component(BufferView, name=name, source_buffer=source_buffer,
                          offset=offset, length = length, type=type)

def create_material(self, name: Optional[str] = None,
                    pbr_info: Optional[PBRInfo] = PBRInfo(),
                    normal_texture: Optional[TextureRef] = None,
                    occlusion_texture: Optional[TextureRef] = None,
                    occlusion_texture_factor: Optional[float] = 1.0,
                    emissive_texture: Optional[TextureRef] = None,
                    emissive_factor: Optional[Vec3] = (1.0, 1.0, 1.0),
                    use_alpha: Optional[bool] = False,
                    alpha_cutoff: Optional[float] = .5,
                    double_sided: Optional[bool] = False):
    self.create_component(Material, name=name, pbr_info=pbr_info, normal_texture=normal_texture,
                          occlusion_texture=occlusion_texture, occlusion_texture_factor=occlusion_texture_factor,
                          emissive_texture=emissive_texture, emissive_factor=emissive_factor,
                          use_alpha=use_alpha, alpha_cutoff=alpha_cutoff, double_sided=double_sided)


def create_image(self, name: Optional[str] = None,
                 buffer_source: BufferID = None,
                 uri_source: str = None):
    self.create_component(Image, name=name, buffer_source=buffer_source, uri_source=uri_source)

def create_texture(self, image: ImageID,
                   name: Optional[str] = None,
                   sampler: Optional[SamplerID] = None):
    self.create_component(Texture, name=name, image=image, sampler=sampler)

def create_sampler(self, name: Optional[str] = None,
                   mag_filter: Optional[Literal["NEAREST", "LINEAR"]] = "LINEAR",
                   min_filter: Optional[Literal["NEAREST", "LINEAR", "LINEAR_MIPMAP_LINEAR"]] = "LINEAR_MIPMAP_LINEAR",
                   wrap_s: Optional[SamplerMode] = "REPEAT",
                   wrap_t: Optional[SamplerMode] = "REPEAT"):
    self.create_component(Sampler, name=name, mag_filter=mag_filter, min_filter=min_filter,
                          wrap_s=wrap_s, wrap_t=wrap_t)

def create_light(self, name: Optional[str] = None,
                 color: Optional[RGB] = (1.0, 1.0, 1.0),
                 intensity: Optional[float] = 1.0,
                 point: PointLight = None,
                 spot: SpotLight = None,
                 directional: DirectionalLight = None):
    self.create_component(Light, name=name, color=color, intensity=intensity,
                          point=point, spot=spot, directional=directional)

def create_geometry(self, patches: list[GeometryPatch], name: Optional[str] = None):
    self.create_component(name=name, patches=patches)

def create_table(self, name: Optional[str] = None,
                 meta: Optional[str] = None,
                 methods_list: Optional[list[MethodID]] = None,
                 signals_list: Optional[list[SignalID]] = None):
    self.create_component(Table, name=name, meta=meta, methods_list=methods_list, signals_list=signals_list)



