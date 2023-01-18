# Import the string constants you need (mainly keys) as well as classes and gui elements
from random import randint, random, shuffle
import random

from core.pandemic_framework import (Graph_Node, Graph_World, graph_left_upper, graph_right_upper, NUMBER_OF_NODES,
                                  AVERAGE_NODE_DEGREE, INITIAL_OUTBREAK_SIZE)
from core.gui import STAR
from core.link import Link
from core.pairs import center_pixel
from core.sim_engine import gui_get, gui_set
from core.world_patch_block import World

class Virus_World(Graph_World):

    @staticmethod
    def link_nodes_for_graph(nbr_nodes, random_node_list):
        # Treat random graphs as a separate case.
        degree = gui_get(AVERAGE_NODE_DEGREE)
        if(degree > gui_get(NUMBER_OF_NODES)):
            degree = gui_get(NUMBER_OF_NODES)
        # A generator for the links
        for i in range(len(random_node_list)):
            neighboring_agents = random_node_list[i].agents_in_radius(200)
            rand_degree = randint(1, degree*2)
            for j in range(0, len(neighboring_agents)):
                if j == rand_degree:
                    break
                if len(neighboring_agents[j].all_links()) < degree*2:
                    Link(random_node_list[i], neighboring_agents[j])
        Virus_World.initialize_infected(random_node_list)
        return

    def initialize_infected(random_node_list):
        nbr_infected = gui_get(INITIAL_OUTBREAK_SIZE)
        if(nbr_infected > gui_get(NUMBER_OF_NODES)):
            nbr_infected = gui_get(NUMBER_OF_NODES)
        infected_list = random_node_list.copy()
        random.shuffle(infected_list)
        for i in range(0, nbr_infected):
            infected_list[i].set_color('red')



def rand_num_exclude(size, exclude):
    randInt = randint(0, size-1)
    if randInt == exclude:
        return rand_num_exclude(size, exclude)
    else:
        return randInt


if __name__ == '__main__':
    from core.agent import PyLogo
    PyLogo(Virus_World, 'Pandemic_Simulation', gui_left_upper=graph_left_upper, gui_right_upper = graph_right_upper,
           agent_class=Graph_Node, clear=True, bounce=True, auto_setup=False)
