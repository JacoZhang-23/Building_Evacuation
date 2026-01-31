from typing import Tuple

import mesa

import mesa_geo as mg

from building_evacuation.space import BuildingCell
from building_evacuation.model import BuildingEvacuation


model_params = {
    "people_amount": mesa.visualization.Slider("Total number of people", 200, 1, 500, 1), # total number of people
    "people_level": mesa.visualization.Slider("people level", 5, 1, 5, 1), # cost of each people
    "export_data": mesa.visualization.Checkbox("export data after simulation", True),
    #"num_exits": mesa.visualization.Slider("Exits Number", 1, 1, 2, 1),
    "num_steps": mesa.visualization.Slider("Total Steps", 500, 0, 1500, 1)
}


def cell_portrayal(cell: BuildingCell) -> Tuple[float, float, float, float]:
    # if cell.water_level == 0:
    #     return cell.elevation, cell.elevation, cell.elevation, 1
    if cell.l1_elevation == 99999: # don't show boundary
        return 0,0,0,0
    elif cell.l1_people_level == 0: # if no people show evacuation path
        return cell.l1_elevation, cell.l1_elevation, cell.l1_elevation, 1
        # return (
        #     (1 - cell.elevation) * 74,
        #     (1 - cell.elevation) * 141,
        #     255,
        #     1,
        # )
    else: #show people
        return (74, 141, 255, 1)

map_module = mg.visualization.MapModule(#todo i donnot need map if the crs is not load properly
    portrayal_method=cell_portrayal,
    map_height=300,
    map_width=300,
    tiles=None
)

#dynamic chart
people_chart = mesa.visualization.ChartModule(
    [
        {"Label": "Total Amount of people", "Color": "Blue"},
        #{"Label": "Total Contained", "Color": "Blue"},
        #{"Label": "Total Outflow", "Color": "Orange"},
    ]
)

server = mesa.visualization.ModularServer(
    BuildingEvacuation, [map_module, people_chart], "Evacuation Model", model_params
)
