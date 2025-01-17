'''
Authors: Chengxuyuan, Kk
'''

import numpy as np
import json
from dataclasses import dataclass
import enum
import networkx as nx
from typing import Any, MutableMapping, Set, Tuple

# # floorplan color map (Defined by @ys)
# floorplan_map = {
#   0: [255, 255, 255], # background
#   1: [192, 193, 224], # closet, purple
#   # 2: [192, 255, 255], # bathroom/washroom, light blue
#   2: [193, 254, 255], # bathroom/washroom, light blue
#   # 3: [224, 255, 192], # livingroom/kitchen/dining room, light green
#   3: [225, 255, 193], # livingroom/kitchen/dining room, light green
#   # 4: [255, 224, 128], # bedroom, yellow
#   4: [254, 224, 128], # bedroom, yellow
#   5: [255, 160, 96], # hall,orange
#   6: [255, 224, 224], # balcony, pink
#   7: [96, 179, 255], # garage, blue
#   8: [1, 255, 19],  # laundry room, green
#   9: [255, 60, 128], # window
#   10: [0, 0, 255], #door
#   11: [0, 0, 0]  # wall
# }

@enum.unique
class ROOMTYPE(enum.Enum):
  # TODO(kk): change per above floorplan_map
  BACKGROUND = 0
  CLOSET = 1
  BATHROOM = 2
  LIVINGROOM = 3
  BEDROOM = 4
  HALL = 5
  BALCONY = 6
  GARAGE = 7
  LAUNDRAY = 8
  WINDOW = 9
  DOOR = 10
  WALL = 11


@dataclass
class Room(object):
  """docstring for Room"""
  room_id: str
  area: int
  room_type: ROOMTYPE


@dataclass
class Link(object):
  """docstring for Room"""
  color: str
  distance: float
  source: str
  target: str


