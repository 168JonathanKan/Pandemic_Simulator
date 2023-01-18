from math import sqrt
from random import choice, sample, randint
from typing import List, Optional, Tuple

from pygame.color import Color
from pygame.draw import circle

import core.gui as gui
from core.agent import Agent, PYGAME_COLORS
from core.gui import (BLOCK_SPACING, CIRCLE, HOR_SEP, KNOWN_FIGURES, NETLOGO_FIGURE, SCREEN_PIXEL_HEIGHT,
                      SCREEN_PIXEL_WIDTH, STAR)
from core.link import Link, link_exists
from core.pairs import ATT_COEFF, ATT_EXPONENT, Pixel_xy, REP_COEFF, REP_EXPONENT, Velocity, force_as_dxdy
from core.sim_engine import gui_get, gui_set, SimEngine
from core.world_patch_block import World


class Graph_Node(Agent):

    def __init__(self, **kwargs):
        if 'color' not in kwargs:
            color = 'cyan'
            kwargs['color'] = Color(color)
        if 'shape_name' not in kwargs:
            shape_name = 'circle'
            kwargs['shape_name'] = shape_name
        super().__init__(**kwargs)

        # Is the  node selected?
        self.selected = False

    def __str__(self):
        return f'FLN-{self.id}'

    def adjust_distances(self, screen_distance_unit, velocity_adjustment=1):

        normalized_force = self.compute_velocity(screen_distance_unit, velocity_adjustment)
        self.set_velocity(normalized_force)
        self.forward()

    def compute_velocity(self, screen_distance_unit, velocity_adjustment):
        repulsive_force: Velocity = Velocity((0, 0))

        for node in (World.agents - {self}):
            repulsive_force += force_as_dxdy(self.center_pixel, node.center_pixel, screen_distance_unit)

        # Also consider repulsive force from walls.
        repulsive_wall_force: Velocity = Velocity((0, 0))

        horizontal_walls = [Pixel_xy((0, 0)), Pixel_xy((SCREEN_PIXEL_WIDTH(), 0))]
        x_pixel = Pixel_xy((self.center_pixel.x, 0))
        for h_wall_pixel in horizontal_walls:
            repulsive_wall_force += force_as_dxdy(x_pixel, h_wall_pixel, screen_distance_unit)

        vertical_walls = [Pixel_xy((0, 0)), Pixel_xy((0, SCREEN_PIXEL_HEIGHT()))]
        y_pixel = Pixel_xy((0, self.center_pixel.y))
        for v_wall_pixel in vertical_walls:
            repulsive_wall_force += force_as_dxdy(y_pixel, v_wall_pixel, screen_distance_unit)

        attractive_force: Velocity = Velocity((0, 0))
        for node in (World.agents - {self}):
            if link_exists(self, node):
                attractive_force += force_as_dxdy(self.center_pixel, node.center_pixel, screen_distance_unit,
                                                  repulsive=False)

        # noinspection PyTypeChecker
        net_force: Velocity = repulsive_force + repulsive_wall_force + attractive_force
        normalized_force: Velocity = net_force / max([net_force.x, net_force.y, velocity_adjustment])
        normalized_force *= 10

        if gui_get(PRINT_FORCE_VALUES):
            print(f'{self}. \n'
                  f'rep-force {tuple(repulsive_force.round(2))}; \n'
                  f'rep-wall-force {tuple(repulsive_wall_force.round(2))}; \n'
                  f'att-force {tuple(attractive_force.round(2))}; \n'
                  f'net-force {tuple(net_force.round(2))}; \n'
                  f'normalized_force {tuple(normalized_force.round(2))}; \n\n'
                  )
        return normalized_force

    def delete(self):
        World.agents.remove(self)
        World.links -= {lnk for lnk in World.links if lnk.includes(self)}

    def draw(self, shape_name=None):
        super().draw(shape_name=shape_name)
        if self.selected:
            radius = round((BLOCK_SPACING() / 2) * self.scale * 1.5)
            circle(gui.SCREEN, Color('red'), self.rect.center, radius, 1)


