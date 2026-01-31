# Add this entire function to the end of your tool.py file

import matplotlib.colors as mcolors
from matplotlib import animation
from matplotlib.animation import PillowWriter
from tqdm import tqdm
from building_evacuation.model import BuildingEvacuation
import os
import glob
from loguru import logger

import numpy as np
import imageio
import matplotlib as mpl
import matplotlib.pyplot as plt

def create_3d_animation(
        model: BuildingEvacuation,
        output_filename="simulation.gif",
        max_steps=200,
        steps_per_frame=1,
        fps=15,
        camera_elevation=20,
        camera_initial_azimuth=60,
        camera_rotation_speed=0,
):
    """
    Generates a 3D animation with manual layering to solve rendering issues.
    """
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    scatter_l1, scatter_l2 = None, None

    def setup_plot():
        nonlocal scatter_l1, scatter_l2
        logger.info("Setting up static 3D plot (Manual Layering Mode)...")
        ax.clear()

        # ... Color normalization ...
        l1_data = model.space.raster_layer.get_raster("l1_elevation")
        l2_data = model.space.raster_layer.get_raster("l2_elevation")
        valid_data = np.concatenate([l1_data[l1_data != 99999], l2_data[l2_data != 99999]])
        vmin, vmax = (np.min(valid_data), np.max(valid_data)) if valid_data.size > 0 else (0, 1)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap('viridis')

        agent_gdf = model.get_agents_as_GeoDataFrame()
        agents_l1 = agent_gdf[agent_gdf.level == 1]
        agents_l2 = agent_gdf[agent_gdf.level == 2]

        # 1. floor painting
        ny, nx = 0, 0  # get shape later
        for level in [1]:
            floor_data_raw = model.space.raster_layer.get_raster(f"l{level}_elevation")[0, :, :]
            floor_data_flipped = np.flipud(floor_data_raw)
            mask = floor_data_flipped == 99999.0
            ny, nx = floor_data_flipped.shape
            x_grid, y_grid = np.meshgrid(np.arange(nx), np.arange(ny))
            z_grid = np.full_like(x_grid, float(level) - 0.05, dtype=float)
            face_colors = cmap(norm(floor_data_flipped))
            face_colors[mask] = (0, 0, 0, 0)
            ax.plot_surface(x_grid, y_grid, z_grid, rstride=1, cstride=1, facecolors=face_colors, linewidth=0,
                            antialiased=False, shade=False)

        # 2.L1 agent painting
        x1 = [p[0] for p in agents_l1._pos]
        y1 = [p[1] for p in agents_l1._pos]
        z1 = [lvl +0.25 for lvl in agents_l1.level]
        scatter_l1 = ax.scatter(x1, y1, z1, c='orange', s=30, ec='k', lw=0.5, depthshade=True)

        # 3.L2 floor painting
        for level in [2]:
            floor_data_raw = model.space.raster_layer.get_raster(f"l{level}_elevation")[0, :, :]
            floor_data_flipped = np.flipud(floor_data_raw)
            mask = floor_data_flipped == 99999.0
            ny, nx = floor_data_flipped.shape
            x_grid, y_grid = np.meshgrid(np.arange(nx), np.arange(ny))
            z_grid = np.full_like(x_grid, float(level) - 0.05, dtype=float)
            face_colors = cmap(norm(floor_data_flipped))
            face_colors[mask] = (0, 0, 0, 0)
            ax.plot_surface(x_grid, y_grid, z_grid, rstride=1, cstride=1, facecolors=face_colors, linewidth=0,
                            antialiased=False, shade=False)

        # 4. L2 agent painting
        x2 = [p[0] for p in agents_l2._pos]
        y2 = [p[1] for p in agents_l2._pos]
        z2 = [lvl +0.25 for lvl in agents_l2.level]
        scatter_l2 = ax.scatter(x2, y2, z2, c='red', s=30, ec='k', lw=0.5, depthshade=True)

        # ... Aesthetics ...
        # --- Aesthetics (with custom ticks) ---
        ax.set_box_aspect((nx, ny, (nx + ny) * 0.4))
        ax.set_zlim(0, 3)
        ax.set_zticks(np.arange(0, 3.0, 0.5))
        ax.set_yticks(np.arange(0, 151, 50))
        ax.set_xticks(np.arange(0, nx + 1, 50))
        ax.set_xlabel("X Coordinate", fontweight='bold')
        ax.set_ylabel("Y Coordinate", fontweight='bold')
        ax.set_zlabel("Floor Level", fontweight='bold')
        ax.set_facecolor('white')
        ax.grid(True, linestyle='--', alpha=0.6)

    def update(frame_index, pbar):
        nonlocal scatter_l1, scatter_l2
        for _ in range(steps_per_frame):
            if model.running: model.step()

        agent_gdf = model.get_agents_as_GeoDataFrame()
        agents_l1 = agent_gdf[agent_gdf.level == 1]
        agents_l2 = agent_gdf[agent_gdf.level == 2]

        if not agents_l1.empty:
            x1 = [p[0] for p in agents_l1._pos];
            y1 = [p[1] for p in agents_l1._pos];
            z1 = [lvl +0.25 for lvl in agents_l1.level]
            scatter_l1._offsets3d = (x1, y1, z1)
        else:
            scatter_l1._offsets3d = ([], [], [])

        # 更新二楼的点
        if not agents_l2.empty:
            x2 = [p[0] for p in agents_l2._pos];
            y2 = [p[1] for p in agents_l2._pos];
            z2 = [lvl + 0.25 for lvl in agents_l2.level]
            scatter_l2._offsets3d = (x2, y2, z2)
        else:
            scatter_l2._offsets3d = ([], [], [])

        # ... Update title and camera ...
        current_step = model.schedule.steps
        ax.set_title(f"Step: {current_step} | Agents Remaining: {model.people_amount}", fontsize=14)
        current_azim = camera_initial_azimuth + frame_index * camera_rotation_speed
        ax.view_init(elev=camera_elevation, azim=current_azim)

        pbar.update(1)
        return scatter_l1, scatter_l2

    # --- Main Animation Logic ---
    setup_plot()
    total_frames = max_steps // steps_per_frame

    logger.info(f"Generating animation with {total_frames} frames...")
    with tqdm(total=total_frames, desc="Animating frames") as pbar:
        ani = animation.FuncAnimation(
            fig, update, frames=total_frames, fargs=(pbar,),
            interval=1000 / fps, blit=True
        )

        logger.info(f"Saving animation to {output_filename}...")
        ani.save(output_filename, writer=PillowWriter(fps=fps), dpi=300)

    plt.close(fig)
    logger.info("Animation saved successfully.")