@dataclass
class Rooms(object):
  """docstring for Room"""
  _room_nodes: MutableMapping[str, Room] # id -> node
  _public_types: Set[ROOMTYPE]
  _private_types: Set[ROOMTYPE]
  _links: MutableMapping[Tuple[str, str], Link] # (id, id) -> node
  _graph: nx.Graph
  _all_pairs_shortest_path: Any
  _all_pairs_shortest_dist: np.array

  @classmethod
  def create_from_json(cls, path_room) -> "Rooms":
    with open(path_room, "r") as f:
      data_raw = json.load(f) 

    room_nodes = {}
    for room_raw in data_raw['nodes']:
      roomtype = ROOMTYPE(int(room_raw['id'].split('_')[0]))
      room = Room(room_raw['id'], int(room_raw['area']), roomtype)
      room_nodes.update({room_raw['id']: room})

    links = {}
    graph = nx.Graph()
    for link_raw in data_raw['links']:
      link = Link(link_raw['color'], link_raw['distance'], link_raw['source'], link_raw['target'])
      links.update({(link_raw['source'], link_raw['target']): link})
      links.update({(link_raw['target'], link_raw['source']): link})
      graph.add_edge(link_raw['source'], link_raw['target'], length=link_raw['distance'])

    all_pairs_shortest_path = dict(nx.all_pairs_shortest_path(graph))
    all_pairs_shortest_dist = {}
    for id_start, id_end_and_paths in all_pairs_shortest_path.items():
      id_end_and_dist = {}
      for id_end, path in id_end_and_paths.items():
        dist = 0.0
        for i in range(len(path)-1):
          dist += links[(path[i], path[i+1])].distance
        id_end_and_dist[id_end] = dist
      all_pairs_shortest_dist[id_start] = id_end_and_dist
    public_types = [ROOMTYPE.LIVINGROOM,ROOMTYPE.HALL]
    private_types = [ROOMTYPE.BATHROOM,ROOMTYPE.BEDROOM,ROOMTYPE.LAUNDRAY,ROOMTYPE.CLOSET]

    return Rooms(room_nodes, public_types, private_types, links, graph, all_pairs_shortest_path, all_pairs_shortest_dist)

  def get_shortest_distance(self):
    pass

  def get_total_area(self):
    return np.sum([r.area for r in self._room_nodes.values()])

  def get_public_area(self):
    return np.sum([r.area for r in self._room_nodes.values() if r.room_type in self._public_types])

  # Written by kk 4/16
  def get_area_inuse(self):
    area_garage = np.sum([r.area for r in self._room_nodes.values() if r.room_type == ROOMTYPE.GARAGE])
    area_closet = np.sum([r.area for r in self._room_nodes.values() if r.room_type == ROOMTYPE.CLOSET])
    return self.get_total_area() - area_closet - area_garage

  # Written by kk 4/16
  def get_public_ratio (self):
    return self.get_public_area() / self.get_total_area()

  def get_corridor_area(self):
    return np.sum([r.area for r in self._room_nodes.values() if r.room_type == ROOMTYPE.HALL])

  def get_corridor_ratio(self):
    return self.get_corridor_area() / (self.get_area_inuse() + 1e-6) # modified by kk 4/16

  def get_total_number_roomtype(self):
    # TODO: (Chengxuyuan) minor the number of room 0 BACKGROUND
    room_types = np.unique([r.room_type.value for r in self._room_nodes.values()])
    return len(room_types)-1 # Modified by kk 4/16

  def get_target_nearby_function(self, room_id_input):
    # TODO: (Chengxuyuan) minor the number of room 0 BACKGROUND
    if room_id_input not in self._room_nodes:
      raise ValueError(f"Invalide room_id_input: {room_id_input}")
    # Find all doors that connects to room_id.
    door_to_link_map = {l.target: l for l in self._links.values() if l.source == room_id_input}
    # Find neighbors that connect to `door_to_link_map`.
    neighbor_links_to_door = [l.source for l in self._links.values() if (l.target in door_to_link_map and l.source != room_id_input)]
    # Find neigbhor types
    room_types = np.unique([self._room_nodes[room_id].room_type.value for room_id in neighbor_links_to_door])
    return len(room_types)

  # Written by kk 4/16
  def get_function_ratio(self):
    # return self.get_target_nearby_function(3_1) / self.get_total_number_roomtype()
    return 2 / self.get_total_number_roomtype()

  def get_ave_connectivity_public(self, room_id_input):
    if room_id_input not in self._room_nodes:
      raise ValueError(f"Invalide room_id_input: {room_id_input}")
    total_distances = []
    for room_id, room in self._room_nodes.items():
      if room.room_type in self._public_types and room_id != room_id_input:
        total_distances.append(self._all_pairs_shortest_dist[room_id_input][room_id])
    if len(total_distances) == 0:
      raise ValueError("No public rooms!")
    return np.mean(total_distances)

  def get_ave_connectivity_private(self, room_id_input):
    if room_id_input not in self._room_nodes:
      raise ValueError(f"Invalide room_id_input: {room_id_input}")
    total_distances = []
    for room_id, room in self._room_nodes.items():
      if room.room_type in self._private_types and room_id != room_id_input:
        total_distances.append(self._all_pairs_shortest_dist[room_id_input][room_id])
    if len(total_distances) == 0:
      raise ValueError("No private rooms!")
    return np.mean(total_distances)

  def get_path_living_longest(self):
    dist_max = -1e10
    for id_start, id_end_and_dists in self._all_pairs_shortest_dist.items():
      for id_end, dist in id_end_and_dists.items():
        dist_max = np.max([dist, dist_max])
    return dist_max

  def get_path_living_shortest(self):
    dist_min = 1e10
    for id_start, id_end_and_dists in self._all_pairs_shortest_dist.items():
      for id_end, dist in id_end_and_dists.items():
        dist_min = np.min([dist, dist_min])
    return dist_min

  def print_path_start_to_end(self, id_start, id_end):
    print(f"The path from start id {id_start} to end id {id_end} is: ")
    print(self._all_pairs_shortest_path[id_start][id_end])
    print(f"The distance from start id {id_start} to end id {id_end} is: ", self._all_pairs_shortest_dist[id_start][id_end])
    path = self._all_pairs_shortest_path[id_start][id_end]
    for i in range(len(path) - 1):
      print(f"Distance from {path[i]} to {path[i+1]}: ", self._links[(path[i], path[i+1])].distance)

  # written by kk 4/16
  def get_score_commonarea(self):
    if self.get_public_ratio() > 0.3:
      score_commonarea = 100
    else:
      score_commonarea = (self.get_public_ratio() / 0.3) * 100
    return score_commonarea

  # written by kk 4/16
  def get_score_function(self):
    if self.get_function_ratio() > 0.7:
      score_function = 100
    else:
      score_function = (self.get_function_ratio() / 0.7) * 100
    return score_function

  # written by kk 4/16
  def get_score_corridor(self):
    if self.get_corridor_ratio() >= 0.1:
      score_corridor = 0
    else:
      score_corridor = 100 - (self.get_corridor_ratio() / 0.1) * 100
    return score_corridor

  # written by kk 4/16
  def get_score_connectivity_public(self):
    score_connectivity_public = (1 - ((self.get_ave_connectivity_public("3_1") - self.get_path_living_shortest()) / ((self.get_path_living_longest()) - self.get_path_living_shortest())) )* 100
    return score_connectivity_public

  # written by kk 4/16
  def get_score_connectivity_private(self):
    return (self.get_ave_connectivity_private("3_1") - self.get_path_living_shortest()) / (self.get_path_living_longest() - self.get_path_living_shortest())  * 100

  def get_score(self):
    score = (self.get_score_connectivity_public() + self.get_score_connectivity_private() + self.get_score_commonarea() + self.get_score_corridor() + self.get_score_function()) / 5
    return score

# path_room = "/Users/chen/Downloads/comoto/2-0-v2_adding garage_color_clean edge_with door_connectivity.json"
path_room = "demo/demo/2-0-v2_adding garage_color_clean edge_with door_connectivity.json"
rooms = Rooms.create_from_json(path_room)
print("rooms.get_total_area(): ", rooms.get_total_area())
print("rooms.get_public_area(): ", rooms.get_public_area())
print("get_total_number_roomtype(): ", rooms.get_total_number_roomtype())
print("get_target_nearby_function to 3_1 is: ", rooms.get_target_nearby_function("3_1"))
print("get_corridor_area: ", rooms.get_corridor_area())
print("avg public distance to 3_1 is:", rooms.get_ave_connectivity_public("3_1"))
print("get_path_living_longest(): ", rooms.get_path_living_longest())
# rooms.print_path_start_to_end("8_1", "3_1")
print("public_ratio: ", rooms.get_public_ratio())
print("score_commonarea: ", rooms.get_score_commonarea())
print("function_ratio: ", rooms.get_function_ratio())
print("score_function: ", rooms.get_score_function())
print("corridor_ratio: ", rooms.get_corridor_ratio())
print("score_corridor: ", rooms.get_score_corridor())
print("connectivity score public: ", rooms.get_score_connectivity_public())
print("connectivity score private: ", rooms.get_score_connectivity_private())
print("Final Score: ", rooms.get_score())