class Graph_World(World):

    def __init__(self, patch_class, agent_class):
        self.velocity_adjustment = 1
        super().__init__(patch_class, agent_class)
        self.shortest_path_links = None
        self.selected_nodes = set()

    # noinspection PyMethodMayBeStatic
    def average_path_length(self):
        return

    def build_graph(self):

        nbr_nodes = gui_get(NUMBER_OF_NODES)
        random_node_list = self.create_random_agents(nbr_nodes, color='cyan', shape_name='circle')
        if nbr_nodes:
            self.link_nodes_for_graph(nbr_nodes, random_node_list)

    def build_shortest_path(self):
        Graph_World.reset_links()
        self.selected_nodes = [node for node in World.agents if node.selected]
        # If there are exactly two selected nodes, find the shortest path between them.
        if len(self.selected_nodes) == 2:
            self.shortest_path_links = self.shortest_path()
            # self.shortest_path_links will be either a list of links or None
            # If there is a path, highlight it.
            if self.shortest_path_links:
                for lnk in self.shortest_path_links:
                    lnk.color = Color('red')
                    lnk.width = 2

    @staticmethod
    def create_random_link():
        """
        Create a new link between two random nodes, if possible.
        The approach is to pick a random node and then pick another random node
        with no link to the first one. If there are no nodes that are not already
        linked to the first node, select a different first node. Repeat until
        a pair of nodes is found that can be linked. If all pairs of nodes
        are already linked, do nothing.
        """
        link_created = False
        # sample() both copies and shuffles elements from its first argument.
        # Can't use choice with World.agents because world.agents is a set and
        # can't be accessed through an index, which is what choice uses.
        node_set_1 = sample(World.agents, len(World.agents))
        while not link_created:
            node_1 = node_set_1.pop()
            # Since node_1 has been popped from node_set_1,
            # node_set_2 does not contain node_1.
            # Can't use choice with a set.
            node_set_2 = sample(node_set_1, len(node_set_1))
            while node_set_2:
                node_2 = node_set_2.pop()
                if not link_exists(node_1, node_2):
                    Link(node_1, node_2)
                    link_created = True
                    break

    def delete_a_shortest_path_link(self):
        """
        Look for a link to delete so that there is still some shortest path.
        Pick the one with the longest shortest path.
        """
        (longest_path_len, lnk) = (0, None)
        for lnk_x in self.shortest_path_links:
            World.links.remove(lnk_x)
            path = self.shortest_path()
            if path and len(path) > longest_path_len:
                (longest_path_len, lnk) = (len(path), lnk_x)
            World.links.add(lnk_x)

        if not lnk:
            lnk = choice(self.shortest_path_links)
        World.links.remove(lnk)

    def disable_enable_buttons(self):
        # 'enabled' is a pseudo attribute. gui_set replaces it with 'disabled' and negates the value.
        # Show node id's or not as requested.
        show_labels = gui_get(SHOW_NODE_IDS)
        for node in World.agents:
            node.label = str(node.id) if show_labels else None

    def draw(self):
        self.build_shortest_path()
        # Update which buttons are enabled.
        self.disable_enable_buttons()
        super().draw()

    def handle_event(self, event):
        """
        This is called when a GUI widget is changed and the change isn't handled by the system.
        The key of the widget that changed is in event.
        """

        super().handle_event(event)

    @staticmethod
    def link_nodes_for_graph(nbr_nodes, random_node_list):
        """
        Link the nodes to create the requested graph.

        Args:
            graph_type: The name of the graph type.
            nbr_nodes: The total number of nodes the user requested
            ring_node_list: The nodes that have been arranged in a ring.
                            Will contain either:
                            nbr_nodes - 1 if graph type is STAR or WHEEL
                            or nbr_nodes otherwise

        Returns: None

        To be overridden in subclasses.
        """
        pass

    def mouse_click(self, xy: Tuple[int, int]):
        """ Select closest node. """
        patch = self.pixel_tuple_to_patch(xy)
        if len(patch.agents) == 1:
            node = sample(patch.agents, 1)[0]
        else:
            patches = patch.neighbors_24()
            nodes = {node for patch in patches for node in patch.agents}
            node = nodes.pop() if nodes else Pixel_xy(xy).closest_block(World.agents)
        if node:
            node.selected = not node.selected

    @staticmethod
    def reset_links():
        # Set all the links back to normal.
        for lnk in World.links:
            lnk.color = lnk.default_color
            lnk.width = 1

    @staticmethod
    def screen_distance_unit():
        dist_unit = gui_get(DIST_UNIT)
        screen_distance_unit = sqrt(SCREEN_PIXEL_WIDTH() ** 2 + SCREEN_PIXEL_HEIGHT() ** 2) / dist_unit
        return screen_distance_unit

    def setup(self):
        SimEngine.fps = gui_get(VIRUS_CHECK_FREQUENCY)
        self.disable_enable_buttons()
        self.build_graph()

    def shortest_path(self) -> Optional[List[Link]]:
        """
        Create and return a shortest path (if any) between the selected nodes.
        Uses a breadth-first search.
        """
        count = 0
        (node1, node2) = self.selected_nodes
        # Start with the node with the smaller number of neighbors.
        if len(node1.lnk_nbrs()) > len(node2.lnk_nbrs()):
            (node1, node2) = (node2, node1)
        visited = {node1}
        # A path is a sequence of tuples (link, node) where
        # the link attaches to the node in the preceding
        # tuple. The first tuple in a path starts with a
        # None link since there is no preceding node.

        # The frontier is a list of paths, shortest firs

        frontier = [[(None, node1)]]
        while frontier:
            current_path = frontier.pop(0)
            # The lnk_nbrs are tuples as in the paths. For a given node
            # they are all the node's links along with the nodes linked to.

            # This gets the last node in the current path,
            (_last_link, last_node) = current_path[-1]

            # This gets all the non-visited lnk_nbrs of the last node.
            # Each neighbor is a (link, node) pair.
            lnk_nbrs = [(lnk, nbr) for (lnk, nbr) in last_node.lnk_nbrs() if nbr not in visited]

            # Do any of these continuations reach the target, node_2? If so, we've found the shortest path.
            lnks_to_node_2 = [(lnk, nbr) for (lnk, nbr) in lnk_nbrs if nbr == node2]
            # If lnks_to_node_2 is non-empty it will have one element: (lnk, node_2)

            if lnks_to_node_2:
                path = current_path + lnks_to_node_2
                # Extract the links, but drop the None at the beginning.
                lnks = [lnk for (lnk, _nbr) in path[1:]]
                return lnks

            # Not done. Add the newly reached nodes to visted.
            visited |= {nbr for (_lnk, nbr) in lnk_nbrs}

            # For each neighbor construct an extended version of the current path.
            extended_paths = [current_path + [lnk_nbr] for lnk_nbr in lnk_nbrs]

            # Add all those extended paths to the frontier.
            frontier += extended_paths
        # If we get out of the loop because the frontier is empty, there is no path from node_1 to node_2.
        return None


    def step(self):
        list_nodes = World.agents
        infection_chance = gui_get(VIRUS_SPREAD_CHANCE)
        recover_chance = gui_get(RECOVERY_CHANCE)
        resistance_chance = gui_get(GAIN_RESISTANCE_CHANCE)
        for node in list_nodes:
            if node.color == 'red':
                connections = node.lnk_nbrs()
                for infect in connections:
                    if randint(1, 100) <= infection_chance and infect[1].color is not 'grey':
                        infect[1].set_color('red')
                if randint(1, 100) <= recover_chance:
                    node.set_color('cyan')
                if randint(1, 100) <= resistance_chance:
                    node.set_color('grey')





