import os
import uuid
import random

import mesa
# from mesa.time import RandomActivation
import numpy as np
from shapely.geometry import Point
import geopandas as gpd

import matplotlib as mpl
import matplotlib.pyplot as plt

import mesa_geo as mg

from loguru import logger
from building_evacuation.space import Building


# --------------------- PeopleAgent Class (Corrected Version) ---------------------
class PeopleAgent(mg.GeoAgent):
    """
    An agent that represents a person in the evacuation simulation.
    Agents move based on elevation and people level within the raster grid.
    """

    def __init__(self, unique_id, level, model, pos):
        super().__init__(
            unique_id,
            model,
            geometry=None,
            crs=model.space.crs,
        )
        self.pos = pos  # Initial position of the agent
        self.level = level  # Level of the agent (1 or 2)
        self.is_at_boundary = False

    @property
    def pos(self):
        return self._pos

    @property
    def indices(self):
        return self._indices

    @pos.setter
    def pos(self, pos):
        """
        Sets the agent's position and correctly calculates raster indices.
        This uses the original, correct formula for index conversion.
        """
        self._pos = pos
        if pos is not None:
            x, y = self.pos
            row_idx = self.model.space.raster_layer.height - y - 1
            col_idx = x
            self._indices = row_idx, col_idx
            # --- 结束修正 ---

            # The rest of the logic remains the same
            self.geometry = Point(
                # Note: rasterio transform uses (col, row) order for indices
                self.model.space.raster_layer.transform * (col_idx, row_idx)
            )
        else:
            self.geometry = None

    def step(self):
        """
        Agent's behavior in each step.
        1. Check if current position is an exit. If so, exit the simulation.
        2. Find the neighboring cell with the lowest cost (elevation + congestion).
        3. If a better cell is found, move there.
        """
        # Get the cell at the agent's current position
        # Note: raster_layer access is via (x, y) coordinates
        current_cell = self.model.space.raster_layer[self.pos[0]][self.pos[1]]

        # --- FIX FOR AGENT GRIDLOCK: Check for exit at CURRENT position first ---
        if self.level == 1 and current_cell.l1_elevation == 0:
            self.model.space.remove_people(self)
            self.model.schedule.remove(self)
            self.model.people_amount -= 1
            return  # Agent is removed, stop further actions

        if self.level == 2 and current_cell.l2_elevation == 0: #优先检查当前位置，如果已经为0，即可下楼
            # This is a stairwell leading down. Agent moves to level 1.
            # The agent will move on the next step from its new level 1 position.
            old_pos = self.pos
            self.model.space.remove_people(self)  # Remove from level 2 count
            self.level = 1
            self.pos = old_pos  # Position doesn't change yet
            self.model.space.add_people(self)  # Add to level 1 count
            return  # Let agent move on level 1 in the next step

        # --- Standard Movement Logic ---
        if self.level == 1:
            neighbors = self.model.space.raster_layer.get_neighboring_cells(
                pos=self.pos, moore=True, include_center=True
            )
            # Find the best neighboring cell to move to
            lowest_cost_cell = min(
                neighbors,
                key=lambda cell: cell.l1_elevation + cell.l1_people_level,
            )

            if lowest_cost_cell.pos != self.pos:
                self.model.space.move_people(self, lowest_cost_cell.pos)

        else:  # level == 2
            neighbors = self.model.space.raster_layer.get_neighboring_cells(
                pos=self.pos, moore=True, include_center=True
            )
            # Find the best neighboring cell to move to
            lowest_cost_cell = min(
                neighbors,
                key=lambda cell: cell.l2_elevation + cell.l2_people_level,
            )

            if lowest_cost_cell.pos != self.pos:
                self.model.space.move_people(self, lowest_cost_cell.pos)



