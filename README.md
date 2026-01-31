# Building Evacuation Simulation Framework

## Overview
This framework outlines the building evacuation simulation system, which models human movement in a two-story building during emergency evacuation scenarios. The system uses agent-based modeling with geographic information systems (GIS) integration.

## Framework Components

### 1. Input Parameters

The simulation accepts the following input parameters:

#### Core Simulation Parameters
- **people_amount**: Total number of people in the simulation (Slider: 1-500)
- **people_level**: Cost factor for each person affecting movement decisions (Slider: 1-5)
- **export_data**: Flag to export simulation data after completion (Checkbox: True/False)
- **num_steps**: Total simulation steps to run (Slider: 0-1500)
- **max_steps**: Maximum steps before simulation terminates (Used in run_without_server.py: 120)

#### Building Environment Parameters
- **Building Structure**: Two-floor building with elevation data
  - Floor 1 elevation data (`will_f1_path.asc`)
  - Floor 2 elevation data (`will_f2_path.asc`)
- **Coordinate Reference System (CRS)**: EPSG:4326
- **People Density**: Dynamic tracking per cell for both floors

#### Agent Parameters
- **Agent Class**: `PeopleAgent` inheriting from `mg.GeoAgent`
- **Agent Properties**:
  - `unique_id`: Unique identifier
  - `level`: Current floor level (1 or 2)
  - `pos`: Current position (x, y coordinates)
  - `is_at_boundary`: Boundary status flag

### 2. Model

The core simulation model consists of several key components:

#### Model Classes
- **BuildingEvacuation**: Main model class inheriting from `mesa.Model`
- **PeopleAgent**: Individual agent class representing people
- **Building**: Geographic space class managing the building environment
- **BuildingCell**: Individual cell class for the raster grid

#### Model Structure
```
BuildingEvacuation (Main Model)
├── space: Building (Geographic Space)
│   └── raster_layer: RasterLayer with BuildingCell objects
│       ├── l1_elevation: Floor 1 elevation data
│       ├── l2_elevation: Floor 2 elevation data
│       ├── l1_people_level: Current people density on floor 1
│       ├── l2_people_level: Current people density on floor 2
│       └── l1_people_level_normalized: Normalized density for floor 1
│           └── l2_people_level_normalized: Normalized density for floor 2
├── schedule: RandomActivation scheduler
└── datacollector: Data collection module
```

#### Key Functions
- **Initialization**:
  - `____()`: Initialize model with parameters
  - `initialize_people_two_floor()`: Place agents on valid positions
  - `set_will_building_layer()`: Load building elevation data

- **Agent Behavior**:
  - `PeopleAgent.step()`: Individual agent movement logic
    - Check if current position is an exit
    - Find neighboring cell with lowest cost (elevation + congestion)
    - Move to optimal position if available

- **Space Management**:
  - `Building.move_people()`: Move agents between positions
  - `Building.add_people()`: Update people density when agents enter cells
  - `Building.remove_people()`: Update people density when agents leave cells

- **Simulation Control**:
  - `BuildingEvacuation.step()`: Advance simulation by one step
  - Stop conditions: All people evacuated or max steps reached

#### Movement Logic
1. **Floor 1 Agents**:
   - Move to neighboring cells with lowest `l1_elevation + l1_people_level`
   - Exit when reaching cells with `l1_elevation = 0`

2. **Floor 2 Agents**:
   - Move to neighboring cells with lowest `l2_elevation + l2_people_level`
   - Descend to floor 1 when reaching stairwells (`l2_elevation = 0`)
   - Continue movement on floor 1 after descent

### 3. Model Results Collection & Visualization

The system provides comprehensive data collection and visualization capabilities:

#### Data Collection
- **DataCollector**: Tracks model-level metrics
  - Total People remaining in building
  - Level 1 People count
  - Level 2 People count
  - Current simulation step
  - Scenario identifier (initial people amount)

- **Export Functions**:
  - `export_poeple_amount_time()`: Export population data to CSV
    - File: `simulation_results/evacuation_data_{N}p.csv`
    - Contains step-by-step population counts

#### Visualization Methods
1. **3D Animation**:
   - Function: `create_3d_animation()`
   - Output: `simulation_results/evacuation_3D_{N}p.gif`
   - Features:
     - Two floors rendered as surfaces
     - Agents shown as colored points (orange for floor 1, red for floor 2)
     - Camera rotation capability
     - Real-time population count display

2. **Population Curves**:
   - Function: `export_poeple_amount_time()`
   - Output: `simulation_results/evacuation_data_{N}p.png`
   - Features:
     - Three-line plot showing total, floor 1, and floor 2 populations
     - Time series data from simulation steps
     - Professional styling with grid and legend

3. **Server-Based Visualization** (Optional):
   - **MapModule**: Real-time 2D visualization using mesa-geo
     - Cell portrayal based on elevation and people density
     - Color coding: grayscale for empty paths, blue for people
   - **ChartModule**: Dynamic population chart
     - Real-time updates during simulation

#### Output Files
- **Data Files**:
  - CSV files with evacuation data
  - ASC files with spatial data at different steps

- **Visualization Files**:
  - GIF animations of 3D simulation
  - PNG plots of population curves
  - Real-time web-based visualization (when using server)

## Workflow Summary

1. **Initialization**: Set up model with parameters and load building data
2. **Simulation**: Agents move based on elevation and congestion
3. **Data Collection**: Track population metrics at each step
4. **Visualization**: Generate 3D animations and population plots
5. **Export**: Save results for further analysis

This framework provides a comprehensive approach to modeling and visualizing building evacuation scenarios, with flexible parameters and multiple output formats for different analysis needs.
