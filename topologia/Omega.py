# Copyright (c) 2010 Advanced Micro Devices, Inc.
#               2016 Georgia Institute of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

from __future__ import print_function
from __future__ import absolute_import

from m5.params import *
from m5.objects import *
from math import *

from common import FileSystemConfig

from .BaseTopology import SimpleTopology

# Creates an omega topology, assuming an equal number of
# cache and four directories, one in each corner of the
# topology.
# Wormhole routing is enforced (based on known fixed
# links) to guarantee deadlock freedom.
 
class Omega(SimpleTopology):
	description='Omega'

	def __init__(self, controllers):
		self.nodes = controllers

	# Makes a omega topology
	# assuming an equal number of cache and directory cntrls

	def makeTopology(self, options, network, IntLink, ExtLink, Router):
		nodes = self.nodes

		# 1-ary
		cpu_per_router = 2

		num_routers = int((options.num_cpus * (log(options.num_cpus,2) + 1)) / cpu_per_router)
		print("Butterfly number of routers = " + str(num_routers))
		num_rows = int(log(options.num_cpus, 2) + (2 - cpu_per_router))
		print("With " + str(num_rows) + " Ranks")

		## Define as latencias associadas.
		# default values for link latency and router latency.
		# Can be over-ridden on a per link/router basis
		link_latency = options.link_latency # used by simple and garnet
		router_latency = options.router_latency # only used by garnet

		
		cache_nodes = []
		dir_nodes = []
		dma_nodes = []
		for node in nodes:
			if node.type == 'L1Cache_Controller' or \
			node.type == 'L2Cache_Controller':
				cache_nodes.append(node)
			elif node.type == 'Directory_Controller':
				dir_nodes.append(node)
			elif node.type == 'DMA_Controller':
				dma_nodes.append(node)



		assert(num_rows > 0 and num_rows <= num_routers)
		assert(len(dir_nodes) == 4)

		# Cria os roteadores
		routers = [Router(router_id=i, latency = router_latency) \
			for i in range(num_routers)]
		network.routers = routers


		link_count = 0

		# Conecta cada nodo ao seu roteador apropriado
		ext_links = []
		print("Conectando os nodes aos roteadores\n")
		for (i, n) in enumerate(cache_nodes):
			cntrl_level, router_id = divmod(i, options.num_cpus / cpu_per_router)
			print("Conectado o node " + str(n) + " ao roteador " + str(router_id) + "\n")
			ext_links.append(ExtLink(link_id=link_count, ext_node=n,
									int_node=routers[router_id],
									latency = link_latency))
			link_count += 1

		
		print("Diretorio 1 ligado ao roteador 0")
		ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[0],
								int_node=routers[0],
								latency = link_latency))
		link_count += 1

		print("Diretorio 2 ligado ao roteador " + str((options.num_cpus / cpu_per_router / 2) - 1))
		ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[1],
								int_node=routers[(options.num_cpus / cpu_per_router / 2) - 1],
								latency = link_latency))
		link_count += 1

		print("Diretorio 3 ligado ao roteador " + str(options.num_cpus/cpu_per_router / 2))
		ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[2],
								int_node=routers[options.num_cpus / cpu_per_router / 2],
								latency = link_latency))
		link_count += 1

		print("Diretorio 4 ligado ao roteador " + str((options.num_cpus / cpu_per_router) - 1))
		ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[3],
								int_node=routers[(options.num_cpus / cpu_per_router) - 1],
								latency = link_latency))
		link_count += 1

		# Conecta os nodos de DMA ao roteador 0. These should only be DMA nodes.
		for (i, node) in enumerate(dma_nodes):
			assert(node.type == 'DMA_Controller')
			ext_links.append(ExtLink(link_id=link_count, ext_node=node,
									 int_node=routers[0],
									 latency = link_latency))

		network.ext_links = ext_links

		
		print("\nConectando os roteadores entre eles")
		int_links = []

		for i in xrange(num_rows - 1):
			aux = 0
			for j in xrange(options.num_cpus / cpu_per_router):
				print("\nO node [" +str(i)+ ","+str(j)+"] se conecta em:")
				print("[" + str(i+1) + "," + str(aux) + "]")

				_out = (i * options.num_cpus / cpu_per_router) + j
				_in = ((i+1) * options.num_cpus / cpu_per_router) + aux

				print("Ligou o " +  str(_out) + " no " +  str(_in))
				int_links.append(IntLink(link_id=link_count,
										 src_node=routers[_out],
										 dst_node=routers[_in],
										 src_outport="South",
										 dst_inport="North",
										 latency = link_latency,
										 weight=1))
				link_count += 1

				print("Ligou o " +  str(_in) + " no " +  str(_out))
				int_links.append(IntLink(link_id=link_count,
										 src_node=routers[_in],
										 dst_node=routers[_out],
										 src_outport="North",
										 dst_inport="South",
										 latency = link_latency,
										 weight=1))
				link_count += 1


				aux += 1

				print("\nE em [" + str(i+1) + "," + str(aux) + "]")
				_in = ((i+1) * options.num_cpus / cpu_per_router) + aux

				print("Ligou o " +  str(_out) + " no " +  str(_in))
				int_links.append(IntLink(link_id=link_count,
										 src_node=routers[_out],
										 dst_node=routers[_in],
										 src_outport="South",
										 dst_inport="North",
										 latency = link_latency,
										 weight=1))
				link_count += 1

				print("Ligou o " +  str(_in) + " no " +  str(_out))
				int_links.append(IntLink(link_id=link_count,
										 src_node=routers[_in],
										 dst_node=routers[_out],
										 src_outport="North",
										 dst_inport="South",
										 latency = link_latency,
										 weight=1))
				link_count += 1

				if(j == (options.num_cpus / cpu_per_router / 2) - 1):
					print("---RESETOU AUX!!!---")
					aux = 0
				else:
					aux += 1

		network.int_links = int_links

	# Register nodes with filesystem
	def registerTopology(self, options):
		for i in xrange(options.num_cpus):
			FileSystemConfig.register_node([i],
					MemorySize(options.mem_size) / options.num_cpus, i)