# --------------------- BuildingEvacuation Model (Final Version) ---------------------
class BuildingEvacuation(mesa.Model):
    """
    The core evacuation simulation model. Agents (people) move in a grid based on elevation
    and people levels. This model includes data collection, simulation steps, and initialization.
    """

    def __init__(self, people_amount, people_level, export_data, num_steps, max_steps, running):
        """
         Initialize the evacuation model.
        """
        super().__init__()
        self.people_amount = people_amount
        self.initial_people_amount = people_amount
        self.export_data = export_data
        self.max_steps = max_steps
        self.running = running
        # self.num_steps = num_steps # This is now handled by schedule.steps, so it can be removed

        self.space = Building(crs="epsg:4326", people_level=people_level)
        self.schedule = mesa.time.RandomActivation(self)

        logger.info("Loading Wilkinson data")
        self.space.set_will_building_layer(
            "data/processed_data/will_floor/path/will_f1_path.asc",
            "data/processed_data/will_floor/path/will_f2_path.asc",
            crs="epsg:4326")

        self.initialize_people_two_floor(people_amount)
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Total People": lambda m: m.people_amount,
                "Level 1 People": lambda m: sum(1 for a in m.schedule.agents if a.level == 1),
                "Level 2 People": lambda m: sum(1 for a in m.schedule.agents if a.level == 2),
                "step": lambda m: m.schedule.steps,
                "scenario": lambda m: m.initial_people_amount,
            }
        )
        self.datacollector.collect(self)

    def initialize_people_two_floor(self, num_people):
        """
        Initialize people agents on both floors by first identifying valid spawn points.
        """
        logger.info(f"Initializing {num_people} people in two floors")
        valid_coords_l1 = []
        valid_coords_l2 = []
        for x in range(self.space.raster_layer.width):
            for y in range(self.space.raster_layer.height):
                if self.space.raster_layer.cells[x][y].l1_elevation != 99999:
                    valid_coords_l1.append((x, y))
                if self.space.raster_layer.cells[x][y].l2_elevation != 99999:
                    valid_coords_l2.append((x, y))

        if not valid_coords_l1 and not valid_coords_l2:
            raise ValueError("Both floors have no valid locations to place agents.")

        count = 0
        while count < num_people:
            # define starting floor of agent
            if random.random() < 0.5:
                if not valid_coords_l1: continue
                pos, level = random.choice(valid_coords_l1), 1
            else:
                if not valid_coords_l2: continue
                pos, level = random.choice(valid_coords_l2), 2

            people = PeopleAgent(uuid.uuid4().int, model=self, pos=pos, level=level)
            self.space.add_people(people)
            self.schedule.add(people)
            count += 1

        l1_current_people_level = self.space.raster_layer.get_raster("l1_people_level")
        l2_current_people_level = self.space.raster_layer.get_raster("l2_people_level")
        if l1_current_people_level.max() > 0:
            self.space.raster_layer.apply_raster(
                l1_current_people_level / l1_current_people_level.max(), "l1_people_level_normalized")
        if l2_current_people_level.max() > 0:
            self.space.raster_layer.apply_raster(
                l2_current_people_level / l2_current_people_level.max(), "l2_people_level_normalized")

    def get_agents_as_GeoDataFrame(self, agent_cls=PeopleAgent) -> gpd.GeoDataFrame:
        """
        Returns the agents in the simulation as a GeoDataFrame.
        Handles the case where there are no agents left.
        """
        if not self.schedule.agents:
            return gpd.GeoDataFrame([], columns=["unique_id", "_pos", "geometry", "level"],
                                    crs=self.space.crs).set_index("unique_id")

        agents_list = []
        for agent in self.schedule.agents:
            if isinstance(agent, agent_cls):
                agent_dict = {
                    attr: value for attr, value in vars(agent).items()
                    if attr not in {"model", "pos", "_crs"}
                }
                if 'unique_id' not in agent_dict: agent_dict['unique_id'] = agent.unique_id
                agents_list.append(agent_dict)

        agents_gdf = gpd.GeoDataFrame.from_records(agents_list, index="unique_id")
        agents_gdf.set_geometry("geometry", inplace=True)
        agents_gdf.crs = self.space.crs
        return agents_gdf

    def step(self):
        """
        Advance the model by one step.
        """
        self.schedule.step()
        self.datacollector.collect(self)

        logger.info(f"Step {self.schedule.steps} | People Remaining: {self.people_amount}")

        # 检查停止条件
        if self.people_amount == 0 or self.schedule.steps >= self.max_steps:
            logger.info("Simulation stopping condition met.")
            self.running = False