# ############################################## Define GUI ############################################## #
import PySimpleGUI as sg

# Keys and other GUI strings. Grouped together more or less as they appear in the GUI.

NUMBER_OF_NODES = 'number-of-nodes'
AVERAGE_NODE_DEGREE = 'average-node-degree'
INITIAL_OUTBREAK_SIZE = 'initial-outbreak-size'
CLEAR = 'clear'

VIRUS_SPREAD_CHANCE = 'virus-spread-chance'
VIRUS_CHECK_FREQUENCY = 'virus-check-frequency'
RECOVERY_CHANCE = 'recovery-chance'
GAIN_RESISTANCE_CHANCE = 'gain-resistance-chance'

# REP_COEFF = 'rep_coeff'
# REP_EXPONENT = 'rep_exponent'
# ATT_COEFF = 'att_coeff'
# ATT_EXPONENT = 'att_exponent'
DIST_UNIT = 'dist_unit'
SHOW_NODE_IDS = "Show node id's"
PRINT_FORCE_VALUES = 'Print force values'

SHAPE = 'shape'
COLOR = 'color'

tt = 'Probability that two nodes in a random graph will be linked\n' \
     'or that a link in a small world graph will be rewired'

graph_left_upper = [

    [sg.Text('number-of-nodes', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((0, 100), default_value=20, orientation='horizontal', key=NUMBER_OF_NODES,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],
    [sg.Text('average-node-degree', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((0, 100), default_value=5, orientation='horizontal', key=AVERAGE_NODE_DEGREE,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],

    [sg.Text('initial-out-break-size', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((0, 100), default_value=5, orientation='horizontal', key=INITIAL_OUTBREAK_SIZE,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],

    [sg.Text('virus-spread-chance', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((0, 100), default_value=2, orientation='horizontal', key=VIRUS_SPREAD_CHANCE,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],

    [sg.Text('virus-check-frequency(FPS)', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((10, 60), default_value=1, orientation='horizontal', key=VIRUS_CHECK_FREQUENCY,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],

    [sg.Text('recovery-chance', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((0, 100), default_value=5, orientation='horizontal', key=RECOVERY_CHANCE,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],

    [sg.Text('gain-resistance-chance', pad=((0, 10), (20, 0)),
             tooltip=tt),
     sg.Slider((0, 100), default_value=5, orientation='horizontal', key=GAIN_RESISTANCE_CHANCE,
               size=(10, 20), pad=((0, 0), (10, 0)),
               tooltip=tt)],

    [
        sg.Checkbox("Show node id's", key=SHOW_NODE_IDS, default=False, pad=((20, 0), (20, 0))),
        sg.Checkbox('Print force values', key=PRINT_FORCE_VALUES, default=False, pad=((20, 0), (20, 0)))
    ],

]
graph_right_upper = [

]

if __name__ == '__main__':
    from core.agent import PyLogo

    PyLogo(Graph_World, 'Force test', gui_left_upper=graph_left_upper, gui_right_upper=graph_right_upper,
           agent_class=Graph_Node, clear=True, auto_setup=True)
