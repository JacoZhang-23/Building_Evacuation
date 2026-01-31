from __future__ import annotations

import zipfile
import gzip

import mesa
import numpy as np
import rasterio as rio
import mesa_geo as mg

class BuildingCell(mg.Cell):
    '''
    Class:
    holds the info of each cell of the raster data related to building evacuation path
    '''
    l1_elevation: int | None
    l2_elevation: int | None
    #water_level: int | None
    #water_level_normalized: float | None

    def __init__(
        self,
        #model,
        pos: mesa.space.Coordinate | None = None,
        indices: mesa.space.Coordinate | None = None,
    ):
        super().__init__(pos, indices)
        self.path_value = None
        #self.people_level
        self.l1_people_level = None
        self.l2_people_level = None
        self.l1_people_level_normalized = None
        self.l2_people_level_normalized = None

    def step(self):
        pass

class Building(mg.GeoSpace):
    '''
    Class
    loaded the whole raster data and act as a complet envirnment of the model
    '''
    def __init__(self, crs, people_level):
        super().__init__(crs=crs)
        self.people_level = people_level


    def set_will_building_layer(self, building_zip_file_1, building_zip_file_2, crs):
        '''
        Load the building layer from ascii file.
        '''

        raster_layer = mg.RasterLayer.from_file(
            building_zip_file_1, cell_cls=BuildingCell, attr_name="l1_elevation"
        )

        with rio.open(building_zip_file_2,) as dataset:
            values = dataset.read()
        raster_layer.apply_raster(values, attr_name= "l2_elevation")

        print("In-Set_Building->setting the crs to", crs)
        raster_layer.crs = crs
        #相当于在一个栅格中，定义了两个属性的值，一楼和二楼
        #initialize the each cell's "people level" attribute
        raster_layer.apply_raster(
            data=np.zeros(shape=(1, raster_layer.height, raster_layer.width)),
            attr_name="l1_people_level",
        )

        raster_layer.apply_raster(
            data=np.zeros(shape=(1, raster_layer.height, raster_layer.width)),
            attr_name="l2_people_level",
        )

        super().add_layer(raster_layer)


    def set_building_layer(self, building_zip_file, crs):
        '''
        Load the building layer from ascii file.
        '''

        raster_layer = mg.RasterLayer.from_file(
            #f"/vsigzip/{building_zip_file}", cell_cls=BuildingCell, attr_name="elevation"
            building_zip_file, cell_cls=BuildingCell, attr_name="elevation"
        )

        print("In-Set_Building->setting the crs to", crs)
        raster_layer.crs = crs

        # initialize the each cell's "people level" attribute
        raster_layer.apply_raster(
            data=np.zeros(shape=(1, raster_layer.height, raster_layer.width)),
            attr_name="people_level",
        )
        super().add_layer(raster_layer)

    @property
    def raster_layer(self):
        return self.layers[0]

    def is_at_boundary(self, row_idx, col_idx):
        return (
            row_idx == 0
            or row_idx == self.raster_layer.height
            or col_idx == 0
            or col_idx == self.raster_layer.width
        )

    def move_people(self, people, new_pos):
        '''
        what does this do
        '''
        self.remove_people(people)
        people.pos = new_pos
        self.add_people(people)

    def add_people(self, people):
        '''
        what does this do
        '''
        x, y = people.pos
        row_ind, col_ind = people.indices
        # if self.is_at_boundary(row_ind, col_ind):
        #     people.is_at_boundary = True
        #     #self.outflow += 1 ## check this
        # else:
        if people.level == 1:
            self.raster_layer.cells[x][y].l1_people_level += self.people_level
        else:
            self.raster_layer.cells[x][y].l2_people_level += self.people_level
    def remove_people(self, people):
        '''
        what does this do
        '''
        x, y = people.pos
        if people.level == 1:
            self.raster_layer.cells[x][y].l1_people_level -= self.people_level
            #self.raster_layer.cells[x][y].l1_people_level += self.people_level
        else:
            self.raster_layer.cells[x][y].l2_people_level -= self.people_level
