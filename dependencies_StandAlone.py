#!/usr/bin/env python

import argparse
import re
import subprocess, sys, os
from pythonds import Queue, Graph, Vertex
from colorama import Fore, Style

vertices = []
consumes = Graph()
is_consumed = Graph()
blacklisted_modules_id = []

class MyVertex(Vertex):
    WHITE = 'white'
    GRAY = 'gray'
    BLACK = 'black'
    def __init__(self,num):
        self.color = MyVertex.WHITE
        super().__init__(num)

def bfs(graph, start, debug=False):
      """
      Breadth First Search (BFS)
      Given a node in a graph, BFS will find all nodes connected to this
      node. The distance between nodes is measured in HOPS. It will find
      all nodes at distance 'k' before finding any nodes at a further
      distance. It will return the full list of connected nodes.
       PseudoCode:
       BFS(G,s)
       for each vertex u in V[G] - {s} do
        state[u] = WHITE
        predecessor[u] = nil
      state[s] = GRAY
      predecessor[s] = nil
      QUEUE = {s}
      while QUEUE != 0 do
        u = dequeue[Q]
        process vertex u as desired
        for each v in Adjacent[u] do
          process edge (u,v) as desired (e.g. distance[v] = distance[u] + 1)
          if state[v] = WHITE then
            state[v] = GRAY
            predecessor[v] = u
            enqueue[Q,v]
        state[u] = BLACK
      """
      result = []
      for v in graph.getVertices():
          a_vertex = graph.getVertex(v)
          a_vertex.__classname__ = 'MyVertex'
          a_vertex.setColor(MyVertex.WHITE)
          a_vertex.setDistance(0)
          a_vertex.setPred(None)

      start.setDistance(0)
      start.setPred(None)
      vertex_queue = Queue()
      vertex_queue.enqueue(start)
      while (vertex_queue.size() > 0):
          current_vertex = vertex_queue.dequeue()
          result.append(current_vertex)
          if debug:
              print(current_vertex)
          for v in current_vertex.getConnections():
              if v.getColor() == MyVertex.WHITE:
                  v.setColor(MyVertex.GRAY)
                  v.setDistance(current_vertex.getDistance() + 1)
                  v.setPred(current_vertex)
                  vertex_queue.enqueue(v)
          current_vertex.setColor(MyVertex.BLACK)
      return result

def createGraph(args):
    blacklist_modules = []
    if args.exclude_from_nodes:
        blacklist_modules.extend(args.exclude_from_nodes)
    if args.exclude_from_files:
        with open(args.exclude_from_files, 'r') as f:
            lines = [line.rstrip() for line in f]
        blacklist_modules.extend(lines)

    with open('%s' % args.filename, 'r') as f:
        for linenum, line in enumerate(f):
            m_v = re.match('(\d+).*label=(\w+),.*tooltip=(\w+)', line)
            m_e = re.match('(\d+) -> (\d+)(\[.*\])*;', line)
            if m_v:
                while (len(vertices) < int(m_v.group(1))):
                    if args.debug:
                        print(Fore.RED + Style.BRIGHT + "Adding missing Vtx {}".format(len(vertices)))
                    vertices.append(Vertex(-1))
                    vertices[-1].label = "FAKE_VTX"
                if args.debug:
                    print(Fore.GREEN + "Adding vertex {}".format(m_v.group(1)))
                vertices.append(Vertex(int(m_v.group(1))))
                vertices[-1].label = m_v.group(2)
                vertices[-1].tooltip = m_v.group(3)
                vertices[-1].linecolor = 'black'
                if m_v.group(2) in blacklist_modules:
                    blacklisted_modules_id.append(int(m_v.group(1)))
                    vertices[-1].linecolor = 'red'
            elif m_e:
                if not int(m_e.group(1)) in blacklisted_modules_id:
                    consumes.addEdge(int(m_e.group(1)), int(m_e.group(2)))
                if not int(m_e.group(2)) in blacklisted_modules_id:
                    is_consumed.addEdge(int(m_e.group(2)), int(m_e.group(1)))
            else:
                print(Fore.RED + Style.BRIGHT + "Unknown line [{}]: ".format(linenum)
                      + Style.RESET_ALL + "{}".format(line.strip()))

