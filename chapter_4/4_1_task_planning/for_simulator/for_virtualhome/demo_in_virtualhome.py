import sys
from simulation.unity_simulator import comm_unity

YOUR_FILE_NAME = "你的仿真器路径\\unity_simulator\\VirtualHome.exe"
port= "8080"

comm = comm_unity.UnityCommunication(
    file_name=YOUR_FILE_NAME,
    port=port,
    timeout_wait= 60
)

env_id = 0 # env_id ranges from 0 to 6
comm.fast_reset(env_id)

# Check the number of cameras
s, cam_count = comm.camera_count()
s, images = comm.camera_image([0, cam_count-1])

# Add a camera at the specified rotation and position
comm.add_camera(position=[-3, 2, -5], rotation=[10, 15, 0])

# # View camera from different modes
modes = ['normal'] 
images = []
for mode in modes:
    s, im = comm.camera_image([cam_count], mode=mode)
    images.append(im[0])

from PIL import Image 
import numpy as np
img_data = im[0]
img_array = np.array(Image.fromarray(img_data))
# Reset the environment
comm.reset(0)
comm.add_camera(position=[4, 2, -3], rotation=[10, 15, 0])
import json
# Get graph


# # print(json.dumps(graph, indent=4))
# # Get the fridge node

# ======================================================
# Reset the environment


# # Open it
#fridge_node['states'] = ['OPEN']

# # create a new node
new_node = {
    'id': 1000,
    'class_name': 'apple',
    'states': []
}
comm.add_character('Chars/Female2')
# 0.11 1.717 -1.731 24 -10
s, cam_count = comm.camera_count()
comm.add_character_camera(position=[0.11, 1.717, -0.8], rotation=[24, -10, 0], name='new_camera')
comm.activate_physics(gravity=-10)
s, graph = comm.environment_graph()
with open("tmp.json",'w', encoding='utf-8') as f:
    json.dump(graph,f,indent=4,ensure_ascii=False)
# # Add an edge


# script1 = [
#     '<char0> [find] <salmon> ({})'.format(salmon_id),
#     #'<char0> [find] <salmon> ({})'.format(apple_id),
#     '<char0> [grab] <salmon> ({})'.format(salmon_id),
#     '<char0> [walk] <fridge> ({})'.format(fridge_id),
#     '<char0> [drop] <salmon> ({})'.format(salmon_id),
#     # '<char0> [turnto] <fridge> ({})'.format(fridge_id),
#    #'<char0> [open] <fridge> ({})'.format(fridge_id),
#     # '<char0> [walk] <fridge> ({})'.format(fridge_id),
#     # '<char0> [find] <salmon> ({})'.format(salmon_id),
#     # '<char0> [grab] <salmon> ({})'.format(salmon_id),
#     # '<char0> [walk] <fridge> ({})'.format(fridge_id),
#     # '<char0> [open] <fridge> ({})'.format(fridge_id),
#     # '<char0> [putin] <salmon> ({}) <fridge> ({})'.format(salmon_id,fridge_id),   
#     # '<char0> [close] <fridge> ({})'.format(fridge_id),
#     #'<char0> [open] <microwave> ({})'.format(microwave_id),
#     #'<char0> [putin] <apple> ({}) <fridge> ({})'.format(apple_id, fridge_id),
#     #'<char0> [close] <microwave> ({})'.format(microwave_id),
#     #'<char0> [walk] <salmon> ({})'.format(new_id)
# ]

script2 = [
                "<char0> [WALK] <kitchen> (204)",
                "<char0> [WALK] <fridge> (304)",
                "<char0> [WALK] <cereal> (333)",
                "<char0> [GRAB] <cereal> (333)",
                "<char0> [WALK] <fridge> (304)",
                "<char0> [OPEN] <fridge> (304)",
                "<char0> [PUTIN] <cereal> (333) <fridge> (304)"
]
# print(salmon_node)
# script = []
# for id in floor_ids:
#     print(id)
#     script.append('<char0> [walk] <floor> ({})'.format(id))
#     comm.render_script(script, recording=True, frame_rate=10)

# script = [
#     '<char0> [find] <microwave> ({})'.format(microwave_id),
#     '<char0> [walk] <microwave> ({})'.format(microwave_id),
#     '<char0> [grab] <salmon> ({})'.format(salmon_id),
#     '<char0> [walk] <fridge> ({})'.format(fridge_id),
#     #'<char0> [open] <microwave> ({})'.format(microwave_id),
#     '<char0> [put] <salmon> ({}) <floor> ({})'.format(salmon_id, 208),
#     #'<char0> [close] <microwave> ({})'.format(microwave_id),
# ]
graphs = []
s1,graph1 = comm.environment_graph()
graphs.append(graph1)
s,message=comm.render_script(script2,recording=True,camera_mode=['FIRST_PERSON'],output_folder='E:\\project\\virtualhome\\virtualhome\\output5',find_solution=True,frame_rate=10)
print(message)
