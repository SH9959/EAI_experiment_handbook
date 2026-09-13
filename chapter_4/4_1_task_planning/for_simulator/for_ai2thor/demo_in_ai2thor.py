import os
from pprint import pprint
import time
import cv2
import json
from http import HTTPStatus
import dashscope

from myController import MyController, get_all_objects_in_scene, get_prompt, parse_action

# User instruction
instruction = "place a cup with a knife in it on the kitchen counter space"
scene = 'FloorPlan10'

# Initialize the AI2THOR controller
controller = MyController()
# Reset the scene
event = controller.reset(scene)
# Get all objects in the scene
all_objects = get_all_objects_in_scene(event)
print(all_objects)
# Get the skill set and their simple descriptions
with open("./action.json", "r", encoding="utf-8") as f:
    skill_set_description = json.load(f)
# Initialize the history list
history = []
skills = [item['name'].lower() for item in skill_set_description]
prompt = get_prompt(instruction, all_objects, skill_set_description, skills)


class IllegalException(Exception):
    pass

# def task_is_not_finished(
#     instruction:str,
#     event
# ):
#     """Determine whether the current task is completed based on pre-set task completion conditions, here only a simple condition is set
#     """
#     if instruction == "place a cup with a knife in it on the kitchen counter space":
#     # Check if the last action is PutObject and if the object was successfully placed
#         print(event)
#         if event and event.metadata['lastAction'] == 'PutObject' and event.metadata['actionReturn']['placed']:
#             return False
#         return True
    


if __name__ == "__main__":

    """for task="place a cup with a knife in it on the kitchen counter space", plan as follows:

        "GotoObject-countertop",
        "PickupObject-ButterKnife",
        "TeleportObject-cup",
        "OpenObject-Cabinet",
        "PutObject-ButterKnife",
        "PickupObject-Cup",
        "CloseObject-Cabinet",
        "TeleportObject-countertop",
        "PutObject-Cup"
        
    """

    image = controller.getImg()
    img_path = "tmp_image.png"  
    cv2.imwrite(img_path, image)
    next_action_object = ""
    feed_back_message = ""

    while not 'done' in next_action_object.lower(): # task_is_not_finished(instruction,event):
        # Get the prompt
        prompt = get_prompt(
            instruction=instruction, 
            all_objects=all_objects, 
            skill_set_description=skill_set_description, 
            history_of_actions=history, 
            current_image=img_path, 
            skills=skills,
            feed_back_message=feed_back_message
        )
        print("-"*25,'prompt follow','-'*25)
        print(prompt)
        print("-"*25,'prompt above','-'*25)

        input("\033[1;97;43mPress Enter to continue >>>\033[0m")

        messages = [
            {
                "role": "system",
                "content": [
                    {"text": "You are a helpful assistant."}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"image": img_path},
                    {"text": prompt}
                ]
            }
        ]
        start_time_of_request = time.time()
        response = dashscope.MultiModalConversation.call(
            # If no environment variable is configured, please replace the following line with: api_key ="sk-xxx"
            api_key = os.getenv('DASHSCOPE_API_KEY'),
            model = 'qwen-vl-plus',
            messages = messages,
            temperature = 0.01,
            top_p = 0.01,
            top_k = 3,
            max_tokens = 32,
            seed=1234,
            stream = False,
        )
        print(f"Request time: {time.time() - start_time_of_request}s")
        # Check the response status
        if response.status_code == HTTPStatus.OK:
            # Extract the next action
            next_action_object = response.output.choices[0].message.content[0]["text"]

            print(f"Next step: \033[1;97;44m{next_action_object}\033[0m")

            # parse_action
            next_action,object_id = parse_action(next_action_object)
            print(f"next_action: {next_action}, object_id: {object_id}")

            if not next_action.lower() in skills:
                raise IllegalException(f"\033[1;97;43mVerify: \033[0mIllegal action: {next_action_object}")

            else:
                print(f"\033[1;97;43mVerify: \033[0mAction '{next_action_object}' is legal.")
                start_time_of_execute = time.time()
                img, event, feed_back_message = controller.execute(next_action_object)
                print(f"Execute time: {time.time() - start_time_of_execute}s")
                if event.metadata["lastActionSuccess"] == True:
                    history.append((next_action_object, "This action was executed successfully."))
                else:
                    history.append((next_action_object, f"This action was not executed successfully because of the following reason:{event.metadata['errorMessage']}"))

                cv2.imwrite(img_path, img)  
                print(f"Image saved to {img_path}")
        else:
            print('Failed to get a valid response from the model.')  
            print(f"Request failed with status code: {response.status_code}")
            # print(f"Response content: {response.content}")

    # Print the history
    print("History:")
    pprint(history)