def toDotOutput(args, graph, append):
    root_label = args.label
    outputFormat = args.output
    root_nodes = [v for v in vertices if v.label == root_label]
    assert(len(root_nodes)<=1)
    print(Fore.GREEN + "Generating the {} graph...".format(append) + Style.RESET_ALL)
    nodes = bfs(graph, graph.getVertex(root_nodes[0].getId()))
    filename = args.outputfile
    if filename == '':
        filename = root_label

    with open('%s_%s.gv' % (filename, append), 'w') as output:
        output.write('digraph RECO { graph [label = "%s", labelloc=top];\n' % root_label)
        distances = {}
        for n in nodes:
            distances.setdefault(n.getDistance(), list())
            distances[n.getDistance()].append(n.getId())
            if args.debug:
                print(Fore.GREEN + Style.BRIGHT
                        + "Level {}, node {}".format(n.getDistance(), n.getId())
                        + Style.RESET_ALL)
            if n.getDistance() > args.maxBFSDepth:
                print(Fore.RED + Style.BRIGHT
                        + "Stopping at BFS level {}".format(args.maxBFSDepth)
                        + Style.RESET_ALL)
                continue
            output.write('%d[label=%s_%d, tooltip=%s, color=%s, shape=box];\n' % (n.getId(),
                vertices[n.getId()].label,
                n.getDistance(),
                vertices[n.getId()].tooltip,
                vertices[n.getId()].linecolor))
            # Print connections only if your depth is maxBFSDepth - 1, so that you'll land
            # still on required modules, otherwise there'll be connections to non-existing nodes.
            if n.getDistance() < args.maxBFSDepth:
                for child in n.getConnections():
                    output.write('%d -> %d;\n' % (n.getId(), child.getId()))
            if len(n.getConnections()) == 0:
                print(Fore.YELLOW + Style.BRIGHT +
                        "Leaf Node level {} name {}".format(n.getDistance(), vertices[n.getId()].label)
                        + Style.RESET_ALL)
        output.write('}\n')
        print("Graph processed.")
        for k in distances.keys():
            print("Level "
                    + Fore.GREEN + "{}".format(k) + Style.RESET_ALL
                    + " has " + Fore.YELLOW + "{}".format(len(distances[k])) + Style.RESET_ALL +" entries")
    try:
        f = open(os.devnull, 'w')
        _ = subprocess.check_call(
                ['dot',
                 '-Grankdir=LR',
                 '-Gmindist=4.0',
                 '-Gsplines=ortho',
                 '-v',
                 '-T{outputFormat}'.format(outputFormat=outputFormat),
                 '{filename}_{append}.gv'.format(filename=filename, append=append),
                 '-o',
                 '{filename}_{append}.{outputFormat}'.format(filename=filename, outputFormat=outputFormat, append=append)
                 ], stdout=f, stderr=f)
    except subprocess.CalledProcessError as e:
        print("Return value:{}".format(e.returcode))
        print("Output: {}".format(e.output))
        sys.exit(1)
    print("Done.")

def searchAndPrintNode(args):
    createGraph(args)
    toDotOutput(args, consumes, 'consumes')
    toDotOutput(args, is_consumed, 'is_consumed_by')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Explore CMSSW FWK dependency graph.')
  parser.add_argument('-f', '--filename',
                     default = None,
                     help = 'Dependency file to use to extract information.',
                     type = str,
                     required=True)
  parser.add_argument('-l', '--label',
                     default = '',
                     help = 'Label of the python module to use as the main vertex of the Graph.',
                     type = str,
                     required=True)
  parser.add_argument('-d', '--debug',
                     default = False,
                     action='store_true',
                     help = 'Enable debugging printouts',
                     required=False)
  parser.add_argument('-o', '--output',
                     default = 'pdf',
                     help = 'Output extension of the generated plots.',
                     type = str,
                     required=False)
  parser.add_argument('-O', '--outputfile',
                     default = '',
                     help = 'Output filename, w/o extension, to be used. If none given, use the label of the root module.',
                     type = str,
                     required=False)
  parser.add_argument('-m', '--maxBFSDepth',
                     help = 'Maximum depth of BFS exploration to plot.',
                     type = int,
                     default = sys.maxsize,
                     required=False)
  parser.add_argument('--exclude_from_nodes',
                     nargs='*',
                     default = '',
                     help = 'List of python labels starting from which nodes will be pruned while exploring the graph.',
                     required=False,
                     type=str)
  parser.add_argument('--exclude_from_files',
                     default = '',
                     help = 'Text file that contains the list of python labels starting from which nodes will be pruned while exploring the graph. One module per line.',
                     required=False,
                     type=str)
  args = parser.parse_args()
  print(args)
  searchAndPrintNode(args)
