# original env -  zhangbo , but deleted now
from loguru import logger
from building_evacuation.model import BuildingEvacuation
from building_evacuation.tools import export_poeple_amount_time, create_3d_animation , export_snapshots

PEOPLE_AMOUNT = 200
MAX_STEPS = 120

# fps and steps per frame
STEPS_PER_FRAME = 1
FPS = 10

if __name__ == "__main__":
    logger.info(f"Initializing model with {PEOPLE_AMOUNT} people for {MAX_STEPS} steps...")

    model = BuildingEvacuation(
        people_amount=PEOPLE_AMOUNT,
        people_level=5,
        export_data=True,
        num_steps=0,
        max_steps=MAX_STEPS,
        running=True
    )

    # create_3d_animation(
    #     model=model,
    #     output_filename=f"simulation_results/evacuation_3D_{PEOPLE_AMOUNT}p.gif",
    #     max_steps=MAX_STEPS,
    #     steps_per_frame=STEPS_PER_FRAME,
    #     fps=FPS,
    #     camera_rotation_speed=0
    # )

    # logger.info(f"Exporting simulation data to CSV...")
    # # plot the line chart showing number of each floors
    # export_poeple_amount_time(model, PEOPLE_AMOUNT)

    # logger.info("All tasks complete!")

    snapshot_points = [1, 30, 60, 90, 120] 

    # 函数会自动创建一个名为 "snapshots" 的子文件夹来存放图片
    export_snapshots(
        model=model,
        snapshot_steps=snapshot_points,
        output_dir=f"simulation_results/snapshots_{PEOPLE_AMOUNT}p"
    )

    # 上面的函数已经运行了模型，所以我们现在可以直接导出数据

    logger.info(f"Exporting population data to CSV and plot...")
    export_poeple_amount_time(model, PEOPLE_AMOUNT)

    logger.info("All tasks complete!")