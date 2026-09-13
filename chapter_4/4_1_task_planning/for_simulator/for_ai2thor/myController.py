from ai2thor.controller import Controller  # Import base controller from AI2THOR
from typing import *  # Import type hints
import numpy as np  # For numerical operations
from pprint import pprint  # Pretty-print for debugging

class DoneException(Exception):
    # Custom exception to indicate task completion
    pass

def parse_action(action_object:str):
    # Parse action string into action name and object ID
    action_object_pair = action_object.split("-")
    if len(action_object_pair) > 1:
        next_action = action_object_pair[0]  # Extract action name
        object_id = action_object_pair[1]    # Extract object identifier
    else:
        next_action = action_object
        object_id = ""
    return next_action, object_id

class MyController(Controller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Call parent class constructor

    def getImg(self):
        # Get current frame from the environment
        return self.last_event.cv2img

    def execute(self, action_object:str):
        # Execute parsed action in the environment
        next_action, object = parse_action(action_object)
        step_dict, feed_back_msg = self._genAI2ThorAPI(next_action, object)
        event = super().step(**step_dict)  # Execute AI2THOR action
        print(event.metadata["lastActionSuccess"])
        
        # Handle execution failure feedback
        if 'false' in str(event.metadata["lastActionSuccess"]):
            print("Failure reason: ", event.metadata['errorMessage'])
            feed_back_msg += f" \nFailure reason: {event.metadata['errorMessage']}"
            
        pprint(step_dict)
        return event.cv2img, event, feed_back_msg
    
    def GotoObject(self, target_place:str):
        # Generate teleportation parameters to approach target object
        obj, feed_back_msg = self._findObject(target_place)
        obj = obj[0]
        position, rotation, horizon = self._getTeleportPose(obj)
        template = {
            "action": "Teleport",
            "position": position,
            "rotation": rotation,
            "horizon": horizon,
            "standing": True
        }
        return template, feed_back_msg

    def PickupObject(self, objectId:str, forceAction:bool=True, placeStationary:bool=True):
        # Generate parameters for object pickup action
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "PickupObject",
            "objectId": obj["objectId"],
            "forceAction": forceAction,
            "manualInteract": placeStationary
        }
        return template, feed_back_msg

    def PutObject(self, objectId:str, forceAction:bool=True, placeStationary:bool=True):
        # Generate parameters for object placement action
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "PutObject",
            "objectId": obj["objectId"],
            "forceAction": forceAction,
            "placeStationary": placeStationary
        }
        return template, feed_back_msg

    def OpenObject(self, objectId:str, openness:float=1):
        # Generate parameters to open objects (doors/cabinets)
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "OpenObject",
            "objectId": obj["objectId"],
            "forceAction": True,
            "openness": openness
        }
        return template, feed_back_msg

    def CloseObject(self, objectId:str, forceAction:bool=True):
        # Generate parameters to close objects
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "CloseObject",
            "objectId": obj["objectId"],
            "forceAction": forceAction,
        }
        return template, feed_back_msg

    def SliceObject(self, objectId:str, forceAction:bool=True):
        # Generate parameters for slicing objects (e.g., cutting food)
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "SliceObject",
            "objectId": obj["objectId"],
            "forceAction": forceAction,
        }
        return template, feed_back_msg

    def ToggleObjectOn(self, objectId:str, forceAction:bool=True):
        # Generate parameters to turn on electronic devices
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "ToggleObjectOn",
            "objectId": obj["objectId"],
            "forceAction": forceAction,
        }
        return template, feed_back_msg

    def ToggleObjectOff(self, objectId:str, forceAction:bool=True):
        # Generate parameters to turn off electronic devices
        obj, feed_back_msg = self._findObject(objectId)
        obj = obj[0]
        template = {
            "action": "ToggleObjectOff",
            "objectId": obj["objectId"],
            "forceAction": forceAction,
        }
        return template, feed_back_msg

    def _get_id_by_object_str(self, objtype:str):
        # Find object ID by object type string
        found = []
        for obj in self.last_event.metadata["objects"]:
            if objtype.lower() in obj["objectType"].lower():
                found.append(obj)
        if len(found) == 0:
            print(f"Object {objtype} Not Found")
            return ""
        return found[0]['objectId']
    
    def _genAI2ThorAPI(self, api_name:str, obj:str):
        # Dynamically generate AI2THOR API call based on action name
        api = getattr(self, api_name)
        return api(obj)

    def _findObject(self, objtype: str):
        # Find objects in the environment by type
        if "|" in objtype:
            objtype = objtype.split("|")[0]
        found = []
        for obj in self.last_event.metadata["objects"]:
            if objtype.lower() in obj["objectType"].lower():
                found.append(obj)
        feed_back_message = ""
        if len(found) == 0:
            feed_back_message = f"Object {objtype} Not Found"
            print(feed_back_message)
        found = sorted(found, key=lambda o: o["distance"])
        return found, feed_back_message

    def _getTeleportPose(self, obj):
        # Calculate optimal teleport position near target object
        poses = self.step(
            action="GetInteractablePoses",
            objectId=obj["objectId"],
            horizons=np.linspace(-30, 60, 30),
            standings=[True]
        ).metadata["actionReturn"]

        objpos = np.array([obj['position']["x"], obj['position']["y"], obj['position']["z"]])

        def distance(pos):
            # Calculate Euclidean distance to object
            pos = np.array([pos["x"], pos["y"], pos["z"]])
            return np.linalg.norm(objpos - pos)
            
        # Select closest valid position
        poses = sorted(poses, key=distance)[0]
        return {"x": poses["x"], "y": poses["y"], "z": poses["z"]}, poses["rotation"], poses["horizon"]

def get_all_objects_in_scene(event):
    # Extract unique object categories from environment
    l = len(event.metadata['objects'])
    all_objects = list(set([event.metadata['objects'][i]['name'].split("_")[0] for i in range(l)]))
    return all_objects

def get_prompt(
        instruction:str, 
        all_objects:List[str], 
        skill_set_description,
        skills,
        **kwargs
        ) -> str:
    # Generate natural language prompt for LLM planning
    prompt = f"""
You are a household robot that can interact with objects in a 3D environment, and you have just one hand.
You are given a task to complete:
###{instruction}
You are given a list of objects in the scene:
###{str(all_objects)}
The action you can use are:
###{str(skills)}
And here are their descriptions:
###{str(skill_set_description)}
Please only output the next one step (like "PickupObject-Potato" or "GotoObject-Apple") in the string format. 
    """

    # Add additional context if available
    if 'history_of_actions' in kwargs:
        prompt += f"""
        The whole history of actions you have planned: 
        ###{str(kwargs['history_of_actions'])}
        """
    if 'current_image' in kwargs:
        prompt += f"""
        Now you can see the image in front of you:
        """
    if 'few_shots' in kwargs:
        prompt += f"""
        Here are some examples:
        ###{str(kwargs['few_shots'])}
        """
    if 'feed_back_message' in kwargs:
        prompt += f"""
        Here is the feedback message of the last action:
        ###{kwargs['feed_back_message']}
        """
    return prompt

if __name__ == "__main__":
    # Test controller initialization
    p = MyController()
    p.reset("FloorPlan418")