def export_poeple_amount_time(model: BuildingEvacuation, people_scenario_name) -> None:
    """
    Exports the population data to a CSV file and generates a plot
    with three curves: Total, Level 1, and Level 2 population over time.

    This is a standalone utility function.
    """

    directory_path = "simulation_results/"
    os.makedirs(directory_path, exist_ok=True)

    base_filename = f"evacuation_data_{people_scenario_name}p"
    csv_file_path = os.path.join(directory_path, f"{base_filename}.csv")
    plot_file_path = os.path.join(directory_path, f"{base_filename}.png")
    df = model.datacollector.get_model_vars_dataframe()

    required_cols = ['step', 'Total People', 'Level 1 People', 'Level 2 People']
    if not all(col in df.columns for col in required_cols):
        logger.error(f"Dataframe is missing required columns! Columns found: {df.columns.to_list()}")
        logger.error("Please ensure the model's DataCollector is configured correctly.")
        return

    logger.info(f"Exporting population data to {csv_file_path}")
    df.to_csv(csv_file_path, index=False)

    #3 line plot
    logger.info(f"Generating population curve plot and saving to {plot_file_path}")

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 7))

    #line plot
    ax.plot(df['step'], df['Total People'], color='black', linestyle='-', marker='o', markersize=4,
            label='Total Remaining')
    ax.plot(df['step'], df['Level 1 People'], color='dodgerblue', linestyle='--', marker='s', markersize=4,
            label='Level 1 Population')
    ax.plot(df['step'], df['Level 2 People'], color='red', linestyle=':', marker='^', markersize=4,
            label='Level 2 Population')

    #plot setting
    ax.set_title(f'Building Evacuation Over Time (Scenario: {people_scenario_name} People)', fontsize=16,
                 fontweight='bold')
    ax.set_xlabel('Simulation Step', fontsize=12)
    ax.set_ylabel('Number of People', fontsize=12)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0, top=model.initial_people_amount * 1.05)
    ax.legend(fontsize=10)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    fig.tight_layout()
    fig.savefig(plot_file_path, dpi=300)
    plt.close(fig)


    # 文件: tools.py
# 添加这个新函数，或者用它替换 create_snapshot_gif

# 需要引入的库
def export_snapshots(
        model: BuildingEvacuation,
        snapshot_steps: list,
        output_dir="simulation_results/snapshots",
        camera_elevation=20,
        camera_initial_azimuth=60,
):
    """
    Runs the model and saves PNG snapshots at specific, user-defined steps.
    """
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # 创建快照输出文件夹
    os.makedirs(output_dir, exist_ok=True)
    
    # --- 绘图函数 (只绘制并保存一帧) ---
    def draw_and_save_frame(step_number):
        logger.info(f"Exporting snapshot for step {step_number}...")
        ax.clear()

        agent_gdf = model.get_agents_as_GeoDataFrame()
        agents_l1 = agent_gdf[agent_gdf.level == 1]
        agents_l2 = agent_gdf[agent_gdf.level == 2]
        
        # ... (这里是完整的绘图逻辑，和你原来的setup_plot一样) ...
        l1_data = model.space.raster_layer.get_raster("l1_elevation")
        l2_data = model.space.raster_layer.get_raster("l2_elevation")
        valid_data = np.concatenate([l1_data[l1_data != 99999], l2_data[l2_data != 99999]])
        vmin, vmax = (np.min(valid_data), np.max(valid_data)) if valid_data.size > 0 else (0, 1)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap('viridis')
        ny, nx = model.space.raster_layer.height, model.space.raster_layer.width
        x_grid, y_grid = np.meshgrid(np.arange(nx), np.arange(ny))

        # 绘制楼层
        for level in [1, 2]:
            floor_data_raw = model.space.raster_layer.get_raster(f"l{level}_elevation")[0, :, :]
            floor_data_flipped = np.flipud(floor_data_raw)
            mask = floor_data_flipped == 99999.0
            z_grid = np.full_like(x_grid, float(level), dtype=float)
            face_colors = cmap(norm(floor_data_flipped))
            face_colors[mask] = (0, 0, 0, 0)
            ax.plot_surface(x_grid, y_grid, z_grid, rstride=1, cstride=1, facecolors=face_colors, linewidth=0, antialiased=False, shade=False)

        # 绘制Agents
        x1, y1, z1 = [p[0] for p in agents_l1._pos], [p[1] for p in agents_l1._pos], [lvl + 0.25 for lvl in agents_l1.level]
        ax.scatter(x1, y1, z1, c='orange', s=30, ec='k', lw=0.5, depthshade=True)
        x2, y2, z2 = [p[0] for p in agents_l2._pos], [p[1] for p in agents_l2._pos], [lvl + 0.25 for lvl in agents_l2.level]
        ax.scatter(x2, y2, z2, c='red', s=30, ec='k', lw=0.5, depthshade=True)

        # 设置美学和视角
        ax.set_box_aspect((nx, ny, (nx + ny) * 0.4))
        ax.set_zlim(0, 3); ax.set_zticks(np.arange(0, 3.5, 0.5))
        ax.set_yticks(np.arange(0, 151, 50)); ax.set_xticks(np.arange(0, nx + 1, 50))
        ax.set_xlabel("X Coordinate", fontweight='bold'); ax.set_ylabel("Y Coordinate", fontweight='bold'); ax.set_zlabel("Floor Level", fontweight='bold')
        ax.set_facecolor('white'); ax.grid(True, linestyle='--', alpha=0.6)
        ax.view_init(elev=camera_elevation, azim=camera_initial_azimuth)
        ax.set_title(f"Step: {step_number} | Agents Remaining: {model.people_amount}", fontsize=20)
        
        # --- 关键修改：直接保存到最终的输出文件夹 ---
        output_path = os.path.join(output_dir, f"snapshot_step_{step_number:04d}.png")
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved snapshot to {output_path}")

    # --- 主循环逻辑 ---
    max_step_needed = 0
    if snapshot_steps: # 检查列表是否为空
        max_step_needed = max(snapshot_steps)
    
    # 将0步加入快照点，以保存初始状态
    snapshot_points_with_initial = sorted(list(set([0] + snapshot_steps)))

    # 运行模型直到最后一个需要的快照步数
    with tqdm(total=max_step_needed, desc="Running simulation for snapshots") as pbar:
        # 首先绘制初始状态 (step 0)
        if 0 in snapshot_points_with_initial:
            draw_and_save_frame(0)

        while model.schedule.steps < max_step_needed and model.running:
            model.step()
            pbar.update(1)
            # 检查当前步数是否是需要的快照点
            if model.schedule.steps in snapshot_points_with_initial:
                draw_and_save_frame(model.schedule.steps)

    logger.info("Snapshot export process complete.")
    plt.close(fig)